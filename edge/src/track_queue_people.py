import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "data" / "videos" / "counter.mp4"
CONFIG = ROOT / "edge" / "config" / "video_regions.json"
OUT = ROOT / "data" / "evidence" / "queue_tracking"
SNAPSHOTS = OUT / "snapshots"

MODEL_NAME = "yolo11n.pt"
CONFIDENCE = 0.25
IMAGE_SIZE = 640
DEVICE = "cpu"

OUT.mkdir(parents=True, exist_ok=True)
SNAPSHOTS.mkdir(parents=True, exist_ok=True)

if not VIDEO.exists():
    raise FileNotFoundError(f"Video not found: {VIDEO}")
if not CONFIG.exists():
    raise FileNotFoundError(f"Region configuration not found: {CONFIG}")

config = json.loads(CONFIG.read_text(encoding="utf-8"))
video_config = config.get("counter.mp4")
if not isinstance(video_config, dict):
    raise ValueError("Expected 'counter.mp4' in video_regions.json")

points = video_config.get("queue_region", [])
if len(points) < 3:
    raise ValueError("Queue polygon needs at least three points. Run configure_queue_region.py.")

polygon = np.array(points, dtype=np.int32)

cap = cv2.VideoCapture(str(VIDEO))
if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {VIDEO}")

fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()

if polygon[:, 0].max() >= width or polygon[:, 1].max() >= height:
    raise ValueError(
        f"Queue polygon coordinates exceed video size {width}x{height}. "
        "Reconfigure the queue region."
    )

print(f"Video: {VIDEO.name} ({width}x{height}, {fps:.2f} FPS)")
print(f"Queue polygon points: {points}")
print("Loading YOLO model and starting person tracking...")

model = YOLO(MODEL_NAME)
annotated_path = OUT / "counter_queue_tracking.mp4"
csv_path = OUT / "queue_person_records.csv"
summary_path = OUT / "summary.json"

video_writer = cv2.VideoWriter(
    str(annotated_path),
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (width, height),
)
if not video_writer.isOpened():
    raise RuntimeError("Could not create annotated video.")

# One dictionary entry per tracker ID that entered the queue region.
people = {}
frames_processed = 0
started = time.time()

try:
    results = model.track(
        source=str(VIDEO),
        stream=True,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],  # COCO person class only
        conf=CONFIDENCE,
        imgsz=IMAGE_SIZE,
        device=DEVICE,
        verbose=False,
    )

    for result in results:
        frame = result.orig_img.copy()
        frame_index = frames_processed
        video_second = frame_index / fps
        frames_processed += 1

        current_queue_ids = set()

        if result.boxes is not None and result.boxes.id is not None:
            track_ids = result.boxes.id.int().cpu().tolist()
            boxes = result.boxes.xyxy.cpu().tolist()
            confidences = result.boxes.conf.cpu().tolist()

            for track_id, box, confidence in zip(track_ids, boxes, confidences):
                x1, y1, x2, y2 = [int(v) for v in box]

                # Use the bottom-centre of the person bounding box as the footpoint.
                foot_x = int((x1 + x2) / 2)
                foot_y = int(y2)

                inside_queue = (
                    cv2.pointPolygonTest(
                        polygon, (float(foot_x), float(foot_y)), False
                    ) >= 0
                )

                if not inside_queue:
                    continue

                key = str(track_id)
                current_queue_ids.add(key)

                if key not in people:
                    snapshot_path = SNAPSHOTS / f"person_track_{track_id}.jpg"
                    crop = result.orig_img[
                        max(0, y1):min(height, y2),
                        max(0, x1):min(width, x2),
                    ]
                    if crop.size:
                        cv2.imwrite(str(snapshot_path), crop)

                    people[key] = {
                        "track_id": int(track_id),
                        "video_filename": VIDEO.name,
                        "first_seen_video_second": round(video_second, 3),
                        "last_seen_video_second": round(video_second, 3),
                        "first_seen_frame": frame_index,
                        "last_seen_frame": frame_index,
                        "max_confidence": round(float(confidence), 4),
                        "snapshot_path": (
                            str(snapshot_path.relative_to(ROOT))
                            if snapshot_path.exists() else ""
                        ),
                    }
                else:
                    people[key]["last_seen_video_second"] = round(video_second, 3)
                    people[key]["last_seen_frame"] = frame_index
                    people[key]["max_confidence"] = max(
                        people[key]["max_confidence"],
                        round(float(confidence), 4),
                    )

                # Draw only queue-region people as tracked people.
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
                cv2.circle(frame, (foot_x, foot_y), 5, (0, 0, 255), -1)
                cv2.putText(
                    frame, f"Person {track_id}",
                    (x1, max(25, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 0), 2,
                )

        # Overlay queue boundary and current/unique queue counts.
        cv2.polylines(frame, [polygon], True, (0, 255, 255), 3)
        cv2.putText(
            frame,
            f"People currently in queue: {len(current_queue_ids)}",
            (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2,
        )
        cv2.putText(
            frame,
            f"Unique queue track IDs so far: {len(people)}",
            (30, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2,
        )

        video_writer.write(frame)

        if frames_processed % 30 == 0:
            print(
                f"Frames {frames_processed}/{total_frames} | "
                f"Current queue {len(current_queue_ids)} | "
                f"Unique queue IDs {len(people)}"
            )
finally:
    video_writer.release()

records = sorted(people.values(), key=lambda row: row["track_id"])
fields = [
    "track_id", "video_filename",
    "first_seen_video_second", "last_seen_video_second",
    "first_seen_frame", "last_seen_frame",
    "max_confidence", "snapshot_path",
]

with csv_path.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)

summary = {
    "video": VIDEO.name,
    "resolution": f"{width}x{height}",
    "fps": fps,
    "reported_frames": total_frames,
    "processed_frames": frames_processed,
    "unique_queue_track_ids": len(records),
    "processing_seconds": round(time.time() - started, 2),
    "model": MODEL_NAME,
    "tracker": "ByteTrack",
    "device": DEVICE,
    "queue_polygon": points,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "csv_path": str(csv_path.relative_to(ROOT)),
    "annotated_video_path": str(annotated_path.relative_to(ROOT)),
    "snapshots_folder": str(SNAPSHOTS.relative_to(ROOT)),
    "note": (
        "Counts are unique tracker IDs observed in the queue polygon. "
        "Tracker IDs can change after occlusion or re-entry. "
        "This test writes files only; it does not insert database records."
    ),
}
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("\n===== QUEUE TRACKING TEST COMPLETE =====")
print(json.dumps(summary, indent=2))
