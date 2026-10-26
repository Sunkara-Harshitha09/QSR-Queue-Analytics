import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "data" / "videos" / "counter.mp4"
CONFIG = ROOT / "edge" / "config" / "video_regions.json"
WINDOW = "Select QUEUE region - left-click points, S=save, C=clear, Esc=cancel"

if not VIDEO.exists():
    raise FileNotFoundError(f"Video not found: {VIDEO}")

cap = cv2.VideoCapture(str(VIDEO))
ok, frame = cap.read()
cap.release()
if not ok:
    raise RuntimeError("Could not read the first frame of counter.mp4")

height, width = frame.shape[:2]
max_width, max_height = 1280, 720
scale = min(max_width / width, max_height / height, 1.0)
preview = cv2.resize(frame, (int(width * scale), int(height * scale)))

points = []

def mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([int(round(x / scale)), int(round(y / scale))])

def draw():
    canvas = preview.copy()
    scaled = [(int(x * scale), int(y * scale)) for x, y in points]

    for i, p in enumerate(scaled):
        cv2.circle(canvas, p, 6, (0, 255, 255), -1)
        cv2.putText(canvas, str(i + 1), (p[0] + 7, p[1] - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

    if len(scaled) >= 2:
        cv2.polylines(canvas, [np.array(scaled, dtype=np.int32)],
                      False, (0, 255, 255), 2)
    if len(scaled) >= 3:
        cv2.polylines(canvas, [np.array(scaled, dtype=np.int32)],
                      True, (0, 255, 0), 2)

    cv2.putText(canvas, "Click queue boundary points in order",
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(canvas, "S=save (min 3 points) | C=clear | ESC=cancel",
                (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    return canvas

cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
cv2.setMouseCallback(WINDOW, mouse)

print(f"Video resolution: {width} x {height}")
print("Click at least 3 points around the actual queue waiting area.")
print("Click in order around the boundary; press S to save.")

while True:
    cv2.imshow(WINDOW, draw())
    key = cv2.waitKey(30) & 0xFF

    if key == 27:
        print("Cancelled. Configuration was not changed.")
        break
    elif key in (ord("c"), ord("C")):
        points.clear()
        print("Points cleared.")
    elif key in (ord("s"), ord("S")):
        if len(points) < 3:
            print("Please select at least 3 points.")
            continue

        polygon = np.array(points, dtype=np.int32)
        if not cv2.isContourConvex(polygon):
            print("Warning: polygon is not convex. Check that points follow the boundary.")
        if abs(cv2.contourArea(polygon)) < 100:
            print("Selected region is too small. Select the queue area again.")
            continue

        config = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}

        # Preserve the existing configuration and add/update only queue_region.
        if "counter.mp4" in config and isinstance(config["counter.mp4"], dict):
            config["counter.mp4"]["queue_region"] = points
            config["counter.mp4"]["video_width"] = width
            config["counter.mp4"]["video_height"] = height
        else:
            # Do not guess the existing schema if the file has an unexpected structure.
            raise ValueError(
                "Expected a top-level 'counter.mp4' object in video_regions.json. "
                "No config was saved; share the JSON file contents."
            )

        CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print("\nSaved queue polygon:")
        print(json.dumps(points, indent=2))
        print(f"Configuration updated: {CONFIG}")
        break

cv2.destroyAllWindows()
