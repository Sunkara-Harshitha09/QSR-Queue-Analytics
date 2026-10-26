import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "data" / "videos" / "normal_queue.mp4"
CONFIG = ROOT / "edge" / "config" / "video_regions.json"
WINDOW = "Select normal_queue QUEUE region"

with VIDEO.open("rb") as f:
    pass

cap = cv2.VideoCapture(str(VIDEO))
ok, frame = cap.read()
cap.release()
if not ok:
    raise RuntimeError(f"Could not read {VIDEO}")

height, width = frame.shape[:2]
scale = min(1000 / width, 750 / height, 1.0)
preview = cv2.resize(frame, (int(width * scale), int(height * scale)))
points = []

def draw():
    canvas = preview.copy()
    scaled = [(int(x * scale), int(y * scale)) for x, y in points]
    for i, p in enumerate(scaled):
        cv2.circle(canvas, p, 4, (0, 255, 255), -1)
        cv2.putText(canvas, str(i + 1), (p[0] + 5, p[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    if len(scaled) >= 2:
        cv2.polylines(canvas, [np.array(scaled, dtype=np.int32)],
                      len(scaled) >= 3, (0, 255, 0), 2)
    cv2.putText(canvas, "Click queue boundary | S=save | C=clear | ESC=cancel",
                (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
    return canvas

def mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([round(x / scale), round(y / scale)])

cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
cv2.setMouseCallback(WINDOW, mouse)

print(f"Video resolution: {width} x {height}")
print("Click at least 3 points around where customers actually wait.")
print("Press S to save, C to clear, Esc to cancel.")

try:
    while True:
        cv2.imshow(WINDOW, draw())
        key = cv2.waitKey(30) & 0xFF
        if key == 27:
            print("Cancelled; configuration unchanged.")
            break
        if key in (ord("c"), ord("C")):
            points.clear()
            print("Points cleared.")
        if key in (ord("s"), ord("S")):
            if len(points) < 3:
                print("Select at least 3 points first.")
                continue
            poly = np.array(points, dtype=np.int32)
            if abs(cv2.contourArea(poly)) < 10:
                print("Region is too small; select again.")
                continue

            config = json.loads(CONFIG.read_text(encoding="utf-8"))
            if "normal_queue.mp4" not in config:
                raise ValueError("normal_queue.mp4 entry is missing from config.")
            config["normal_queue.mp4"]["queue_region"] = points
            config["normal_queue.mp4"]["video_width"] = width
            config["normal_queue.mp4"]["video_height"] = height
            CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
            print("Saved normal_queue.mp4 queue polygon:")
            print(json.dumps(points, indent=2))
            print(f"Updated {CONFIG}")
            break
finally:
    cv2.destroyAllWindows()
