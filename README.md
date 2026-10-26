
# QSR Queue Analytics

An AI-powered Quick Service Restaurant (QSR) queue monitoring and customer analytics system designed to analyze video streams, track people, monitor queues, and support operational decision-making.

## Project Overview

QSR Queue Analytics aims to help restaurants monitor customer queues, understand customer flow, and identify potential congestion using computer vision and video analytics.

The project is being developed as an end-to-end application with a web dashboard, backend APIs, database storage, and an edge video analytics pipeline.

## Key Features

- **Dashboard:** Customer analytics, queue information, video analysis results, and system status.
- **Authentication:** Login interface and backend authentication APIs.
- **Video Analytics:** Person detection and multi-object tracking on recorded videos.
- **Queue Monitoring:** Configurable queue regions and preliminary queue-related analytics.
- **Evidence Management:** Planned storage of alert screenshots and video evidence.
- **Historical Analytics:** Database-backed tracking records and processing information.
- **Real-Time Monitoring:** Planned integration with live cameras and real-time updates.
- **Alerts:** Planned threshold-based queue alerts with timestamps and supporting evidence.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, JavaScript |
| Backend | Django, Django REST Framework |
| Database | PostgreSQL |
| Database Deployment | Docker Compose |
| Object Detection | YOLO |
| Object Tracking | ByteTrack |
| Video Processing | OpenCV, FFmpeg |
| Planned GPU Pipeline | NVIDIA DeepStream, CUDA |
| Version Control | Git, GitHub |

## Current Implementation Status

### Implemented

- React-based login and dashboard interfaces.
- Django backend and API endpoints.
- PostgreSQL database setup using Docker Compose.
- Recorded-video person detection and tracking using YOLO11n and ByteTrack on CPU.
- Tracking results imported into PostgreSQL.
- Annotated video outputs and H.264 video conversion.
- Preliminary queue-region configuration for recorded videos.
- Initial queue analytics API integration.

### In Progress

- Validating queue regions and customer-counting accuracy.
- Integrating recorded-video analytics into dashboard metrics.
- Improving queue analytics and estimating waiting times using validated service-time data.
- Refining dashboard metrics and historical analytics.

### Planned

- NVIDIA DeepStream inference and tracking on a compatible GPU system.
- Live RTSP camera integration and edge deployment.
- Real-time customer counting and queue monitoring.
- Configurable threshold-based alerts with timestamped image/video evidence.
- End-to-end integration between edge analytics, backend APIs, PostgreSQL, and the frontend.
- Performance benchmarking for accuracy, FPS, processing latency, and GPU utilization.
- Production deployment and security validation.

**Note:** DeepStream GPU execution and live RTSP integration have not yet been verified as completed. Waiting-time estimates require calibration and validation; observed tracking duration must not be treated as actual queue waiting time.

## Project Structure

The repository is organized around the following major components. Exact subdirectories may evolve during development.

- `backend_django/` — Django backend and API implementation.
- `frontend_react/` — React frontend application.
- `edge/` — Video analytics and tracking-related scripts and configuration.
- `data/` — Local input videos and generated evidence; large or sensitive files should remain untracked.
- `docker-compose.yml` — Local service configuration, if present.
- `.env` — Local environment variables; must not be committed.
- `.gitignore` — Files and directories excluded from Git.

## Prerequisites

Install the tools required for your development environment:

- Python and pip
- Node.js and npm
- Git
- Docker Desktop
- PostgreSQL-compatible database setup

A compatible NVIDIA GPU, NVIDIA drivers, CUDA, and NVIDIA DeepStream SDK will be required to execute the planned GPU-accelerated pipeline.

## Local Development

### 1. Backend

From the repository root, activate your existing Python environment and start Django:

```powershell
.\.venv\Scripts\Activate.ps1
Set-Location .\backend_django
python manage.py runserver
```

The backend development server normally runs at `http://127.0.0.1:8000`.

### 2. Frontend

Open a separate PowerShell terminal:

```powershell
Set-Location .\frontend_react
npm install
npm run dev
```

Use the local URL printed by Vite to open the frontend.

### 3. Database

Start the configured PostgreSQL service from the repository root, if `docker-compose.yml` is configured for it:

```powershell
docker compose up -d postgres
docker compose ps
```

Configure database credentials through local environment variables. Never commit real credentials.

## API Endpoints

The current backend includes endpoints for health checks, dashboards, processing runs, measurements, queue tracking, queue estimates, authentication, and thresholds.

Examples of currently implemented routes include:

- `/api/health/`
- `/api/dashboard/`
- `/api/processing-runs/`
- `/api/measurements/`
- `/api/queue-person-tracks/`
- `/api/queue-tracking-runs/`
- `/api/queue-dashboard/`
- `/api/queue-estimates/`
- `/api/auth/token/`
- `/api/auth/me/`
- `/api/thresholds/`

Check the backend source code for the exact methods, request formats, and authentication requirements for each endpoint.

## Data and Privacy

- Do not commit `.env` files, passwords, API keys, tokens, or database credentials.
- Do not commit virtual environments, caches, build outputs, or local database volumes.
- Keep large source videos, generated videos, model weights, and private customer footage out of Git unless explicitly approved.
- Use authorized video datasets and follow applicable privacy requirements.
- Do not treat tracker IDs as unique real-world customer identities.
- Validate all queue counts and waiting-time estimates before using them operationally.

## Development Roadmap

1. Stabilize the current backend, database, and frontend integration.
2. Validate detection, tracking, and queue-region accuracy.
3. Implement calibrated queue and waiting-time analytics.
4. Integrate and test NVIDIA DeepStream on a compatible GPU.
5. Connect live camera streams and edge devices.
6. Implement evidence-backed threshold alerts.
7. Benchmark performance and validate end-to-end behavior.
8. Harden authentication, configuration, and deployment.

