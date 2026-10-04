#!/usr/bin/env bashio

# Read options
KIOSK_ENABLED=$(bashio::config 'kiosk_enabled')
KIOSK_PORT=$(bashio::config 'kiosk_port')
KIOSK_TOKEN=$(bashio::config 'kiosk_token')
QUIET_RETURN=$(bashio::config 'quiet_return_seconds')
DEFAULT_VIEW=$(bashio::config 'default_view')

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

# Run Django migrations (lightweight — only for channels/sessions if needed)
cd /app/backend
python3 manage.py collectstatic --noinput 2>/dev/null
python3 manage.py migrate --noinput 2>/dev/null

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
    exec daphne \
        -b 0.0.0.0 -p 8099 \
        --proxy-headers \
        securityhawk.asgi:application
fi
