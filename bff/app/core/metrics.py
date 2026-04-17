from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


HTTP_REQUEST_TOTAL = Counter(
    "drmoto_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    "drmoto_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.3, 0.5, 1, 2, 5, 10),
)

HTTP_IN_PROGRESS = Gauge(
    "drmoto_http_in_progress",
    "Current in-flight HTTP requests",
)

APP_INFO = Gauge(
    "drmoto_app_info",
    "Application build info",
    ["version", "env"],
)


def metrics_content() -> bytes:
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST
