# Stage 1: Build Vue frontend (native runner architecture for lightning-fast bundling)
FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM ghcr.io/home-assistant/base:latest

# Upgrade base packages and install Python + Pillow
RUN apk update && apk upgrade --no-cache && \
    apk add --no-cache \
        python3 \
        py3-pillow

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install exact locked production dependencies with uv
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-hashes -o requirements.txt && \
    uv pip install --system --break-system-packages --index-strategy unsafe-best-match --no-cache -r requirements.txt && \
    rm -f requirements.txt /usr/local/bin/uv /usr/bin/tempio

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend into Django static
COPY --from=frontend-build /app/frontend/dist ./backend/static/frontend/

# Copy run script
COPY run.sh /run.sh
RUN chmod a+x /run.sh

LABEL \
    io.hass.version="0.3.10" \
    io.hass.type="app" \
    io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
