
import json
from pathlib import Path

import cv2
import numpy as np

# =========================================================
# PROJECT PATHS
# =========================================================
ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = ROOT / "data" / "videos"
CONFIG_PATH = ROOT / "edge" / "config" / "video_regions.json"
OUTPUT_DIR = ROOT / "data" / "evidence" / "annotated_regions"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# PROVISIONAL REGION COORDINATES
# Coordinates are based on each video's original resolution.
# These are service-activity regions, NOT verified queue areas.
# =========================================================
PROPOSED_REGIONS = {
    "counter.mp4": {
        "description": "Wide-angle restaurant counter",
        "resolution": [2560, 1440],
        "region_key": "service_activity_region",
        "points": [
            [700, 650],
            [1500, 620],
            [1600, 1000],
            [850, 1250],
        ],
    },
    "normal_queue.mp4": {
        "description": "Vertical close-up of service counter",
        "resolution": [240, 426],
        "region_key": "service_activity_region",
        "points": [
            [5, 190],
            [230, 190],
            [230, 320],
            [5, 320],
        ],
    },
}


def load_existing_config():
    if not CONFIG_PATH.exists():
        return {}

    try:
        return json.loads(
            CONFIG_PATH.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON in {CONFIG_PATH}: {exc}"
        ) from exc


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )


def annotate_frame(frame, polygon, title):
    """Draw a translucent green polygon and numbered vertices."""
    image = frame.copy()
    overlay = frame.copy()
    points = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))

    cv2.fillPoly(overlay, [points], (0, 180, 80))
    image = cv2.addWeighted(overlay, 0.25, image, 0.75, 0)

    thickness = max(2, round(frame.shape[1] / 500))
    cv2.polylines(
        image,
        [points],
        True,
        (0, 255, 100),
        thickness,
    )

    radius = max(4, round(frame.shape[1] / 200))
    font_scale = 0.45 if frame.shape[1] < 500 else 0.8

    for index, (x, y) in enumerate(polygon, start=1):
        cv2.circle(image, (x, y), radius, (255, 255, 255), -1)
        cv2.circle(image, (x, y), radius, (0, 100, 40), 2)
        cv2.putText(
            image,
            str(index),
            (min(x + radius + 3, frame.shape[1] - 12),
             max(y - radius - 2, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 70, 30),
            1 if frame.shape[1] < 500 else 2,
            cv2.LINE_AA,
        )

    header_height = min(
        70,
        max(42, frame.shape[0] // 6),
    )
    cv2.rectangle(
        image,
        (0, 0),
        (frame.shape[1], header_height),
        (25, 25, 25),
        -1,
    )

    cv2.putText(
        image,
        title,
        (8, min(25, header_height - 18)),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (255, 255, 255),
        1 if frame.shape[1] < 500 else 2,
        cv2.LINE_AA,
    )

    cv2.putText(
        image,
        "GREEN = PROVISIONAL REGION - VERIFY",
        (8, header_height - 7),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.32 if frame.shape[1] < 500 else 0.55,
        (100, 255, 160),
        1,
        cv2.LINE_AA,
    )

    return image


def process_video(video_name, proposal, config):
    video_path = VIDEO_DIR / video_name

    if not video_path.exists():
        print(f"SKIPPED: Video not found: {video_path}")
        return False

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        cap.release()
        print(f"FAILED: Could not open {video_name}")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if frame_count <= 0:
        cap.release()
        print(f"FAILED: No frames reported for {video_name}")
        return False

    expected_width, expected_height = proposal["resolution"]

    if [width, height] != [expected_width, expected_height]:
        print(
            f"WARNING: {video_name} resolution is {width}x{height}; "
            f"the proposal was defined for "
            f"{expected_width}x{expected_height}."
        )

    polygon = proposal["points"]

    for x, y in polygon:
        if not (0 <= x < width and 0 <= y < height):
            cap.release()
            print(
                f"FAILED: Polygon point {(x, y)} lies outside "
                f"the {width}x{height} frame."
            )
            return False

    # Select a middle frame for visual inspection.
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 2)
    ok, frame = cap.read()
    cap.release()

    if not ok:
        print(f"FAILED: Could not read middle frame from {video_name}")
        return False

    # Preserve unrelated settings for this and other videos.
    video_config = config.setdefault(video_name, {})
    video_config["description"] = proposal["description"]
    video_config["resolution"] = [width, height]
    video_config[proposal["region_key"]] = polygon

    annotated = annotate_frame(
        frame,
        polygon,
        f"{video_name} | {proposal['region_key']}",
    )

    output_path = OUTPUT_DIR / (
        f"{Path(video_name).stem}_{proposal['region_key']}.jpg"
    )

    if not cv2.imwrite(str(output_path), annotated):
        print(f"FAILED: Could not write {output_path}")
        return False

    print(f"\nVideo: {video_name}")
    print(f"Actual resolution: {width} x {height}")
    print(f"Region points: {polygon}")
    print(f"Annotation saved: {output_path}")

    return True


def main():
    if not VIDEO_DIR.exists():
        raise SystemExit(f"Video folder not found: {VIDEO_DIR}")

    config = load_existing_config()
    success_count = 0

    for video_name, proposal in PROPOSED_REGIONS.items():
        if process_video(video_name, proposal, config):
            success_count += 1

    save_config(config)

    print("\n" + "=" * 60)
    print("REGION CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"Videos annotated: {success_count}/{len(PROPOSED_REGIONS)}")
    print(f"Configuration: {CONFIG_PATH}")
    print(f"Annotations: {OUTPUT_DIR}")
    print(
        "Reminder: These polygons are provisional activity regions, "
        "not verified queue boundaries."
    )


if __name__ == "__main__":
    main()
