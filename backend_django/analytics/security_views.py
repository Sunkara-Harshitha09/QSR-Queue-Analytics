from django.contrib.auth import authenticate, get_user_model

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import QueueThreshold
from rest_framework.permissions import AllowAny, IsAuthenticated

User = get_user_model()


def get_active_thresholds():
    thresholds, _ = QueueThreshold.objects.get_or_create(pk=1)
    return thresholds


def threshold_data(thresholds):
    return {
        "queue_people_threshold": thresholds.queue_people_threshold,
        "waiting_minutes_threshold": thresholds.waiting_minutes_threshold,
        "updated_at": thresholds.updated_at,
        "updated_by": (
            thresholds.updated_by.username
            if thresholds.updated_by
            else None
        ),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def login_api(request):
    """
    Authenticate using either a username or a unique email address.
    Returns JWT access and refresh tokens on success.
    """
    login_value = (
        request.data.get("username")
        or request.data.get("email")
        or ""
    ).strip()

    password = request.data.get("password", "")

    if not login_value or not password:
        return Response(
            {"detail": "Enter your username/email and password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = login_value

    # If the supplied value looks like an email, resolve it to a username.
    if "@" in login_value:
        email_matches = User.objects.filter(
            email__iexact=login_value,
            is_active=True,
        )

        if email_matches.count() != 1:
            return Response(
                {"detail": "No unique active account was found for this email."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        username = email_matches.first().get_username()

    user = authenticate(
        request=request,
        username=username,
        password=password,
    )

    if user is None or not user.is_active:
        return Response(
            {"detail": "Invalid username/email or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "username": user.get_username(),
                "email": user.email,
                "is_admin": user.is_staff or user.is_superuser,
                "is_superuser": user.is_superuser,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user_api(request):
    user = request.user

    return Response(
        {
            "username": user.get_username(),
            "email": user.email,
            "is_admin": user.is_staff or user.is_superuser,
            "is_superuser": user.is_superuser,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def thresholds_api(request):
    """
    Authenticated users may view thresholds.
    Only staff/superusers may change them.
    """
    if request.method == "GET":
        thresholds = get_active_thresholds()
        return Response(threshold_data(thresholds))

    # Enforce permissions in the backend, not just in React.
    if not (request.user.is_staff or request.user.is_superuser):
        return Response(
            {"detail": "Only administrators can change thresholds."},
            status=status.HTTP_403_FORBIDDEN,
        )

    people = request.data.get("queue_people_threshold")
    minutes = request.data.get("waiting_minutes_threshold")

    try:
        people = int(people)
        minutes = int(minutes)
    except (TypeError, ValueError):
        return Response(
            {"detail": "Both thresholds must be whole numbers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not 1 <= people <= 100:
        return Response(
            {"detail": "Queue threshold must be between 1 and 100."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not 1 <= minutes <= 240:
        return Response(
            {"detail": "Waiting threshold must be between 1 and 240 minutes."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    thresholds = get_active_thresholds()
    thresholds.queue_people_threshold = people
    thresholds.waiting_minutes_threshold = minutes
    thresholds.updated_by = request.user
    thresholds.save()

    return Response(
        threshold_data(thresholds),
        status=status.HTTP_200_OK,
    )
