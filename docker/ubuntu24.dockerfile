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
# RUN mkdir -p ~/miniconda3 && wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh && bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3 & rm -rf ~/miniconda3/miniconda.sh

RUN mkdir -p /opt && chown -R $USERNAME:$USERNAME /opt
USER $USERNAME
WORKDIR /home/$USERNAME
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
 && bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda \
 && rm Miniconda3-latest-Linux-x86_64.sh
ENV PATH=/opt/conda/bin:$PATH
RUN conda init --all && conda config --set auto_activate false && conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
RUN conda create -y -n agent python=3.12
COPY requirements.txt /tmp/requirements.txt
COPY requirements_kb.txt /tmp/requirements_kb.txt
RUN conda run -n agent pip install -U -r /tmp/requirements.txt 
RUN conda run -n agent pip install -U -r /tmp/requirements_kb.txt
RUN mkdir -p /tmp/proj_dir && mkdir -p /tmp/work_dir
WORKDIR /tmp/proj_dir