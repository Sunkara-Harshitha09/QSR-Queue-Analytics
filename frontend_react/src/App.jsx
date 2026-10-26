import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000/api";

const VIDEO_LIST = [
  {
    id: "counter",
    name: "Restaurant Counter",
    file: "counter.mp4",
    path: "/videos/counter.mp4",
    resolution: "2560 × 1440",
    duration: "10.28 sec",
    description: "Wide-angle counter footage",
    region: "Service activity region",
  },
  {
    id: "normal",
    name: "Vertical Counter",
    file: "normal_queue.mp4",
    path: "/videos/normal_queue.mp4",
    resolution: "240 × 426",
    duration: "22.50 sec",
    description: "Vertical service-counter footage",
    region: "Provisional activity region",
  },
];

const NAVIGATION = [
  {
    section: "WORKSPACE",
    items: [
      { id: "dashboard", label: "Dashboard", icon: "◫" },
      { id: "monitoring", label: "Video monitoring", icon: "▣" },
      { id: "analytics", label: "Activity analytics", icon: "⌁" },
      { id: "queue", label: "Queue analytics", icon: "P" },
      { id: "history", label: "Processing history", icon: "◷" },
    ],
  },
  {
    section: "MANAGEMENT",
    items: [
      { id: "cameras", label: "Camera management", icon: "◎" },
      { id: "alerts", label: "Alerts & events", icon: "♧" },
      { id: "reports", label: "Reports & exports", icon: "▤" },
    ],
  },
  {
    section: "SYSTEM",
    items: [{ id: "settings", label: "Settings", icon: "⚙" }],
  },
];

const EMPTY_METRICS = {
  processingRuns: 0,
  completedRuns: 0,
  failedRuns: 0,
  totalMeasurements: 0,
  averageForegroundPercent: null,
  videosMeasured: 0,
  runs: [],
  measurements: [],
};

function Icon({ children }) {
  return <span className="nav-icon" aria-hidden="true">{children}</span>;
}

function StatCard({ label, value, detail, icon, tone = "teal" }) {
  return (
    <article className="stat-card">
      <div className="stat-top">
        <span className="muted stat-label">{label}</span>
        <span className={`stat-icon ${tone}`}><Icon>{icon}</Icon></span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-detail">{detail}</div>
    </article>
  );
}

function Badge({ children, tone = "neutral" }) {
  return (
    <span className={`badge ${tone}`}>
      <span className="badge-dot" />
      {children}
    </span>
  );
}

function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="page-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      {action && <div className="page-action">{action}</div>}
    </div>
  );
}

function EmptyState({ icon, title, text }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function Readiness({ label, status, tone }) {
  return (
    <div className="readiness-row">
      <span className={`readiness-indicator ${tone}`} />
      <span className="readiness-label">{label}</span>
      <span className={`readiness-status ${tone}`}>{status}</span>
    </div>
  );
}

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  function submit(event) {
    event.preventDefault();
    setError("");

    if (!email.trim() || !password) {
      setError("Enter an email address and password to continue.");
      return;
    }

    onLogin(email.trim(), password).catch((err) => {
      setError(err instanceof Error ? err.message : "Sign in failed. Check your credentials.");
    });
  }

  return (
    <main className="login-shell">
      <div className="login-decoration decoration-one" />
      <div className="login-decoration decoration-two" />
      <section className="login-card">
        <div className="brand-mark large">Q<span>•</span></div>
        <div className="eyebrow">QUEUE INTELLIGENCE PLATFORM</div>
        <h1>Welcome back.</h1>
        <p className="muted login-description">
          Sign in to access your QSR video analytics workspace.
        </p>

        <form onSubmit={submit} className="login-form">
          <label htmlFor="login-email">Email address</label>
          <input
            id="login-email"
            type="email"
            placeholder="Enter your registered email address"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />

          <div className="password-label">
            <label htmlFor="login-password">Password</label>
            <button
              className="text-button"
              type="button"
              onClick={() => setShowPassword((value) => !value)}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
          <input
            id="login-password"
            type={showPassword ? "text" : "password"}
            placeholder="Enter your password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />

          {error && <div className="form-error">{error}</div>}

          <button type="submit" className="primary-button login-submit">
            Enter workspace <span>→</span>
          </button>
        </form>

        <div className="login-notice">
          <span>ⓘ</span>
          <p>
            Secure sign-in is verified by the Django API. Your account permissions determine which controls are available.
          </p>
        </div>
        <div className="login-footer">
          QSR QUEUE ANALYTICS · INTERNAL WORKSPACE
        </div>
      </section>
    </main>
  );
}


