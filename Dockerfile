FROM python:3.11-slim

ARG TARGETARCH
ARG VCS_REF=unknown
ARG OLCRTC_REF=e0f430332acb49dacd1c5835d340fb8f7a70b689

LABEL org.opencontainers.image.title="RUPN Server"
LABEL org.opencontainers.image.description="Single-room self-hosted RUPN server"
LABEL org.opencontainers.image.source="https://github.com/makamekm/ruvpn-server"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL io.rupn.olcrtc.revision="${OLCRTC_REF}"

# No RUN steps: the image is assembled from prebuilt files only, so buildx can
# produce linux/arm64 on an amd64 host without QEMU emulation.
WORKDIR /var/lib/rupn-server
WORKDIR /app

COPY --chmod=755 bin/olcrtc-linux-${TARGETARCH} /usr/local/bin/olcrtc
COPY src/rupn_server /app/rupn_server

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV OLCRTC_BIN=/usr/local/bin/olcrtc
ENV RUPN_DATA_DIR=/var/lib/rupn-server
ENV RUPN_STATE_FILE=/var/lib/rupn-server/server.json
ENV RUPN_CONNECTION_TYPE=telemost
ENV RUPN_LINK=direct
ENV RUPN_DNS=
ENV RUPN_TELEMOST_ROOM=
ENV RUPN_TELEMOST_ROOM_FACTORY_URL=
ENV RUPN_VP8_FPS=60
ENV RUPN_VP8_BATCH=32
ENV RUPN_DEBUG=false
ENV RUPN_PRINT_RAW_URI=false
ENV RUPN_ROTATE_ON_START=false
ENV RUPN_ENABLE_BAD_LOG_RESTART_WATCHDOG=false
ENV RUPN_BAD_AFTER_SECONDS=0
ENV RUPN_ENABLE_VP8_RESTART_WATCHDOG=true
ENV RUPN_VP8_INGRESS_FROZEN_AFTER_SECONDS=60
ENV RUPN_VP8_ZERO_INGRESS_AFTER_SECONDS=30
ENV RUPN_VP8_RESTART_BACKOFF_SECONDS=600
ENV RUPN_RESTART_BACKOFF_SECONDS=2

VOLUME ["/var/lib/rupn-server"]
ENTRYPOINT ["python3", "-m", "rupn_server.main"]
