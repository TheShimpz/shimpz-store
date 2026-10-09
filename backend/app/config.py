"""Environment-derived Store limits, endpoints, and cache policies."""

import os
from pathlib import Path

from app.ratelimit import trusted_proxies

BUILD = Path(os.environ.get("SHIMPZ_STORE_BUILD", "/app/build"))
DEVELOPERS_URL = os.environ.get("SHIMPZ_DEVELOPERS_URL", "http://developers-api:8080")
MAX_OAUTH_BODY_BYTES = 32 * 1024
CONTROL_WORKER_THREADS = max(1, int(os.environ.get("SHIMPZ_STORE_CONTROL_WORKER_THREADS", "8")))
CONTROL_QUEUE_MAX = max(0, int(os.environ.get("SHIMPZ_STORE_CONTROL_QUEUE_MAX", "8")))
OAUTH_WORKER_THREADS = max(1, int(os.environ.get("SHIMPZ_STORE_OAUTH_WORKER_THREADS", "8")))
OAUTH_QUEUE_MAX = max(0, int(os.environ.get("SHIMPZ_STORE_OAUTH_QUEUE_MAX", "8")))
HTML_CACHE_CONTROL = "public, no-cache, max-age=0, must-revalidate, no-transform"
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
PRIVATE_NO_STORE_HEADERS = {"Cache-Control": "private, no-store"}
# The tunnel connector's edge network; only a peer inside it may name the client of an OAuth start.
TRUSTED_PROXIES = trusted_proxies(os.environ.get("SHIMPZ_STORE_TRUSTED_PROXY_CIDRS"))
# The same budget as Cloudflare's zone rule: ten starts per client per minute.
OAUTH_START_CAPACITY = 10
OAUTH_START_PERIOD_SECONDS = 60.0
OAUTH_START_MAX_CLIENTS = 4096
