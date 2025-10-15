# Gunicorn configuration file for TranscriptionBot Django admin

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
accesslog = "/var/log/transcriptionbot/gunicorn_access.log"
errorlog = "/var/log/transcriptionbot/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "transcriptionbot_django"

# Server mechanics
daemon = False
pidfile = "/var/run/transcriptionbot/gunicorn.pid"
user = None  # Will be set by systemd
group = None  # Will be set by systemd
umask = 0
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None
