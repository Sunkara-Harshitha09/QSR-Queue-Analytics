
from django.contrib import admin
from django.urls import path

from analytics import views, security_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Existing API endpoints
    path("api/health/", views.health, name="api-health"),
    path("api/dashboard/", views.dashboard, name="api-dashboard"),
    path(
        "api/processing-runs/",
        views.processing_runs,
        name="api-processing-runs",
    ),
    path(
        "api/measurements/",
        views.measurements,
        name="api-measurements",
    ),
    path(
        "api/queue-person-tracks/",
        views.queue_person_tracks,
        name="api-queue-person-tracks",
    ),
    path(
        "api/queue-tracking-runs/",
        views.queue_tracking_runs,
        name="api-queue-tracking-runs",
    ),
    path(
        "api/queue-dashboard/",
        views.queue_dashboard,
        name="api-queue-dashboard",
    ),

    path(
        "api/queue-estimates/",
         views.queue_estimates,
        name="api-queue-estimates",
    ),
    # Authentication endpoints
    path(
        "api/auth/token/",
        security_views.login_api,
        name="auth-token",
    ),
    path(
        "api/auth/me/",
        security_views.current_user_api,
        name="auth-me",
    ),

    # Admin-controlled threshold configuration
    path(
        "api/thresholds/",
        security_views.thresholds_api,
        name="api-thresholds",
    ),
]
