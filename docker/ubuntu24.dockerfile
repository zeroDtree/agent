FROM ubuntu:24.04
LABEL maintainer="3186428803@qq.com"
ENV INDOCK_USER=root
ENV USERNAME=ubuntu
WORKDIR /root
ARG UID=1000
ARG GID=1000

RUN if ! id -u $UID >/dev/null 2>&1; then \
        useradd -u ${UID} -g ${GID} -m $USERNAME; \
    fi
RUN usermod -m -d /home/$USERNAME $USERNAME

RUN apt update && apt install -y curl vim git build-essential fish zsh wget net-tools csh nvtop tmux openbabel iproute2 autoconf

RUN apt install -y netcat-openbsd

RUN mkdir -p /opt && chown -R $USERNAME:$USERNAME /opt
USER $USERNAME
WORKDIR /home/$USERNAME

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH=/home/$USERNAME/.local/bin:$PATH

COPY --chown=$USERNAME pyproject.toml uv.lock /tmp/agent/
RUN cd /tmp/agent && uv sync --frozen

RUN mkdir -p /tmp/proj_dir && mkdir -p /tmp/work_dir
WORKDIR /tmp/proj_dir