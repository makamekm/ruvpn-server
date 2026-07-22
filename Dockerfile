FROM python:3.11-slim

ARG TARGETARCH
ARG VCS_REF=unknown
ARG OLCRTC_REF=0b5019a9d19d9ecc8adbb4e20145b01eb12d5ed0

LABEL org.opencontainers.image.title="RUPN Server"
LABEL org.opencontainers.image.description="Single-room self-hosted RUPN server"
LABEL org.opencontainers.image.source="https://github.com/makamekm/ruvpn-server"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL io.rupn.olcrtc.revision="${OLCRTC_REF}"

WORKDIR /app

COPY bin/olcrtc-linux-${TARGETARCH} /usr/local/bin/olcrtc
COPY src/rupn_server /app/rupn_server

RUN chmod +x /usr/local/bin/olcrtc \
    && mkdir -p /var/lib/rupn-server

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
ENV RUPN_CLIENT_ID=android-01
ENV RUPN_DEBUG=false
ENV RUPN_PRINT_RAW_URI=false
ENV RUPN_ROTATE_ON_START=false
ENV RUPN_ENABLE_BAD_LOG_RESTART_WATCHDOG=false
ENV RUPN_BAD_AFTER_SECONDS=0
ENV RUPN_ENABLE_VP8_RESTART_WATCHDOG=false
ENV RUPN_VP8_INGRESS_FROZEN_AFTER_SECONDS=0
ENV RUPN_VP8_ZERO_INGRESS_AFTER_SECONDS=0
ENV RUPN_RESTART_BACKOFF_SECONDS=2

VOLUME ["/var/lib/rupn-server"]
ENTRYPOINT ["python3", "-m", "rupn_server.main"]
