"""
Gunicorn configuration for production deployment on Render.
Automatically binds to Render's dynamic PORT environment variable.
"""

import os

# Dynamic port binding from Render environment
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Worker processes and threading configuration
# Render Free tier provides 512MB RAM; 2 sync workers with 2 threads each is optimal and lightweight
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = int(os.environ.get("PYTHON_THREADS", 2))
worker_class = "sync"

# Request timeouts
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = 5

# Logging to stdout/stderr for Render live log streaming
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
capture_output = True
