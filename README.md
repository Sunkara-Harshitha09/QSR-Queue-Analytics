# QSR Queue Analytics

An AI-powered Quick Service Restaurant (QSR) queue monitoring and customer analytics system using computer vision.

## Project Overview

This project aims to monitor customer queues, analyze recorded videos, track people, and provide queue analytics through a web dashboard.

## Technology Stack

- Frontend: React, Vite, JavaScript
- Backend: Django, Django REST Framework
- Database: PostgreSQL
- Database Deployment: Docker Compose
- Object Detection: YOLO11n
- Object Tracking: ByteTrack
- Video Processing: OpenCV, FFmpeg
- Planned GPU Pipeline: NVIDIA DeepStream

## Implemented Features

- React login and dashboard interfaces
- Django backend APIs
- PostgreSQL database integration
- Recorded-video person detection and tracking on CPU
- Tracking results stored in the database
- Annotated video outputs
- Preliminary queue-region configuration
- Initial queue analytics APIs

## Work in Progress

- Validate customer counting and queue regions
- Improve queue analytics and waiting-time estimation
- Integrate dashboard metrics
- Execute and validate NVIDIA DeepStream on a compatible GPU
- Integrate live RTSP cameras
- Implement threshold-based alerts with screenshot and video evidence
- Test end-to-end performance and deployment

## Important Note

NVIDIA DeepStream GPU execution and live RTSP integration have not yet been verified as completed. Observed tracking duration is not the same as actual customer waiting time.

## Local Development

### Backend

From the project root, activate your Python environment:

    .\.venv\Scripts\Activate.ps1

Then start Django:

    Set-Location .\backend_django
    python manage.py runserver

### Frontend

Open a separate PowerShell terminal:

    Set-Location .\frontend_react
    npm install
    npm run dev

### Database

From the project root:

    docker compose up -d postgres

## Security and Data

- Never commit `.env` files, passwords, tokens, or credentials.
- Keep private videos, model weights, and large generated files out of Git unless explicitly approved.
- Validate analytics before using them for operational decisions.

## License

No license has been selected yet. All rights remain with the copyright holder.
