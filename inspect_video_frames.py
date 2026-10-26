from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parent
VIDEO_DIR = ROOT / "data" / "videos"
OUT_DIR = ROOT / "data" / "evidence" / "sample_frames" / "inspection"
OUT_DIR.mkdir(parents=True, exist_ok=True)

for filename in ["counter.mp4", "normal_queue.mp4"]:
    video_path = VIDEO_DIR / filename

    if not video_path.exists():
        print(f"NOT FOUND: {video_path}")
        continue

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0

    print(f"\n{filename}: {frame_count} frames, {fps:.2f} FPS, {duration:.2f}s")

    if frame_count <= 0 or fps <= 0:
        print("Could not read video metadata.")
        cap.release()
        continue

    times = [duration * f for f in (0.05, 0.275, 0.5, 0.725, 0.95)]
    tiles = []

    for i, second in enumerate(times, start=1):
        cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
        ok, frame = cap.read()

        if not ok:
            print(f"Could not read frame at {second:.2f}s")
            continue

        height, width = frame.shape[:2]
        scale = min(480 / width, 300 / height)
        resized = cv2.resize(frame, (int(width * scale), int(height * scale)))

        tile = cv2.copyMakeBorder(
            resized, 30, 0, 0, 0,
            cv2.BORDER_CONSTANT, value=(30, 30, 30)
        )
        cv2.putText(
            tile, f"{filename} | {second:.1f}s", (8, 21),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55,
            (255, 255, 255), 1, cv2.LINE_AA
        )

        frame_path = OUT_DIR / f"{Path(filename).stem}_{i}.jpg"
        cv2.imwrite(str(frame_path), frame)
        tiles.append(tile)
        print(f"Saved: {frame_path}")

    cap.release()

    if tiles:
        sheet_width = max(tile.shape[1] for tile in tiles)
        normalized = []

        for tile in tiles:
            if tile.shape[1] < sheet_width:
                tile = cv2.copyMakeBorder(
                    tile, 0, 0, 0, sheet_width - tile.shape[1],
                    cv2.BORDER_CONSTANT, value=(30, 30, 30)
                )
            normalized.append(tile)

        sheet = cv2.vconcat(normalized)
        sheet_path = OUT_DIR / f"{Path(filename).stem}_contact_sheet.jpg"
        cv2.imwrite(str(sheet_path), sheet)
        print(f"CONTACT SHEET: {sheet_path}")

print("\nFrame inspection completed.")
