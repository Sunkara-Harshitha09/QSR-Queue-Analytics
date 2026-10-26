import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = ROOT / "data" / "videos"
CONFIG_PATH = ROOT / "edge" / "config" / "video_regions.json"
OUTPUT_DIR = ROOT / "data" / "evidence" / "queue_tracking"
MODEL_NAME = "yolo11n.pt"
CONFIDENCE = 0.25
IMAGE_SIZE = 640
DEVICE = "cpu"

config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
model = YOLO(MODEL_NAME)
combined_summary = []

for video_name in ("counter.mp4", "normal_queue.mp4"):
    video_path = VIDEO_DIR / video_name
    video_config = config.get(video_name, {})
    points = video_config.get("queue_region", [])

    if len(points) < 3:
        print(f"SKIPPING {video_name}: queue polygon not configured.")
        continue

    polygon = np.array(points, dtype=np.int32)
    out_dir = OUTPUT_DIR / video_path.stem
    snapshots_dir = out_dir / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"SKIPPING {video_name}: cannot open video.")
        continue

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if polygon[:, 0].max() >= width or polygon[:, 1].max() >= height:
        raise ValueError(f"{video_name}: queue polygon exceeds video dimensions.")

    output_video = out_dir / f"{video_path.stem}_queue_tracking.mp4"
    output_csv = out_dir / "person_records.csv"
    output_json = out_dir / "summary.json"

    writer = cv2.VideoWriter(
        str(output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Cannot create output video: {output_video}")

    # IDs are local to each video. Never merge IDs across separate videos.
    people = {}
    frame_index = 0
    start_time = time.time()

    print(f"\n===== Processing {video_name} ({width}x{height}) =====")

    try:
        results = model.track(
            source=str(video_path),
            stream=True,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=CONFIDENCE,
            imgsz=IMAGE_SIZE,
            device=DEVICE,
            verbose=False,
        )

        for result in results:
            frame = result.orig_img.copy()
            current_queue_ids = set()
            video_second = frame_index / fps

            if result.boxes is not None and result.boxes.id is not None:
                ids = result.boxes.id.int().cpu().tolist()
                boxes = result.boxes.xyxy.cpu().tolist()
                confs = result.boxes.conf.cpu().tolist()

                for track_id, box, confidence in zip(ids, boxes, confs):
                    x1, y1, x2, y2 = map(int, box)
                    footpoint = (int((x1 + x2) / 2), y2)

                    inside = cv2.pointPolygonTest(
                        polygon,
                        (float(footpoint[0]), float(footpoint[1])),
                        False,
                    ) >= 0

                    if not inside:
                        continue

                    key = str(track_id)
                    current_queue_ids.add(key)

                    if key not in people:
                        snap = snapshots_dir / f"person_track_{track_id}.jpg"
                        crop = result.orig_img[
                            max(0, y1):min(height, y2),
                            max(0, x1):min(width, x2),
                        ]
                        if crop.size:
                            cv2.imwrite(str(snap), crop)

                        people[key] = {
                            "video_filename": video_name,
                            "track_id": int(track_id),
                            "first_seen_video_second": round(video_second, 3),
                            "last_seen_video_second": round(video_second, 3),
                            "first_seen_frame": frame_index,
                            "last_seen_frame": frame_index,
                            "max_confidence": round(float(confidence), 4),
                            "snapshot_path": (
                                str(snap.relative_to(ROOT)) if snap.exists() else ""
                            ),
                        }
                    else:
                        people[key]["last_seen_video_second"] = round(video_second, 3)
                        people[key]["last_seen_frame"] = frame_index
                        people[key]["max_confidence"] = max(
                            people[key]["max_confidence"],
                            round(float(confidence), 4),
                        )

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
                    cv2.putText(
                        frame, f"Person {track_id}",
                        (x1, max(20, y1 - 7)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 0), 2,
                    )

            cv2.polylines(frame, [polygon], True, (0, 255, 255), 2)
            cv2.putText(
                frame, f"Current queue: {len(current_queue_ids)}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2,
            )
            cv2.putText(
                frame, f"Unique queue IDs: {len(people)}",
                (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2,
            )
            writer.write(frame)
            frame_index += 1

            if frame_index % 60 == 0:
                print(
                    f"{frame_index}/{total_frames} frames; "
                    f"current queue={len(current_queue_ids)}, "
                    f"unique IDs={len(people)}"
                )
    finally:
        writer.release()

    records = sorted(people.values(), key=lambda item: item["track_id"])
    fields = [
        "video_filename", "track_id",
        "first_seen_video_second", "last_seen_video_second",
        "first_seen_frame", "last_seen_frame",
        "max_confidence", "snapshot_path",
    ]

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        csv_writer = csv.DictWriter(f, fieldnames=fields)
        csv_writer.writeheader()
        csv_writer.writerows(records)

    summary = {
        "video": video_name,
        "resolution": f"{width}x{height}",
        "fps": fps,
        "reported_frames": total_frames,
        "processed_frames": frame_index,
        "unique_queue_track_ids": len(records),
        "processing_seconds": round(time.time() - start_time, 2),
        "model": MODEL_NAME,
        "tracker": "ByteTrack",
        "device": DEVICE,
        "queue_polygon": points,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "csv_path": str(output_csv.relative_to(ROOT)),
        "annotated_video_path": str(output_video.relative_to(ROOT)),
        "snapshots_folder": str(snapshots_dir.relative_to(ROOT)),
        "note": (
            "Track IDs are video-local. Counts are tracker IDs observed in the "
            "queue polygon and may include ID switches. Validate annotated output."
        ),
    }
    output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    combined_summary.append(summary)
    print(json.dumps(summary, indent=2))

(OUTPUT_DIR / "both_videos_summary.json").write_text(
    json.dumps(combined_summary, indent=2), encoding="utf-8"
)

print("\n===== BOTH VIDEOS FINISHED =====")
print(f"Combined summary: {OUTPUT_DIR / 'both_videos_summary.json'}")
