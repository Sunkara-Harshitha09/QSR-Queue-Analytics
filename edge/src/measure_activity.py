
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import cv2
import numpy as np
import psycopg

# =========================================================
# PROJECT PATHS
# =========================================================
ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = ROOT / "data" / "videos"
CONFIG_PATH = ROOT / "edge" / "config" / "video_regions.json"
OUTPUT_DIR = ROOT / "data" / "logs"
ENV_PATH = ROOT / ".env"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# MEASUREMENT SETTINGS
# =========================================================
SAMPLE_INTERVAL_SECONDS = 1.0
MIN_CONTOUR_AREA = 500
LEARNING_RATE = 0.005
WARMUP_SECONDS = 2.0


# =========================================================
# ENVIRONMENT AND DATABASE CONNECTION
# =========================================================
def load_env_file():
    """Load root .env values without overriding existing environment variables."""
    if not ENV_PATH.exists():
        raise RuntimeError(f"Root .env file not found: {ENV_PATH}")

    for raw_line in ENV_PATH.read_text(
        encoding="utf-8-sig"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        if key and key not in os.environ:
            os.environ[key] = value


def get_database_url():
    """Normalize PostgreSQL URL and safely encode special password characters."""
    load_env_file()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing from the root .env file."
        )

    database_url = database_url.strip()

    # Remove SQLAlchemy driver suffixes for direct Psycopg connections.
    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
    elif database_url.startswith("postgresql+psycopg2://"):
        database_url = database_url.replace(
            "postgresql+psycopg2://", "postgresql://", 1
        )

    try:
        parsed = urlsplit(database_url)

        if parsed.scheme not in {"postgresql", "postgres"}:
            raise RuntimeError(
                "DATABASE_URL must use a PostgreSQL URL scheme."
            )

        if not parsed.hostname:
            raise RuntimeError(
                "DATABASE_URL does not contain a valid hostname."
            )

        # Read username and password separately, then encode the password.
        username = parsed.username
        password = parsed.password

        if username is None or password is None:
            raise RuntimeError(
                "DATABASE_URL must include a username and password."
            )

        encoded_username = quote(unquote(username), safe="")
        encoded_password = quote(unquote(password), safe="")

        host = parsed.hostname
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"

        port = f":{parsed.port}" if parsed.port else ""

        netloc = (
            f"{encoded_username}:{encoded_password}@{host}{port}"
        )

        return urlunsplit((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        ))

    except ValueError as exc:
        raise RuntimeError(
            "DATABASE_URL is malformed. Check its host and port "
            "in the root .env file without sharing its credentials."
        ) from exc


