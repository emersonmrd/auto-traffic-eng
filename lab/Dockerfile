FROM ubuntu:22.04

LABEL maintainer="Auto Traffic Engineering Lab"
LABEL description="Ubuntu 22.04 Lab Box with Containerlab, Python NetDevOps and Network Tools"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalação de utilitários essenciais, rede e Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    lsb-release \
    git \
    iproute2 \
    iputils-ping \
    iptables \
    dnsutils \
    tcpdump \
    tshark \
    telnet \
    openssh-client \
    net-tools \
    socat \
    bridge-utils \
    jq \
    vim \
    nano \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Instalação do Containerlab oficial
RUN bash -c "$(curl -sL https://get.containerlab.dev)"

# Instalação de bibliotecas Python para Automação de Rede e Backend
RUN pip3 install --no-cache-dir \
    netmiko \
    scrapli \
    scrapli-community \
    paramiko \
    asyncssh \
    pydantic \
    fastapi \
    uvicorn \
    aiogram \
    redis \
    psycopg2-binary \
    sqlalchemy \
    alembic \
    requests \
    httpx \
    pyyaml \
    rich

# Customização do prompt do shell
RUN echo 'export PS1="\[\e[1;36m\][auto-traffic-lab]\[\e[m\] \[\e[1;34m\]\w\[\e[m\] \$ "' >> /root/.bashrc

WORKDIR /workspace

CMD ["/bin/bash"]
