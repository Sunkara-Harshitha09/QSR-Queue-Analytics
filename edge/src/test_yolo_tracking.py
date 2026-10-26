import csv
import json
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "data" / "videos" / "counter.mp4"
OUT = ROOT / "data" / "evidence" / "yolo_tracking_test"
SNAPSHOTS = OUT / "snapshots"

OUT.mkdir(parents=True, exist_ok=True)
SNAPSHOTS.mkdir(parents=True, exist_ok=True)

if not VIDEO.exists():
    raise FileNotFoundError(f"Input video not found: {VIDEO}")

print("Loading YOLO11n model...")
model = YOLO("yolo11n.pt")

cap = cv2.VideoCapture(str(VIDEO))
if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {VIDEO}")

fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()

tracks = {}
annotated_path = OUT / "counter_yolo_tracking.mp4"
writer = cv2.VideoWriter(
    str(annotated_path),
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (width, height),
)

if not writer.isOpened():
    raise RuntimeError("Could not create annotated output video.")

started = time.time()
frames_processed = 0

try:
    results = model.track(
        source=str(VIDEO),
        stream=True,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],
        conf=0.25,
        imgsz=640,
        device="cpu",
        verbose=False,
    )

    for result in results:
        frame = result.orig_img
        frames_processed += 1
        frame_index = int(result.path and result.boxes is not None and frames_processed - 1 or frames_processed - 1)
        video_second = frame_index / fps

        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes
            if boxes.id is not None:
                ids = boxes.id.int().cpu().tolist()
                xyxy = boxes.xyxy.cpu().tolist()
                confs = boxes.conf.cpu().tolist()

                for track_id, box, confidence in zip(ids, xyxy, confs):
                    key = str(track_id)
                    x1, y1, x2, y2 = [int(v) for v in box]

                    if key not in tracks:
                        snapshot = SNAPSHOTS / f"person_track_{track_id}.jpg"
                        crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
                        if crop.size:
                            cv2.imwrite(str(snapshot), crop)

                        tracks[key] = {
                            "track_id": int(track_id),
                            "video_filename": VIDEO.name,
                            "first_seen_video_second": round(video_second, 3),
                            "last_seen_video_second": round(video_second, 3),
                            "first_seen_frame": frame_index,
                            "last_seen_frame": frame_index,
                            "max_confidence": round(float(confidence), 4),
                            "snapshot_path": str(snapshot.relative_to(ROOT)) if snapshot.exists() else "",
                        }
                    else:
                        tracks[key]["last_seen_video_second"] = round(video_second, 3)
                        tracks[key]["last_seen_frame"] = frame_index
                        tracks[key]["max_confidence"] = max(
                            tracks[key]["max_confidence"], round(float(confidence), 4)
                        )

        annotated = result.plot()
        writer.write(annotated)

        if frames_processed % 30 == 0:
            print(f"Processed {frames_processed}/{frame_count} frames; unique track IDs so far: {len(tracks)}")

finally:
    writer.release()

records = sorted(tracks.values(), key=lambda x: x["track_id"])
csv_path = OUT / "person_tracks.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    fieldnames = [
        "track_id", "video_filename",
        "first_seen_video_second", "last_seen_video_second",
        "first_seen_frame", "last_seen_frame",
        "max_confidence", "snapshot_path",
    ]
    writer_csv = csv.DictWriter(f, fieldnames=fieldnames)
    writer_csv.writeheader()
    writer_csv.writerows(records)

summary = {
    "video": VIDEO.name,
    "video_width": width,
    "video_height": height,
    "fps": fps,
    "reported_frames": frame_count,
    "processed_frames": frames_processed,
    "unique_track_ids": len(records),
    "processing_seconds": round(time.time() - started, 2),
    "device": "cpu",
    "model": "yolo11n.pt",
    "tracker": "ByteTrack",
    "note": "Initial tracking test only. Track IDs can switch after occlusion or re-entry; validate snapshots and the annotated video before treating the count as ground truth.",
    "csv": str(csv_path.relative_to(ROOT)),
    "annotated_video": str(annotated_path.relative_to(ROOT)),
    "snapshots_folder": str(SNAPSHOTS.relative_to(ROOT)),
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("\n===== YOLO TRACKING TEST SUMMARY =====")
print(json.dumps(summary, indent=2))