def connect_database():
    """Connect and confirm that the required tables exist."""
    connection = psycopg.connect(
        get_database_url(),
        connect_timeout=5,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'processing_runs',
                      'activity_measurements'
                  )
                """
            )
            tables = {row[0] for row in cursor.fetchall()}

        required = {
            "processing_runs",
            "activity_measurements",
        }
        missing = required - tables

        if missing:
            raise RuntimeError(
                "Missing database tables: "
                + ", ".join(sorted(missing))
            )

        connection.commit()
        return connection

    except Exception:
        connection.close()
        raise


# =========================================================
# REGION CONFIGURATION
# =========================================================
def get_region(settings):
    if settings.get("service_activity_region"):
        return (
            settings["service_activity_region"],
            "service_activity_region",
        )

    if settings.get("queue_region"):
        return settings["queue_region"], "queue_region"

    return None, None


# =========================================================
# VIDEO PROCESSING
# =========================================================
def process_video(video_name, settings, run_time):
    video_path = VIDEO_DIR / video_name
    polygon_points, region_type = get_region(settings)

    if not video_path.exists():
        print(f"\nSKIPPED: Video not found: {video_name}")
        return None

    if not polygon_points or len(polygon_points) < 3:
        print(
            f"\nSKIPPED: No valid region configured for {video_name}"
        )
        return None

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        cap.release()
        print(f"\nFAILED: Could not open {video_name}")
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0 or total_frames <= 0:
        cap.release()
        print(f"\nFAILED: Invalid video metadata for {video_name}")
        return None

    duration = total_frames / fps

    configured_resolution = settings.get("resolution")
    if configured_resolution and configured_resolution != [width, height]:
        print(
            f"WARNING: Configured resolution {configured_resolution} "
            f"differs from actual {[width, height]}. "
            "Verify polygon coordinates."
        )

    polygon = np.array(polygon_points, dtype=np.int32)
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)

    region_pixels = int(cv2.countNonZero(mask))

    if region_pixels == 0:
        cap.release()
        print(f"\nFAILED: Region mask is empty for {video_name}")
        return None

    subtractor = cv2.createBackgroundSubtractorMOG2(
        history=300,
        varThreshold=32,
        detectShadows=False,
    )

    sample_step = max(
        1, round(fps * SAMPLE_INTERVAL_SECONDS)
    )
    warmup_frames = min(
        total_frames // 3,
        max(1, round(fps * WARMUP_SECONDS)),
    )

    buckets = {}
    frame_index = 0
    processed_samples = 0

    print("\n" + "-" * 60)
    print(f"Video          : {video_name}")
    print(f"Resolution     : {width} x {height}")
    print(f"FPS            : {fps:.3f}")
    print(f"Duration       : {duration:.3f} seconds")
    print(f"Region type    : {region_type}")
    print(f"Region pixels  : {region_pixels}")
    print(f"Warm-up frames : {warmup_frames}")
    print("-" * 60)

    while True:
        ok, frame = cap.read()

        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Warm up the background model without recording measurements.
        if frame_index < warmup_frames:
            subtractor.apply(gray, learningRate=LEARNING_RATE)
            frame_index += 1
            continue

        foreground = subtractor.apply(
            gray,
            learningRate=LEARNING_RATE,
        )
        foreground = cv2.bitwise_and(foreground, mask)

        if frame_index % sample_step == 0:
            foreground = cv2.medianBlur(foreground, 5)
            _, foreground = cv2.threshold(
                foreground, 200, 255, cv2.THRESH_BINARY
            )

            kernel = np.ones((3, 3), dtype=np.uint8)
            foreground = cv2.morphologyEx(
                foreground,
                cv2.MORPH_OPEN,
                kernel,
            )

            foreground_pixels = int(
                cv2.countNonZero(foreground)
            )
            foreground_percent = (
                100.0 * foreground_pixels / region_pixels
            )

            contours, _ = cv2.findContours(
                foreground,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )

            large_blobs = sum(
                1
                for contour in contours
                if cv2.contourArea(contour) >= MIN_CONTOUR_AREA
            )

            # Retain the original video timestamp.
            second = int(frame_index / fps)

            bucket = buckets.setdefault(
                second,
                {
                    "sample_count": 0,
                    "foreground_pixels_sum": 0,
                    "foreground_percent_sum": 0.0,
                    "large_blob_count_sum": 0,
                },
            )

            bucket["sample_count"] += 1
            bucket["foreground_pixels_sum"] += foreground_pixels
            bucket["foreground_percent_sum"] += foreground_percent
            bucket["large_blob_count_sum"] += large_blobs
            processed_samples += 1

        frame_index += 1

    cap.release()

    rows = []

    for second, values in sorted(buckets.items()):
        count = values["sample_count"]

        rows.append({
            "video": video_name,
            "second": second,
            "sample_count": count,
            "mean_foreground_pixels": round(
                values["foreground_pixels_sum"] / count, 2
            ),
            "mean_foreground_percent": round(
                values["foreground_percent_sum"] / count, 4
            ),
            "mean_large_foreground_blobs": round(
                values["large_blob_count_sum"] / count, 2
            ),
            "region_type": region_type,
            "measurement_type": "foreground_activity_proxy",
        })

    # Save CSV report.
    output_csv = OUTPUT_DIR / f"activity_{Path(video_name).stem}.csv"
    csv_fields = [
        "video",
        "second",
        "sample_count",
        "mean_foreground_pixels",
        "mean_foreground_percent",
        "mean_large_foreground_blobs",
        "region_type",
        "measurement_type",
    ]

    with output_csv.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(rows)

    percentages = [
        row["mean_foreground_percent"] for row in rows
    ]

    summary = {
        "video": video_name,
        "status": "completed",
        "generated_at_utc": run_time,
        "resolution": [width, height],
        "fps": fps,
        "duration_seconds": round(duration, 3),
        "region_type": region_type,
        "region_pixels": region_pixels,
        "warmup_frames_skipped": warmup_frames,
        "sample_count": processed_samples,
        "seconds_measured": len(rows),
        "mean_foreground_percent": round(
            float(np.mean(percentages)), 4
        ) if percentages else None,
        "csv_file": output_csv.relative_to(ROOT).as_posix(),
        "measurement_type": "foreground_activity_proxy",
        "limitations": [
            "Foreground activity is not a verified customer count.",
            "Warm-up reduces but may not eliminate startup artifacts.",
            "Lighting, shadows, staff movement, and camera movement affect results.",
            "Large foreground blobs are not people.",
            "Waiting time and abandonment are not measured.",
            "The configured region is not validated as queue-only.",
        ],
    }

    print(f"Samples recorded: {processed_samples}")
    print(f"CSV saved       : {output_csv}")

    return {
        "summary": summary,
        "rows": rows,
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "region_pixels": region_pixels,
        "warmup_frames": warmup_frames,
        "region_type": region_type,
    }


# =========================================================
# SAVE RESULTS TO POSTGRESQL
# =========================================================
def save_run_to_database(connection, video_name, result):
    """Save run metadata and measurements in one transaction."""
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO processing_runs (
                    video_filename,
                    measurement_method,
                    region_type,
                    video_width,
                    video_height,
                    video_fps,
                    video_duration_seconds,
                    region_pixels,
                    warmup_frames_skipped,
                    status,
                    notes
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    video_name,
                    "OpenCV MOG2 background subtraction",
                    result["region_type"],
                    result["width"],
                    result["height"],
                    result["fps"],
                    result["duration"],
                    result["region_pixels"],
                    result["warmup_frames"],
                    "completed",
                    "Foreground activity proxy, not a verified "
                    "customer count. Queue region not independently "
                    "validated.",
                ),
            )

            run_id = cursor.fetchone()[0]

            measurement_values = [
                (
                    run_id,
                    row["second"],
                    row["sample_count"],
                    row["mean_foreground_pixels"],
                    row["mean_foreground_percent"],
                    row["mean_large_foreground_blobs"],
                    row["measurement_type"],
                )
                for row in result["rows"]
            ]

            if measurement_values:
                cursor.executemany(
                    """
                    INSERT INTO activity_measurements (
                        processing_run_id,
                        video_second,
                        sample_count,
                        mean_foreground_pixels,
                        mean_foreground_percent,
                        mean_large_foreground_blobs,
                        measurement_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    measurement_values,
                )

    return run_id


