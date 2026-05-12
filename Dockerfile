FROM python:3.11-slim

LABEL org.opencontainers.image.title="RUPN Server"
LABEL org.opencontainers.image.description="Single-instance RUPN server container"
LABEL org.opencontainers.image.source="https://github.com/makamekm/ruvpn-server"

WORKDIR /app

COPY bin/olcrtc-linux-amd64 /usr/local/bin/olcrtc
COPY src/rupn_server /app/rupn_server

RUN chmod +x /usr/local/bin/olcrtc \
    && mkdir -p /var/lib/rupn-server

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV OLCRTC_BIN=/usr/local/bin/olcrtc
ENV RUPN_DATA_DIR=/var/lib/rupn-server
ENV RUPN_STATE_FILE=/var/lib/rupn-server/server.json
ENV RUPN_CARRIER=wbstream
ENV RUPN_TRANSPORT=datachannel
ENV RUPN_LINK=direct
ENV RUPN_DNS=1.1.1.1:53
ENV RUPN_CLIENT_ID=android-01
ENV RUPN_DEBUG=false
ENV RUPN_ROTATE_ON_START=false

VOLUME ["/var/lib/rupn-server"]
ENTRYPOINT ["python3", "-m", "rupn_server.main"]
