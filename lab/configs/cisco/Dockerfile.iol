FROM public.ecr.aws/docker/library/debian:bookworm-slim

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libc6:i386 \
    libstdc++6:i386 \
    libssl3:i386 \
    iproute2 \
    iputils-ping \
    net-tools \
    sudo \
    curl \
    python3 \
    ca-certificates \
    gnupg \
    && apt-get clean

RUN ln -sf /usr/lib/i386-linux-gnu/libcrypto.so.3 /usr/lib/i386-linux-gnu/libcrypto.so.4 2>/dev/null || true

RUN echo 'deb [trusted=yes] https://netdevops.fury.site/apt/ /' | \
sudo tee -a /etc/apt/sources.list.d/netdevops.list

RUN apt-get update && \
    apt-get install -y iouyap

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /iol

COPY *.bin /iol/iol.bin
RUN chmod +x /iol/iol.bin

ENTRYPOINT ["/entrypoint.sh"]
