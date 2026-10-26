
import cv2
import json
from pathlib import Path
from datetime import datetime, timezone

# --------------------------------------------------
# 1. PROJECT PATHS
# File location: QSR_Queue_Analytics/edge/src/
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VIDEO_DIR = PROJECT_ROOT / "data" / "videos"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
FRAME_DIR = PROJECT_ROOT / "data" / "evidence" / "sample_frames"

LOG_DIR.mkdir(parents=True, exist_ok=True)
FRAME_DIR.mkdir(parents=True, exist_ok=True)

REPORT_PATH = LOG_DIR / "video_inspection.json"

# --------------------------------------------------
# 2. CHECK VIDEO DIRECTORY
# --------------------------------------------------

print("=" * 60)
print("QSR QUEUE ANALYTICS - VIDEO INSPECTION")
print("=" * 60)
print(f"Project root : {PROJECT_ROOT}")
print(f"Video folder : {VIDEO_DIR}")
print(f"Report path  : {REPORT_PATH}")

if not VIDEO_DIR.exists():
    raise SystemExit(f"ERROR: Video folder does not exist: {VIDEO_DIR}")

video_files = sorted(
    file for file in VIDEO_DIR.iterdir()
    if file.is_file() and file.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}
)

if not video_files:
    raise SystemExit(
        "ERROR: No supported videos found in data/videos. "
        "Add your MP4 files and run this script again."
    )

# --------------------------------------------------
# 3. INSPECT EACH VIDEO
# --------------------------------------------------

results = []

for video_path in video_files:
    print("\n" + "-" * 60)
    print(f"Video: {video_path.name}")

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print("Status: FAILED TO OPEN")
        results.append({
            "filename": video_path.name,
            "status": "failed_to_open",
            "error": "OpenCV could not open this video.",
        })
        cap.release()
        continue

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    reported_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    duration_seconds = (
        reported_frames / fps
        if fps > 0 and reported_frames > 0
        else None
    )

    print("Status            : OPENED")
    print(f"Resolution        : {width} x {height}")
    print(f"FPS               : {fps:.3f}")
    print(f"Reported frames   : {reported_frames}")
    print(
        f"Reported duration : {duration_seconds:.2f} seconds"
        if duration_seconds is not None
        else "Reported duration: unavailable"
    )

    # Save frames from the start, middle, and end.
    sample_positions = {
        "start": 0,
        "middle": max(0, reported_frames // 2),
        "end": max(0, reported_frames - 1),
    }

    saved_frames = []

    for label, frame_index in sample_positions.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = cap.read()

        if not success:
            print(f"Sample frame '{label}': could not read")
            continue

        output_name = f"{video_path.stem}_{label}.jpg"
        output_path = FRAME_DIR / output_name

        if cv2.imwrite(str(output_path), frame):
            relative_path = output_path.relative_to(PROJECT_ROOT).as_posix()
            saved_frames.append(relative_path)
            print(f"Sample frame saved: {relative_path}")
        else:
            print(f"ERROR: Could not save {output_path.name}")

    cap.release()

    results.append({
        "filename": video_path.name,
        "status": "inspected",
        "file_size_bytes": video_path.stat().st_size,
        "width": width,
        "height": height,
        "fps": fps,
        "reported_frame_count": reported_frames,
        "reported_duration_seconds": duration_seconds,
        "sample_frames": saved_frames,
    })

# --------------------------------------------------
# 4. SAVE INSPECTION REPORT
# --------------------------------------------------

report = {
    "application": "QSR Queue Analytics",
    "report_type": "video_inspection",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "project_root": str(PROJECT_ROOT),
    "video_count": len(video_files),
    "success_count": sum(
        item["status"] == "inspected" for item in results
    ),
    "failure_count": sum(
        item["status"] != "inspected" for item in results
    ),
    "videos": results,
}

REPORT_PATH.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

# --------------------------------------------------
# 5. SUMMARY
# --------------------------------------------------

print("\n" + "=" * 60)
print("INSPECTION SUMMARY")
print("=" * 60)
print(f"Videos discovered : {len(video_files)}")
print(f"Successfully read : {report['success_count']}")
print(f"Failed to read    : {report['failure_count']}")
print(f"JSON report       : {REPORT_PATH}")
print(f"Sample frames     : {FRAME_DIR}")
print("=" * 60)
