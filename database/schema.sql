
CREATE TABLE IF NOT EXISTS processing_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    video_filename TEXT NOT NULL,
    measurement_method TEXT NOT NULL,
    region_type TEXT NOT NULL,
    video_width INTEGER NOT NULL CHECK (video_width > 0),
    video_height INTEGER NOT NULL CHECK (video_height > 0),
    video_fps DOUBLE PRECISION NOT NULL CHECK (video_fps > 0),
    video_duration_seconds DOUBLE PRECISION NOT NULL
        CHECK (video_duration_seconds >= 0),
    region_pixels INTEGER NOT NULL CHECK (region_pixels > 0),
    warmup_frames_skipped INTEGER NOT NULL DEFAULT 0
        CHECK (warmup_frames_skipped >= 0),
    status TEXT NOT NULL DEFAULT 'completed'
        CHECK (status IN ('completed', 'failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS activity_measurements (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processing_run_id BIGINT NOT NULL
        REFERENCES processing_runs(id) ON DELETE CASCADE,
    video_second INTEGER NOT NULL CHECK (video_second >= 0),
    sample_count INTEGER NOT NULL CHECK (sample_count > 0),
    mean_foreground_pixels DOUBLE PRECISION NOT NULL
        CHECK (mean_foreground_pixels >= 0),
    mean_foreground_percent DOUBLE PRECISION NOT NULL
        CHECK (
            mean_foreground_percent >= 0
            AND mean_foreground_percent <= 100
        ),
    mean_large_foreground_blobs DOUBLE PRECISION NOT NULL
        CHECK (mean_large_foreground_blobs >= 0),
    measurement_type TEXT NOT NULL
        DEFAULT 'foreground_activity_proxy',
    UNIQUE (processing_run_id, video_second)
);

CREATE INDEX IF NOT EXISTS idx_processing_runs_video
    ON processing_runs (video_filename);

CREATE INDEX IF NOT EXISTS idx_activity_measurements_run_second
    ON activity_measurements (processing_run_id, video_second);