function ThresholdPanel({ isAdmin, token, thresholds, onThresholdsSaved }) {
  const [people, setPeople] = useState(String(thresholds?.queue_people_threshold ?? 5));
  const [minutes, setMinutes] = useState(String(thresholds?.waiting_minutes_threshold ?? 5));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setPeople(String(thresholds?.queue_people_threshold ?? 5));
    setMinutes(String(thresholds?.waiting_minutes_threshold ?? 5));
  }, [thresholds]);

  async function saveThresholds(event) {
    event.preventDefault();
    setMessage("");

    if (!isAdmin) {
      setMessage("Administrator permission is required to change thresholds.");
      return;
    }

    const peopleValue = Number(people);
    const minutesValue = Number(minutes);
    if (!Number.isInteger(peopleValue) || peopleValue < 1 || peopleValue > 100) {
      setMessage("Queue threshold must be a whole number between 1 and 100.");
      return;
    }
    if (!Number.isInteger(minutesValue) || minutesValue < 1 || minutesValue > 240) {
      setMessage("Waiting-time threshold must be a whole number between 1 and 240.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/thresholds/`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          queue_people_threshold: peopleValue,
          waiting_minutes_threshold: minutesValue,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (response.status === 401) {
        throw new Error("Your session expired. Please sign in again.");
      }
      if (!response.ok) {
        throw new Error(data.detail || data.error || `Could not save thresholds (HTTP ${response.status}).`);
      }
      onThresholdsSaved(data);
      setMessage("Thresholds saved successfully.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Saving thresholds failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel bottom-panel">
      <div className="panel-heading">
        <div>
          <h2>Queue alert thresholds</h2>
          <p className="muted">Configure the queue size and waiting-time limits used by alert rules.</p>
        </div>
        <Badge tone={isAdmin ? "purple" : "neutral"}>{isAdmin ? "Admin control" : "Read only"}</Badge>
      </div>

      {!isAdmin && (
        <div className="notice-banner">
          <span className="notice-symbol">i</span>
          <div>
            <strong>Administrator permission required</strong>
            <p>You can view the active thresholds. Only an administrator can edit and save them.</p>
          </div>
        </div>
      )}

      <form className="threshold-form" onSubmit={saveThresholds}>
        <label>
          Queue size warning (people)
          <input
            type="number"
            min="1"
            max="100"
            step="1"
            value={people}
            disabled={!isAdmin || saving}
            onChange={(event) => setPeople(event.target.value)}
          />
        </label>
        <label>
          Waiting-time warning (minutes)
          <input
            type="number"
            min="1"
            max="240"
            step="1"
            value={minutes}
            disabled={!isAdmin || saving}
            onChange={(event) => setMinutes(event.target.value)}
          />
        </label>
        {isAdmin && (
          <button className="primary-button" disabled={saving} type="submit">
            {saving ? "Saving…" : "Save threshold settings"}
          </button>
        )}
        {message && <p className="muted" role="status">{message}</p>}
      </form>
      <p className="muted small-note">
        Active values: {thresholds?.queue_people_threshold ?? "—"} people and {thresholds?.waiting_minutes_threshold ?? "—"} minutes.
        The Django API must also enforce admin-only updates.
      </p>
    </section>
  );
}


function CustomerDashboard({ email, queueData, queueEstimates, apiStatus, apiError, refreshData, lastUpdated }) {
  const liveQueueCount = queueData?.current_queue_length ?? queueData?.queue_length ?? queueData?.waiting_customers;
  const orderWait = queueData?.estimated_order_wait_minutes ?? queueData?.estimated_wait_minutes;
  const readyWait = queueData?.estimated_order_ready_minutes;
  const activeCounters = queueData?.active_counters ?? queueData?.available_counters;
  const hasLiveQueue = liveQueueCount !== undefined && liveQueueCount !== null;
  const recordedTrackCount = (queueEstimates ?? []).reduce(
  (total, item) => total + (Number(item.track_records) || 0),
  0
);

const averageObservedSeconds = recordedTrackCount > 0
  ? (
      queueEstimates.reduce(
        (total, item) =>
          total +
          (Number(item.track_records) || 0) *
          (Number(item.average_observed_seconds) || 0),
        0
      ) / recordedTrackCount
    ).toFixed(2)
  : null;

  return (
    <>
      <PageHeader
        eyebrow="CUSTOMER VIEW"
        title="Your queue at a glance"
        description="A simple view of restaurant crowding and estimated waiting time."
        action={<button className="secondary-button" onClick={refreshData}>Refresh status ↻</button>}
      />
      {apiError && <div className="notice-banner" role="alert"><span className="notice-symbol">!</span><div><strong>Could not refresh queue status</strong><p>{apiError}</p></div></div>}
      <section className="panel customer-welcome-panel">
        <div className="panel-heading">
          <div><h2>Welcome{email ? `, ${email.split('@')[0]}` : ''}</h2><p className="muted">Check the queue before deciding when to visit.</p></div>
          <Badge tone={apiStatus === "Connected" ? "green" : "amber"}>{apiStatus}</Badge>
        </div>
        <div className="notice-banner">
          <span className="notice-symbol">i</span>
          <div><strong>{hasLiveQueue ? "Queue information" : "Live waiting-time estimates are not configured yet"}</strong><p>{hasLiveQueue ? "Estimates are based on the latest queue summary available to the system." : "Your customer dashboard is ready, but the current backend does not yet provide a verified live queue count, active staff count, or waiting-time estimate. These will appear after queue and service-time calculations are connected."}</p></div>
        </div>
      </section>
      <div className="stat-grid customer-stat-grid">
  <StatCard
    label="Recorded track IDs"
    value={String(recordedTrackCount)}
    detail="Across analyzed video clips"
    icon="P"
    tone="teal"
  />
  <StatCard
    label="Videos analyzed"
    value={String(queueEstimates?.length ?? 0)}
    detail="Recorded video analysis"
    icon="◷"
    tone="blue"
  />
  <StatCard
    label="Average visible time"
    value={averageObservedSeconds != null ? `${averageObservedSeconds} sec` : "—"}
    detail="Observed track duration, not queue wait"
    icon="✓"
    tone="purple"
  />
  <StatCard
    label="Waiting time"
    value="Not calibrated"
    detail="Requires validated service-time data"
    icon="▣"
    tone="amber"
  />
</div>
      <section className="panel bottom-panel">
        <div className="panel-heading">
          <div>
            <h2>Recorded video analysis</h2>
            <p className="muted">Tracking summaries from the two processed videos — not live queue data.</p>
          </div>
          <Badge tone={queueEstimates?.length ? "blue" : "amber"}>{queueEstimates?.length ? `${queueEstimates.length} video summaries` : "No summaries"}</Badge>
        </div>
        {queueEstimates?.length ? (
          <>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Recorded video</th><th>Distinct track IDs</th><th>Average visible time</th><th>Wait estimate</th></tr></thead>
                <tbody>
                  {queueEstimates.map((item) => (
                    <tr key={item.video_filename}>
                      <td>{item.video_filename}</td>
                      <td>{item.distinct_track_ids ?? "—"}</td>
                      <td>{item.average_observed_seconds != null ? `${item.average_observed_seconds} sec` : "—"}</td>
                      <td>{item.estimated_wait_minutes != null ? `${item.estimated_wait_minutes} min` : "Not calibrated"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted small-note">Track IDs count detections tracked within each recorded clip; they are not a live count of customers currently waiting. Visible time is not the same as queue waiting time.</p>
          </>
        ) : (
          <EmptyState icon="◷" title="No video analysis summary loaded" text="Check that the Django /api/queue-estimates/ endpoint is registered and the two video tracking results exist in PostgreSQL." />
        )}
      </section>
      <section className="panel">
        <div className="panel-heading"><div><h2>What this means</h2><p className="muted">Customer-friendly queue guidance</p></div></div>
        <div className="readiness-list">
          <Readiness label="Queue status" status={hasLiveQueue ? "Summary available" : "Waiting for live queue integration"} tone={hasLiveQueue ? "green" : "amber"} />
          <Readiness label="Camera access" status="Private to authorized administrators" tone="green" />
          <Readiness label="Last update" status={lastUpdated ? lastUpdated.toLocaleTimeString() : "Not yet updated"} tone={lastUpdated ? "green" : "amber"} />
        </div>
        <p className="muted small-note">Waiting-time values will only be shown when the backend provides a calculated estimate. The system will not invent a wait time.</p>
      </section>
    </>
  );
}

function Dashboard({ navigate, metrics, apiStatus, apiError, refreshData, isAdmin, token, thresholds, onThresholdsSaved }) {
  const recentRuns = metrics.runs.slice(0, 5);

  return (
    <>
      <PageHeader
        eyebrow="OVERVIEW / WORKSPACE"
        title="Operations overview"
        description="Monitor your video processing pipeline and recorded footage."
        action={
          <button className="secondary-button" onClick={refreshData}>
            Refresh data ↻
          </button>
        }
      />

      {apiError && (
        <div className="notice-banner" role="alert">
          <span className="notice-symbol">!</span>
          <div>
            <strong>Unable to load all API data</strong>
            <p>{apiError}</p>
            <p>Check that Django is running at {API_BASE}.</p>
          </div>
        </div>
      )}

      <div className="notice-banner">
        <span className="notice-symbol">i</span>
        <div>
          <strong>Measurement status</strong>
          <p>
            Metrics come from OpenCV foreground activity measurements.
            They are not verified customer counts, queue lengths or waiting times.
          </p>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Input videos"
          value={String(VIDEO_LIST.length).padStart(2, "0")}
          detail="Local MP4 files"
          icon="▣"
        />
        <StatCard
          label="Processing runs"
          value={String(metrics.processingRuns)}
          detail="Records in PostgreSQL"
          icon="◷"
          tone="blue"
        />
        <StatCard
          label="Measurements"
          value={String(metrics.totalMeasurements)}
          detail="Saved activity samples"
          icon="⌁"
          tone="purple"
        />
        <StatCard
          label="Failed runs"
          value={String(metrics.failedRuns)}
          detail={`${metrics.completedRuns} completed`}
          icon="!"
          tone="amber"
        />
      </div>

      <div className="content-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Your video sources</h2>
              <p className="muted">Actual input videos in this project</p>
            </div>
            <button className="text-button" onClick={() => navigate("monitoring")}>
              View all →
            </button>
          </div>
          <div className="source-list">
            {VIDEO_LIST.map((video) => (
              <button
                className="source-row"
                key={video.id}
                onClick={() => navigate("monitoring", video.id)}
              >
                <div className="source-thumb"><span>▶</span></div>
                <div className="source-info">
                  <strong>{video.name}</strong>
                  <span>{video.file}</span>
                  <small>{video.resolution} · {video.duration}</small>
                </div>
                <Badge tone="blue">Recorded</Badge>
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>System readiness</h2>
              <p className="muted">Current integration status</p>
            </div>
            <Badge tone={apiStatus === "Connected" ? "green" : "amber"}>
              {apiStatus}
            </Badge>
          </div>
          <div className="readiness-list">
            <Readiness label="React frontend" status="Available" tone="green" />
            <Readiness label="Local video files" status="Configured" tone="green" />
            <Readiness label="PostgreSQL" status={apiStatus === "Connected" ? "Connected" : "Unverified"} tone={apiStatus === "Connected" ? "green" : "amber"} />
            <Readiness label="Django REST API" status={apiStatus} tone={apiStatus === "Connected" ? "green" : "amber"} />
            <Readiness label="Live camera stream" status="Not configured" tone="amber" />
            <Readiness label="Secure login" status="Not implemented" tone="amber" />
          </div>
        </section>
      </div>

      <ThresholdPanel
        isAdmin={isAdmin}
        token={token}
        thresholds={thresholds}
        onThresholdsSaved={onThresholdsSaved}
      />

      <section className="panel bottom-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent processing runs</h2>
            <p className="muted">Loaded from the processing_runs table</p>
          </div>
          <button className="text-button" onClick={() => navigate("history")}>
            Full history →
          </button>
        </div>

        {recentRuns.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Video</th>
                  <th>Status</th>
                  <th>Method</th>
                  <th>Started</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={run.id}>
                    <td>#{run.id}</td>
                    <td>{run.video_filename}</td>
                    <td>
                      <Badge tone={run.status === "completed" ? "green" : "amber"}>
                        {run.status}
                      </Badge>
                    </td>
                    <td>{run.measurement_method}</td>
                    <td>{formatDate(run.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon="◷"
            title={apiStatus === "Loading" ? "Loading processing history" : "No processing runs found"}
            text="Processing history will appear here when API data is available."
          />
        )}
      </section>
    </>
  );
}

function Monitoring({ selectedVideo, setSelectedVideo }) {
  const [playing, setPlaying] = useState({});
  const [showRegion, setShowRegion] = useState(true);

  return (
    <>
      <PageHeader
        eyebrow="VIDEO OPERATIONS"
        title="Video monitoring"
        description="Review the actual footage used by the analytics pipeline."
        action={<Badge tone="blue">Recorded footage</Badge>}
      />

      <div className="notice-banner">
        <span className="notice-symbol">i</span>
        <div>
          <strong>Recorded video, not live streaming</strong>
          <p>
            These are uploaded MP4 files. Live monitoring requires a real camera
            source and a streaming service.
          </p>
        </div>
      </div>

      <div className="video-toolbar">
        <div className="filter-tabs">
          {VIDEO_LIST.map((video) => (
            <button
              key={video.id}
              className={selectedVideo === video.id ? "filter-tab active" : "filter-tab"}
              onClick={() => setSelectedVideo(video.id)}
            >
              {video.name}
            </button>
          ))}
        </div>
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={showRegion}
            onChange={(event) => setShowRegion(event.target.checked)}
          />
          Show region label
        </label>
      </div>

      <div className="video-grid">
        {VIDEO_LIST.map((video) => (
          <section
            className={`panel video-panel ${selectedVideo === video.id ? "selected-panel" : ""}`}
            key={video.id}
          >
            <div className="panel-heading">
              <div>
                <h2>{video.name}</h2>
                <p className="muted">{video.description}</p>
              </div>
              <Badge tone="blue">MP4</Badge>
            </div>

            <div className="video-frame">
              <video
                src={video.path}
                controls
                preload="metadata"
                playsInline
                onPlay={() => setPlaying((current) => ({ ...current, [video.id]: true }))}
                onPause={() => setPlaying((current) => ({ ...current, [video.id]: false }))}
              >
                Your browser does not support HTML video.
              </video>
              {showRegion && (
                <div className="video-region-note">
                  <span className="region-dot" />
                  {video.region} · provisional label only
                </div>
              )}
            </div>

            <div className="video-meta">
              <div><span>File</span><strong>{video.file}</strong></div>
              <div><span>Resolution</span><strong>{video.resolution}</strong></div>
              <div><span>Duration</span><strong>{video.duration}</strong></div>
              <div><span>Playback</span><strong>{playing[video.id] ? "Playing" : "Ready / paused"}</strong></div>
            </div>

            <button
              className="secondary-button full-button"
              onClick={() => setSelectedVideo(video.id)}
            >
              {selectedVideo === video.id ? "Selected video" : "Select video"}
            </button>
          </section>
        ))}
      </div>
    </>
  );
}

function Analytics({ metrics }) {
  const points = metrics.measurements;
  const max = Math.max(1, ...points.map((point) => Number(point.value) || 0));

  return (
    <>
      <PageHeader
        eyebrow="MEASUREMENT INTELLIGENCE"
        title="Activity analytics"
        description="Explore measured foreground activity and its limitations."
      />
      <div className="notice-banner">
        <span className="notice-symbol">i</span>
        <div>
          <strong>Activity is not a people count</strong>
          <p>
            Foreground pixels and blobs can include staff movement, shadows
            and other visual changes.
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Foreground activity over time</h2>
            <p className="muted">Percent of region pixels classified as foreground</p>
          </div>
          <Badge tone={points.length ? "green" : "amber"}>
            {points.length ? `${points.length} records` : "No data"}
          </Badge>
        </div>

        {points.length ? (
          <div className="bar-chart">
            {points.map((point) => (
              <div className="bar-column" key={`${point.runId}-${point.second}`}>
                <span className="bar-value">{Number(point.value).toFixed(1)}%</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      height: `${Math.max(3, (Number(point.value) / max) * 100)}%`,
                    }}
                  />
                </div>
                <span className="bar-label">R{point.runId} · {point.second}s</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon="⌁"
            title="No measurements loaded"
            text="Check the Django API connection and saved activity_measurements records."
          />
        )}
        <p className="muted">
          Each bar represents one saved measurement. Values are foreground-activity
          proxies, not customer counts or waiting-time estimates.
        </p>
      </section>
    </>
  );
}

function History({ metrics }) {
  return (
    <>
      <PageHeader
        eyebrow="AUDIT TRAIL"
        title="Processing history"
        description="Review actual video-processing runs and their status."
      />
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Processing runs</h2>
            <p className="muted">Source: processing_runs table</p>
          </div>
          <Badge tone="blue">{metrics.runs.length} runs</Badge>
        </div>
        {metrics.runs.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Video</th>
                  <th>Status</th>
                  <th>Method</th>
                  <th>Region</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {metrics.runs.map((run) => (
                  <tr key={run.id}>
                    <td>#{run.id}</td>
                    <td>{run.video_filename}</td>
                    <td>
                      <Badge tone={run.status === "completed" ? "green" : "amber"}>
                        {run.status}
                      </Badge>
                    </td>
                    <td>{run.measurement_method}</td>
                    <td>{run.region_type}</td>
                    <td>{formatDate(run.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon="◷"
            title="No run history loaded"
            text="Run records will appear here when the API returns data."
          />
        )}
      </section>
    </>
  );
}

function Cameras() {
  return (
    <>
      <PageHeader
        eyebrow="SOURCE MANAGEMENT"
        title="Camera management"
        description="Manage recorded video sources and prepare for future live-camera integration."
      />
      <div className="stat-grid two">
        <StatCard label="Recorded sources" value="02" detail="Local MP4 files" icon="▣" />
        <StatCard label="Live cameras" value="00" detail="No RTSP or WebRTC source configured" icon="◎" tone="purple" />
      </div>
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source name</th>
                <th>File</th>
                <th>Resolution</th>
                <th>Source type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {VIDEO_LIST.map((video) => (
                <tr key={video.id}>
                  <td><strong>{video.name}</strong></td>
                  <td>{video.file}</td>
                  <td>{video.resolution}</td>
                  <td>Recorded MP4</td>
                  <td><Badge tone="green">Available</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function Alerts() {
  return (
    <>
      <PageHeader
        eyebrow="EVENT CENTER"
        title="Alerts & events"
        description="Camera, processing and analytics events."
      />
      <section className="panel">
        <EmptyState
          icon="♧"
          title="No alert feed connected"
          text="No alerts are fabricated. Backend alert rules and event storage have not been implemented yet."
        />
      </section>
    </>
  );
}

function Reports({ metrics }) {
  const report = useMemo(() => ({
    application: "QSR Queue Analytics",
    exportedAt: new Date().toISOString(),
    dataSource: "Django REST API / PostgreSQL",
    summary: {
      processingRuns: metrics.processingRuns,
      completedRuns: metrics.completedRuns,
      failedRuns: metrics.failedRuns,
      totalMeasurements: metrics.totalMeasurements,
      averageForegroundPercent: metrics.averageForegroundPercent,
    },
    runs: metrics.runs,
    measurements: metrics.measurements.map((point) => ({
      processing_run_id: point.runId,
      video_second: point.second,
      mean_foreground_percent: point.value,
    })),
    warning: "Foreground activity is not a verified customer count or waiting time.",
  }), [metrics]);

  function downloadJson() {
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "qsr-analytics-report.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <PageHeader
        eyebrow="REPORTING"
        title="Reports & exports"
        description="Export the records currently loaded from Django."
        action={
          <button className="primary-button" onClick={downloadJson}>
            Export JSON ↓
          </button>
        }
      />
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Export contents</h2>
            <p className="muted">Only records currently loaded from the API are included.</p>
          </div>
        </div>
        <Readiness label="Processing runs included" status={String(metrics.runs.length)} tone="blue" />
        <Readiness label="Measurement rows included" status={String(metrics.measurements.length)} tone="blue" />
        <Readiness label="Demo measurements inserted" status="No" tone="green" />
      </section>
    </>
  );
}

function Settings({ apiStatus, isAdmin, token, thresholds, onThresholdsSaved }) {
  return (
    <>
      <PageHeader
        eyebrow="SYSTEM CONTROL"
        title="Settings & thresholds"
        description="Review application status and manage queue-alert thresholds."
      />
      <section className="panel settings-list">
        <Readiness label="Frontend framework" status="React + Vite" tone="green" />
        <Readiness label="Analytics engine" status="YOLO tracking / OpenCV" tone="green" />
        <Readiness label="Database" status="PostgreSQL" tone="blue" />
        <Readiness label="Backend API" status={apiStatus} tone={apiStatus === "Connected" ? "green" : "amber"} />
        <Readiness label="Access role" status={isAdmin ? "Administrator" : "Standard user"} tone={isAdmin ? "purple" : "blue"} />
      </section>
      <ThresholdPanel
        isAdmin={isAdmin}
        token={token}
        thresholds={thresholds}
        onThresholdsSaved={onThresholdsSaved}
      />
    </>
  );
}

function QueueAnalytics({ queueData, trackingRuns, personTracks, refreshData }) {
  const [videoFilter, setVideoFilter] = useState("all");

  const filteredPeople = personTracks.filter((person) =>
    videoFilter === "all" || person.video_filename === videoFilter
  );

  return (
    <>
      <PageHeader
        eyebrow="QUEUE INTELLIGENCE"
        title="Queue analytics"
        description="YOLO person tracking results stored in PostgreSQL."
        action={
          <button className="secondary-button" onClick={refreshData}>
            Refresh data
          </button>
        }
      />

      <div className="notice-banner">
        <span className="notice-symbol">i</span>
        <div>
          <strong>Tracking results are preliminary</strong>
          <p>
            Track IDs can change when people are occluded or re-enter the
            scene. These records are not verified unique customer counts
            or measured waiting times.
          </p>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Person-track records"
          value={String(queueData?.person_track_records ?? 0)}
          detail="Stored tracking records"
          icon="P"
          tone="teal"
        />
        <StatCard
          label="Videos with tracks"
          value={String(queueData?.videos_with_tracks ?? 0)}
          detail="Videos represented in database"
          icon="V"
          tone="blue"
        />
        <StatCard
          label="Tracking runs"
          value={String(queueData?.tracking_runs ?? 0)}
          detail="Saved video summaries"
          icon="R"
          tone="purple"
        />
        <StatCard
          label="Frames processed"
          value={String(queueData?.processed_frames ?? 0)}
          detail="Summed across tracking runs"
          icon="F"
          tone="amber"
        />
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Results by video</h2>
            <p className="muted">Track records and processing performance</p>
          </div>
        </div>

        {trackingRuns.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Video</th>
                  <th>Track IDs</th>
                  <th>Frames</th>
                  <th>Processing time</th>
                  <th>Model</th>
                  <th>Tracker</th>
                  <th>Device</th>
                </tr>
              </thead>
              <tbody>
                {trackingRuns.map((run) => (
                  <tr key={run.id}>
                    <td>{run.video_filename}</td>
                    <td>{run.unique_queue_track_ids}</td>
                    <td>{run.processed_frames}/{run.reported_frames}</td>
                    <td>{run.processing_seconds}s</td>
                    <td>{run.model_name}</td>
                    <td>{run.tracker_name}</td>
                    <td>{run.device}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon="R"
            title="No tracking summaries"
            text="Refresh the data after the tracking API becomes available."
          />
        )}
      </section>

      <section className="panel bottom-panel">
        <div className="panel-heading">
          <div>
            <h2>Person tracking history</h2>
            <p className="muted">
              First and last observed times are relative to each source video.
            </p>
          </div>
          <Badge tone="blue">{filteredPeople.length} records</Badge>
        </div>

        <label className="filter-label">
          Filter video
          <select
            value={videoFilter}
            onChange={(event) => setVideoFilter(event.target.value)}
          >
            <option value="all">All videos</option>
            <option value="counter.mp4">counter.mp4</option>
            <option value="normal_queue.mp4">normal_queue.mp4</option>
          </select>
        </label>

        {filteredPeople.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Video</th>
                  <th>Track ID</th>
                  <th>First seen (s)</th>
                  <th>Last seen (s)</th>
                  <th>Confidence</th>
                  <th>Snapshot path</th>
                </tr>
              </thead>
              <tbody>
                {filteredPeople.map((person) => (
                  <tr key={person.id}>
                    <td>{person.video_filename}</td>
                    <td>#{person.track_id}</td>
                    <td>{Number(person.first_seen_video_second ?? 0).toFixed(2)}</td>
                    <td>{Number(person.last_seen_video_second ?? 0).toFixed(2)}</td>
                    <td>
                      {person.max_confidence == null
                        ? "—"
                        : `${(Number(person.max_confidence) * 100).toFixed(1)}%`}
                    </td>
                    <td className="path-cell">
                      {person.snapshot_path || "No snapshot path"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon="P"
            title="No person records"
            text="Try another video filter or refresh the data."
          />
        )}
      </section>
    </>
  );
}


const PAGE_COMPONENTS = {
  dashboard: Dashboard,
  monitoring: Monitoring,
  analytics: Analytics,
  queue: QueueAnalytics,
  history: History,
  cameras: Cameras,
  alerts: Alerts,
  reports: Reports,
  settings: Settings,
};

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function mapRun(run) {
  return {
    ...run,
    video: run.video_filename,
    method: run.measurement_method,
    timestamp: formatDate(run.started_at),
  };
}

function Application({ email, token, isAdmin, onLogout }) {
  const [activePage, setActivePage] = useState("dashboard");
  const [selectedVideo, setSelectedVideo] = useState("counter");
  const [search, setSearch] = useState("");
  const [profileOpen, setProfileOpen] = useState(false);

  const [metrics, setMetrics] = useState(EMPTY_METRICS);
  const [queueData, setQueueData] = useState(null);
  const [queueEstimates, setQueueEstimates] = useState([]);
  const [trackingRuns, setTrackingRuns] = useState([]);
  const [personTracks, setPersonTracks] = useState([]);
  const [thresholds, setThresholds] = useState({ queue_people_threshold: 5, waiting_minutes_threshold: 5 });
  const [apiStatus, setApiStatus] = useState("Loading");
  const [apiError, setApiError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const refreshData = useCallback(async () => {
    setRefreshing(true);
    setApiStatus("Loading");
    setApiError("");

    try {
      // Customers only receive the safe summary endpoint; admin gets operational APIs.
      const urls = isAdmin
        ? [
            `${API_BASE}/health/`, `${API_BASE}/dashboard/`,
            `${API_BASE}/processing-runs/?limit=500`, `${API_BASE}/measurements/?limit=2000`,
            `${API_BASE}/queue-dashboard/`, `${API_BASE}/queue-tracking-runs/?limit=500`,
            `${API_BASE}/queue-person-tracks/?limit=500`, `${API_BASE}/thresholds/`,
            `${API_BASE}/queue-estimates/`,
          ]
        : [`${API_BASE}/health/`, `${API_BASE}/queue-estimates/`];

      const responses = await Promise.all(urls.map(async (url) => {
        const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401) throw new Error("Your session expired or is not authorized. Please sign in again.");
        if (response.status === 403) throw new Error("This account does not have permission to access a requested API.");
        if (!response.ok) throw new Error(`API request failed (${response.status}): ${url}`);
        return response.json();
      }));

      const health = responses[0];
      if (health.status !== "healthy") throw new Error("Django reports that the database is not healthy.");

      if (isAdmin) {
        const [_, dashboard, runData, measurementData, queueSummary, trackingRunData, personTrackData, thresholdData, estimateData] = responses;
        const runs = (runData.results || []).map(mapRun);
        const measurements = (measurementData.results || []).map((item) => ({
          id: item.id, runId: item.processing_run_id, video: item.video_filename,
          second: item.video_second, value: Number(item.mean_foreground_percent),
          pixels: Number(item.mean_foreground_pixels), blobs: Number(item.mean_large_foreground_blobs),
          measurementType: item.measurement_type,
        }));
        setQueueData(queueSummary);
        setQueueEstimates(estimateData.results || []);
        setTrackingRuns(trackingRunData.results || []);
        setPersonTracks(personTrackData.results || []);
        setThresholds(thresholdData);
        setMetrics({
          processingRuns: Number(dashboard.processing_runs || 0),
          completedRuns: Number(dashboard.completed_runs || 0),
          failedRuns: Number(dashboard.failed_runs || 0),
          totalMeasurements: Number(dashboard.total_measurements || 0),
          averageForegroundPercent: dashboard.average_foreground_percent == null ? null : Number(dashboard.average_foreground_percent),
          videosMeasured: new Set(measurements.map((item) => item.video)).size,
          runs, measurements,
        });
      } else {
        setQueueData(null);
        setQueueEstimates(responses[1].results || []);
        setTrackingRuns([]);
        setPersonTracks([]);
        setMetrics(EMPTY_METRICS);
      }
      setApiStatus("Connected");
      setLastUpdated(new Date());
    } catch (error) {
      setApiStatus("Disconnected");
      setApiError(error instanceof Error ? error.message : "Unable to load data from Django.");
    } finally {
      setRefreshing(false);
    }
  }, [token, isAdmin]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  function navigate(page, videoId) {
    setActivePage(page);
    if (videoId) setSelectedVideo(videoId);
  }

  const activeItem = NAVIGATION
    .flatMap((section) => section.items)
    .find((item) => item.id === activePage);

  const ActivePage = !isAdmin
    ? CustomerDashboard
    : (PAGE_COMPONENTS[activePage] || Dashboard);

  const filteredNavigation = (isAdmin ? NAVIGATION : [{ section: "CUSTOMER", items: [{ id: "dashboard", label: "Queue status", icon: "◷" }] }])
    .map((section) => ({
      ...section,
      items: section.items.filter((item) =>
        item.label.toLowerCase().includes(search.toLowerCase()),
      ),
    }))
    .filter((section) => section.items.length > 0);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" onClick={() => navigate("dashboard")}>
          <span className="brand-mark">Q<span>•</span></span>
          <span className="brand-copy">
            <strong>QSR ANALYTICS</strong>
            <small>QUEUE INTELLIGENCE</small>
          </span>
        </button>

        <div className="workspace-switcher">
          <div className="workspace-avatar">Q</div>
          <div>
            <strong>Restaurant workspace</strong>
            <small>Local environment</small>
          </div>
          <span className="switch-arrow">⌄</span>
        </div>

        <div className="sidebar-search">
          <span>⌕</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Find a page..."
            aria-label="Find a page"
          />
          <kbd>/</kbd>
        </div>

        <nav className="sidebar-nav">
          {filteredNavigation.map((section) => (
            <div className="nav-section" key={section.section}>
              <div className="nav-section-title">{section.section}</div>
              {section.items.map((item) => (
                <button
                  key={item.id}
                  className={`nav-item ${activePage === item.id ? "active" : ""}`}
                  onClick={() => navigate(item.id)}
                >
                  <Icon>{item.icon}</Icon>
                  <span>{item.label}</span>
                  {item.id === "monitoring" && (
                    <span className="nav-count">2</span>
                  )}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="pulse-dot" />
            <div>
              <strong>API status</strong>
              <small>{apiStatus}</small>
            </div>
          </div>
          {isAdmin && <button className="help-link" onClick={() => navigate("settings")}>
            ⓘ <span>System status & settings</span>
          </button>}
          <div className="user-profile">
            <div className="profile-avatar">{(email[0] || "U").toUpperCase()}</div>
            <div className="profile-info">
              <strong>{email.split("@")[0]}</strong>
              <small>Preview session</small>
            </div>
            <button
              className="profile-menu-button"
              onClick={() => setProfileOpen((value) => !value)}
              aria-label="Profile menu"
            >
              •••
            </button>
            {profileOpen && (
              <div className="profile-popover">
                {isAdmin && <button onClick={() => navigate("settings")}>Account settings</button>}
                <button onClick={onLogout}>Sign out</button>
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span className="crumb-separator">/</span>
            <strong>{activeItem?.label || "Dashboard"}</strong>
          </div>
          <div className="topbar-right">
            <Badge tone={apiStatus === "Connected" ? "green" : "amber"}>
              {refreshing ? "Refreshing" : apiStatus}
            </Badge>
            <span className="topbar-date">
              {lastUpdated
                ? `Updated ${lastUpdated.toLocaleTimeString()}`
                : "QSR · Local environment"}
            </span>
            <button
              className="topbar-avatar"
              onClick={() => setProfileOpen((value) => !value)}
              aria-label="Open profile"
            >
              {(email[0] || "U").toUpperCase()}
            </button>
          </div>
        </header>

        <div className="page-content">
          <ActivePage
            navigate={navigate}
            email={email}
            lastUpdated={lastUpdated}
            isAdmin={isAdmin}
            token={token}
            thresholds={thresholds}
            onThresholdsSaved={setThresholds}
            metrics={metrics}
            apiStatus={apiStatus}
            apiError={apiError}
            refreshData={refreshData}
            selectedVideo={selectedVideo}
            setSelectedVideo={setSelectedVideo}
            queueData={queueData} queueEstimates={queueEstimates}
            trackingRuns={trackingRuns}
            personTracks={personTracks}
          />
          <footer className="app-footer">
            <span>QSR QUEUE ANALYTICS</span>
            <span>
              {isAdmin ? `${personTracks.length} saved person-track records · ${metrics.totalMeasurements} foreground measurements` : "Customer queue information only"}
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  
async function login(email, password) {
  const response = await fetch(`${API_BASE}/auth/token/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: email.trim(),
      password,
    }),
  });

  const data = await response.json();

  if (!response.ok || !data.access) {
    throw new Error(data.detail || "Login failed. Check your email and password.");
  }

  const meResponse = await fetch(`${API_BASE}/auth/me/`, {
  headers: {
    Authorization: `Bearer ${data.access}`,
  },
});

  const me = await meResponse.json();

  if (!meResponse.ok) {
    throw new Error(me.detail || "Unable to load account permissions.");
  }

  setEmail(me.email || email);
  setIsAdmin(Boolean(me.is_admin || me.is_staff || me.is_superuser));
  setToken(data.access);
}

  if (!token) return <LoginPage onLogin={login} />;
  return <Application email={email} token={token} isAdmin={isAdmin} onLogout={() => { setToken(""); setEmail(""); setIsAdmin(false); }} />;
}
