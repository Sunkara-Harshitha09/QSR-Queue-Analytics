
from django.db import models


class ProcessingRun(models.Model):
    id = models.BigIntegerField(primary_key=True)
    video_filename = models.TextField()
    measurement_method = models.TextField()
    region_type = models.TextField()
    video_width = models.IntegerField()
    video_height = models.IntegerField()
    video_fps = models.FloatField()
    video_duration_seconds = models.FloatField()
    region_pixels = models.IntegerField()
    warmup_frames_skipped = models.IntegerField()
    status = models.TextField()
    started_at = models.DateTimeField()
    notes = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "processing_runs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.video_filename} - {self.status}"


class ActivityMeasurement(models.Model):
    id = models.BigIntegerField(primary_key=True)

    processing_run = models.ForeignKey(
        ProcessingRun,
        db_column="processing_run_id",
        on_delete=models.DO_NOTHING,
        related_name="measurements",
    )

    video_second = models.IntegerField()
    sample_count = models.IntegerField()
    mean_foreground_pixels = models.FloatField()
    mean_foreground_percent = models.FloatField()
    mean_large_foreground_blobs = models.FloatField()
    measurement_type = models.TextField()

    class Meta:
        managed = False
        db_table = "activity_measurements"
        ordering = ["video_second"]

    def __str__(self):
        return (
            f"Run {self.processing_run_id}, "
            f"second {self.video_second}"
        )
from django.db import models
from django.contrib.auth.models import User


class QueueThreshold(models.Model):
    queue_people_threshold = models.PositiveIntegerField(default=5)
    waiting_minutes_threshold = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Queue Threshold"
        verbose_name_plural = "Queue Thresholds"

    def __str__(self):
        return (
            f"Queue: {self.queue_people_threshold} people, "
            f"Waiting: {self.waiting_minutes_threshold} minutes"
        )