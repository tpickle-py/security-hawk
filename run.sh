#!/usr/bin/env bashio

# Read options (with fallbacks if Supervisor API is unavailable)
KIOSK_ENABLED="false"
KIOSK_PORT="8100"
KIOSK_TOKEN=""
QUIET_RETURN="120"
DEFAULT_VIEW="overview"

if bashio::config.has_value 'kiosk_enabled' 2>/dev/null; then
    KIOSK_ENABLED=$(bashio::config 'kiosk_enabled' 2>/dev/null || echo "false")
fi
if bashio::config.has_value 'kiosk_port' 2>/dev/null; then
    KIOSK_PORT=$(bashio::config 'kiosk_port' 2>/dev/null || echo "8100")
fi
if bashio::config.has_value 'kiosk_token' 2>/dev/null; then
    KIOSK_TOKEN=$(bashio::config 'kiosk_token' 2>/dev/null || echo "")
fi
if bashio::config.has_value 'quiet_return_seconds' 2>/dev/null; then
    QUIET_RETURN=$(bashio::config 'quiet_return_seconds' 2>/dev/null || echo "120")
fi
if bashio::config.has_value 'default_view' 2>/dev/null; then
    DEFAULT_VIEW=$(bashio::config 'default_view' 2>/dev/null || echo "overview")
fi

# Fallback values if empty
KIOSK_ENABLED="${KIOSK_ENABLED:-false}"
KIOSK_PORT="${KIOSK_PORT:-8100}"
QUIET_RETURN="${QUIET_RETURN:-120}"
DEFAULT_VIEW="${DEFAULT_VIEW:-overview}"

# Generate kiosk token if empty
if [ -z "$KIOSK_TOKEN" ]; then
    KIOSK_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    bashio::log.info "Generated kiosk token: $KIOSK_TOKEN"
fi

# Export for Django
export KIOSK_ENABLED KIOSK_PORT KIOSK_TOKEN QUIET_RETURN DEFAULT_VIEW
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-}"
export DATA_DIR="/data"

# Ensure data directories exist
mkdir -p /data/plans /data/assets /data/versions

# Run Django migrations
cd /app/backend
python3 manage.py collectstatic --noinput || true
python3 manage.py migrate --noinput || true

bashio::log.info "Starting Security Hawk..."

# Start Daphne on ingress port 8099
if [ "$KIOSK_ENABLED" = "true" ]; then
    bashio::log.info "Kiosk mode enabled on port $KIOSK_PORT"
    # Start ingress-facing Daphne in background
    daphne \
        -b 0.0.0.0 -p 8099 \
        --proxy-headers \
        securityhawk.asgi:application &

    # Start kiosk-facing Daphne in foreground
    exec daphne \
        -b 0.0.0.0 -p "$KIOSK_PORT" \
        --proxy-headers \
        securityhawk.asgi:application
else
    bashio::log.info "Starting Daphne on Ingress port 8099"
    exec daphne \
        -b 0.0.0.0 -p 8099 \
        --proxy-headers \
        securityhawk.asgi:application
fi
