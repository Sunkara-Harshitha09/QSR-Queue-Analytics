import csv
import json
from pathlib import Path
from sqlalchemy.engine import make_url
import psycopg

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "evidence" / "queue_tracking"

def read_database_url():
    env_file = ROOT / ".env"

    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            raw = line.split("=", 1)[1].strip().strip('"').strip("'")
            if raw:
                # Parse URL correctly, including special characters in passwords.
                url = make_url(raw)
                if url.drivername.startswith("postgresql+"):
                    url = url.set(drivername="postgresql")
                return url

    raise RuntimeError("DATABASE_URL is missing from the project .env file.")

def main():
    db_url = read_database_url()
    total_people = 0
    total_runs = 0

    # Pass parsed parameters instead of a raw URL to psycopg.
    connection_args = {
        "host": db_url.host,
        "port": db_url.port or 5432,
        "dbname": db_url.database,
        "user": db_url.username,
        "password": db_url.password,
    }

    with psycopg.connect(**connection_args) as conn:
        with conn.cursor() as cur:
            for video in ("counter.mp4", "normal_queue.mp4"):
                folder = BASE / Path(video).stem
                csv_path = folder / "person_records.csv"
                summary_path = folder / "summary.json"

                if not csv_path.exists() or not summary_path.exists():
                    raise FileNotFoundError(f"Missing tracking results for {video}")

                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
                    rows = list(csv.DictReader(f))

                for row in rows:
                    cur.execute(
                        """
                        INSERT INTO public.queue_person_tracks (
                            video_filename, track_id,
                            first_seen_video_second, last_seen_video_second,
                            first_seen_frame, last_seen_frame,
                            max_confidence, snapshot_path
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (video_filename, track_id)
                        DO UPDATE SET
                            first_seen_video_second = EXCLUDED.first_seen_video_second,
                            last_seen_video_second = EXCLUDED.last_seen_video_second,
                            first_seen_frame = EXCLUDED.first_seen_frame,
                            last_seen_frame = EXCLUDED.last_seen_frame,
                            max_confidence = EXCLUDED.max_confidence,
                            snapshot_path = EXCLUDED.snapshot_path
                        """,
                        (
                            row["video_filename"],
                            int(row["track_id"]),
                            float(row["first_seen_video_second"]),
                            float(row["last_seen_video_second"]),
                            int(row["first_seen_frame"]),
                            int(row["last_seen_frame"]),
                            float(row["max_confidence"]),
                            row["snapshot_path"],
                        ),
                    )
                    total_people += 1

                cur.execute(
                    """
                    INSERT INTO public.queue_tracking_runs (
                        video_filename, resolution, fps,
                        reported_frames, processed_frames,
                        unique_queue_track_ids, processing_seconds,
                        model_name, tracker_name, device,
                        annotated_video_path, snapshots_folder, generated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        summary["video"],
                        summary["resolution"],
                        summary["fps"],
                        summary["reported_frames"],
                        summary["processed_frames"],
                        summary["unique_queue_track_ids"],
                        summary["processing_seconds"],
                        summary["model"],
                        summary["tracker"],
                        summary["device"],
                        summary["annotated_video_path"],
                        summary["snapshots_folder"],
                        summary["generated_at_utc"],
                    ),
                )
                total_runs += 1
                print(f"{video}: processed {len(rows)} person records")

    print("\nDatabase import completed.")
    print(f"Person records processed: {total_people}")
    print(f"Video summaries inserted: {total_runs}")

if __name__ == "__main__":
    main()