# =========================================================
# MAIN
# =========================================================
def main():
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"Configuration file not found: {CONFIG_PATH}"
        )

    if not VIDEO_DIR.exists():
        raise SystemExit(f"Video folder not found: {VIDEO_DIR}")

    try:
        config = json.loads(
            CONFIG_PATH.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid region configuration JSON: {exc}")

    try:
        connection = connect_database()
    except Exception as exc:
        # Do not print the connection URL or credentials.
        raise SystemExit(
            "PostgreSQL connection failed. Check that Docker is running, "
            "the root .env DATABASE_URL is correct, and the required tables "
            "exist. Sensitive connection details were not printed. "
            f"Error type: {type(exc).__name__}; details: {exc}"
        ) from exc

    run_time = datetime.now(timezone.utc).isoformat()
    summaries = []
    saved_runs = 0

    print("=" * 60)
    print("QSR QUEUE ANALYTICS")
    print("OpenCV foreground activity + PostgreSQL")
    print("Activity is a proxy, not a verified customer count.")
    print("Database connection and tables verified.")
    print("=" * 60)

    try:
        for video_name, settings in config.items():
            result = process_video(video_name, settings, run_time)

            if result is None:
                continue

            try:
                run_id = save_run_to_database(
                    connection, video_name, result
                )
            except Exception as exc:
                print(
                    f"DATABASE SAVE FAILED for {video_name}: "
                    f"{type(exc).__name__}: {exc}"
                )
                raise

            saved_runs += 1
            result["summary"]["database_run_id"] = run_id
            result["summary"]["database_measurements_saved"] = len(
                result["rows"]
            )
            summaries.append(result["summary"])

            print(f"Database run ID : {run_id}")
            print(
                "Measurements saved to PostgreSQL: "
                f"{len(result['rows'])}"
            )

    finally:
        connection.close()

    report = {
        "application": "QSR Queue Analytics",
        "generated_at_utc": run_time,
        "method": "OpenCV MOG2 background subtraction",
        "measurement_warning": (
            "Foreground activity is a proxy, not a verified customer count."
        ),
        "videos_measured": len(summaries),
        "videos_saved_to_database": saved_runs,
        "results": summaries,
    }

    report_path = OUTPUT_DIR / "activity_measurement_summary.json"
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print(f"Videos measured          : {len(summaries)}")
    print(f"Videos saved to database : {saved_runs}")
    print(f"Summary report            : {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
