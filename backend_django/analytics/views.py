
from django.db import connection
from django.db.models import Avg, Count, Max
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime, parse_date
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import AllowAny

from .models import ProcessingRun, ActivityMeasurement


def serialize_run(run):
    return {
        "id": run.id,
        "video_filename": run.video_filename,
        "measurement_method": run.measurement_method,
        "region_type": run.region_type,
        "video_width": run.video_width,
        "video_height": run.video_height,
        "video_fps": run.video_fps,
        "video_duration_seconds": run.video_duration_seconds,
        "region_pixels": run.region_pixels,
        "warmup_frames_skipped": run.warmup_frames_skipped,
        "status": run.status,
        "started_at": (
            run.started_at.isoformat() if run.started_at else None
        ),
        "notes": run.notes,
    }


def serialize_measurement(item):
    return {
        "id": item.id,
        "processing_run_id": item.processing_run_id,
        "video_filename": item.processing_run.video_filename,
        "video_second": item.video_second,
        "sample_count": item.sample_count,
        "mean_foreground_pixels": item.mean_foreground_pixels,
        "mean_foreground_percent": item.mean_foreground_percent,
        "mean_large_foreground_blobs": (
            item.mean_large_foreground_blobs
        ),
        "measurement_type": item.measurement_type,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return JsonResponse({
            "status": "healthy",
            "database": "connected",
        })
    except Exception:
        return JsonResponse({
            "status": "unhealthy",
            "database": "unavailable",
        }, status=503)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard(request):
    run_count = ProcessingRun.objects.count()
    completed_runs = ProcessingRun.objects.filter(
        status="completed"
    ).count()
    failed_runs = ProcessingRun.objects.filter(
        status="failed"
    ).count()

    measurement_stats = ActivityMeasurement.objects.aggregate(
        total_measurements=Count("id"),
        average_foreground_percent=Avg(
            "mean_foreground_percent"
        ),
        latest_video_second=Max("video_second"),
    )

    recent_runs = ProcessingRun.objects.order_by(
        "-started_at"
    )[:10]

    return JsonResponse({
        "processing_runs": run_count,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs,
        "total_measurements": (
            measurement_stats["total_measurements"] or 0
        ),
        "average_foreground_percent": (
            measurement_stats["average_foreground_percent"]
        ),
        "latest_video_second": (
            measurement_stats["latest_video_second"]
        ),
        "recent_runs": [
            serialize_run(run) for run in recent_runs
        ],
        "metric_note": (
            "Foreground activity proxy from OpenCV; "
            "not a verified customer count or queue waiting time."
        ),
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def processing_runs(request):
    queryset = ProcessingRun.objects.order_by("-started_at")

    status_value = request.query_params.get("status")
    if status_value in {"completed", "failed"}:
        queryset = queryset.filter(status=status_value)

    filename = request.query_params.get("video_filename")
    if filename:
        queryset = queryset.filter(video_filename__icontains=filename)

    try:
        limit = int(request.query_params.get("limit", "100"))
    except ValueError:
        return JsonResponse(
            {"error": "limit must be an integer"},
            status=400,
        )

    if not 1 <= limit <= 500:
        return JsonResponse(
            {"error": "limit must be between 1 and 500"},
            status=400,
        )

    return JsonResponse({
        "count": queryset.count(),
        "results": [
            serialize_run(run) for run in queryset[:limit]
        ],
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def measurements(request):
    queryset = ActivityMeasurement.objects.select_related(
        "processing_run"
    ).order_by("processing_run_id", "video_second")

    run_id = request.query_params.get("processing_run_id")
    if run_id:
        try:
            queryset = queryset.filter(
                processing_run_id=int(run_id)
            )
        except ValueError:
            return JsonResponse(
                {"error": "processing_run_id must be an integer"},
                status=400,
            )

    filename = request.query_params.get("video_filename")
    if filename:
        queryset = queryset.filter(
            processing_run__video_filename__icontains=filename
        )

    start_second = request.query_params.get("start_second")
    if start_second:
        try:
            queryset = queryset.filter(
                video_second__gte=int(start_second)
            )
        except ValueError:
            return JsonResponse(
                {"error": "start_second must be an integer"},
                status=400,
            )

    end_second = request.query_params.get("end_second")
    if end_second:
        try:
            queryset = queryset.filter(
                video_second__lte=int(end_second)
            )
        except ValueError:
            return JsonResponse(
                {"error": "end_second must be an integer"},
                status=400,
            )

    try:
        limit = int(request.query_params.get("limit", "500"))
    except ValueError:
        return JsonResponse(
            {"error": "limit must be an integer"},
            status=400,
        )

    if not 1 <= limit <= 2000:
        return JsonResponse(
            {"error": "limit must be between 1 and 2000"},
            status=400,
        )

    return JsonResponse({
        "count": queryset.count(),
        "results": [
            serialize_measurement(item) for item in queryset[:limit]
        ],
        "metric_note": (
            "Foreground activity proxy; not a verified customer count."
        ),
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def queue_estimates(request):
    """
    Summarize the existing recorded-video tracking results.
    These are historical observations, not live queue measurements.
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                video_filename,
                COUNT(*) AS track_records,
                COUNT(DISTINCT track_id) AS distinct_track_ids,
                AVG(
                    GREATEST(
                        0,
                        last_seen_video_second - first_seen_video_second
                    )
                ) AS avg_observed_seconds,
                MAX(last_seen_video_second) AS last_observed_second
            FROM public.queue_person_tracks
            WHERE video_filename IN (%s, %s)
            GROUP BY video_filename
            ORDER BY video_filename
        """, ["counter.mp4", "normal_queue.mp4"])

        videos = _fetch_rows_as_dicts(cursor)

    results = []
    for video in videos:
        results.append({
            "video_filename": video["video_filename"],
            "track_records": video["track_records"],
            "distinct_track_ids": video["distinct_track_ids"],
            "average_observed_seconds": (
                round(float(video["avg_observed_seconds"]), 2)
                if video["avg_observed_seconds"] is not None
                else None
            ),
            "last_observed_second": (
                float(video["last_observed_second"])
                if video["last_observed_second"] is not None
                else None
            ),
            "estimated_wait_minutes": None,
            "estimated_order_ready_minutes": None,
            "estimate_status": "requires_service_time_calibration",
        })

    return JsonResponse({
        "mode": "recorded_video_analysis",
        "videos_analyzed": len(results),
        "results": results,
        "note": (
            "Observed track duration is not customer waiting time. "
            "Waiting and order-ready estimates require measured service "
            "time or a validated service-rate configuration."
        ),
    })


def _serialize_db_value(value):
    from decimal import Decimal
    from datetime import date, datetime

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _fetch_rows_as_dicts(cursor):
    columns = [column[0] for column in cursor.description]
    return [
        {
            key: _serialize_db_value(value)
            for key, value in zip(columns, row)
        }
        for row in cursor.fetchall()
    ]


@api_view(["GET"])
@permission_classes([AllowAny])
def queue_person_tracks(request):
    filename = request.query_params.get("video_filename", "").strip()

    try:
        limit = int(request.query_params.get("limit", "100"))
        offset = int(request.query_params.get("offset", "0"))
    except ValueError:
        return JsonResponse(
            {"error": "limit and offset must be integers"}, status=400
        )

    if not 1 <= limit <= 500 or offset < 0:
        return JsonResponse(
            {"error": "limit must be 1-500 and offset non-negative"},
            status=400,
        )

    with connection.cursor() as cursor:
        if filename:
            cursor.execute(
                """
                SELECT COUNT(*) FROM public.queue_person_tracks
                WHERE video_filename ILIKE %s
                """,
                [f"%{filename}%"],
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM public.queue_person_tracks"
            )

        total = cursor.fetchone()[0]

        base_sql = """
            SELECT id, video_filename, track_id,
                   first_seen_video_second, last_seen_video_second,
                   first_seen_frame, last_seen_frame, max_confidence,
                   snapshot_path, created_at
            FROM public.queue_person_tracks
        """

        if filename:
            cursor.execute(
                base_sql + """
                    WHERE video_filename ILIKE %s
                    ORDER BY video_filename, track_id
                    LIMIT %s OFFSET %s
                """,
                [f"%{filename}%", limit, offset],
            )
        else:
            cursor.execute(
                base_sql + """
                    ORDER BY video_filename, track_id
                    LIMIT %s OFFSET %s
                """,
                [limit, offset],
            )

        results = _fetch_rows_as_dicts(cursor)

    return JsonResponse({
        "count": total,
        "limit": limit,
        "offset": offset,
        "results": results,
        "note": "Track IDs are tracker-generated identities, not verified unique customer identities.",
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def queue_tracking_runs(request):
    filename = request.query_params.get("video_filename", "").strip()

    sql = """
        SELECT id, video_filename, resolution, fps,
               reported_frames, processed_frames,
               unique_queue_track_ids, processing_seconds,
               model_name, tracker_name, device,
               annotated_video_path, snapshots_folder,
               generated_at, created_at
        FROM public.queue_tracking_runs
    """

    with connection.cursor() as cursor:
        if filename:
            cursor.execute(
                "SELECT COUNT(*) FROM public.queue_tracking_runs "
                "WHERE video_filename ILIKE %s",
                [f"%{filename}%"],
            )
            total = cursor.fetchone()[0]
            cursor.execute(
                sql + """
                    WHERE video_filename ILIKE %s
                    ORDER BY created_at DESC, id DESC
                """,
                [f"%{filename}%"],
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM public.queue_tracking_runs"
            )
            total = cursor.fetchone()[0]
            cursor.execute(
                sql + " ORDER BY created_at DESC, id DESC"
            )

        results = _fetch_rows_as_dicts(cursor)

    return JsonResponse({"count": total, "results": results})


@api_view(["GET"])
@permission_classes([AllowAny])
def queue_dashboard(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) AS person_track_records,
                   COUNT(DISTINCT video_filename) AS videos_with_tracks
            FROM public.queue_person_tracks
        """)
        person_stats = _fetch_rows_as_dicts(cursor)[0]

        cursor.execute("""
            SELECT COUNT(*) AS tracking_runs,
                   COALESCE(SUM(processed_frames), 0) AS processed_frames,
                   COALESCE(SUM(unique_queue_track_ids), 0)
                       AS summed_video_track_ids
            FROM public.queue_tracking_runs
        """)
        run_stats = _fetch_rows_as_dicts(cursor)[0]

        cursor.execute("""
            SELECT video_filename, COUNT(*) AS person_track_records
            FROM public.queue_person_tracks
            GROUP BY video_filename
            ORDER BY video_filename
        """)
        per_video = _fetch_rows_as_dicts(cursor)

    return JsonResponse({
        **person_stats,
        **run_stats,
        "per_video": per_video,
        "note": "Summed track IDs across videos are not a deduplicated customer count or verified waiting-time measurement.",
    })
