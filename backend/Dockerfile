# ============================================================
# PS5 Monitoring Service - Production Docker Image
# ============================================================
#
# Platform:
#   Home Assistant OS / ARM64
#
# Runtime:
#   Python 3.13 Alpine
#   Paho MQTT 2.1.0
#   SQLite
#
# Security:
#   - Root is used only during entrypoint initialization.
#   - Python runs as UID 100 / GID 101.
#   - Supervisor options remain root-owned.
#   - Temporary credentials are stored under private /run.
# ============================================================

ARG BUILD_FROM=python:3.13-alpine
FROM ${BUILD_FROM}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install the privilege-dropping utility.
RUN apk add --no-cache su-exec

# Install pinned Python dependencies.
COPY requirements.txt /app/requirements.txt

RUN pip install \
    --no-cache-dir \
    --disable-pip-version-check \
    --requirement /app/requirements.txt

# Create the dedicated unprivileged application account.
RUN addgroup -S ps5monitor \
    && adduser -S -G ps5monitor ps5monitor \
    && mkdir -p /data /run/ps5-monitor \
    && chown ps5monitor:ps5monitor /run/ps5-monitor \
    && chmod 700 /run/ps5-monitor

# Copy the application source.
COPY --chown=ps5monitor:ps5monitor app/ /app/

# Copy the privileged startup script.
COPY entrypoint.sh /usr/local/bin/ps5-entrypoint.sh

# Keep the entrypoint readable but not writable by normal users.
RUN chown root:root /usr/local/bin/ps5-entrypoint.sh \
    && chmod 755 /usr/local/bin/ps5-entrypoint.sh

# Root is required only for preparing the protected config.
# The entrypoint drops privileges before launching Python.
USER root

ENTRYPOINT ["/bin/sh", "/usr/local/bin/ps5-entrypoint.sh"]
