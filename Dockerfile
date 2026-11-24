FROM python:3.15-slim-trixie

# Install system dependencies and SSH server
RUN apt-get update && apt-get install -y \
    openssh-server \
    git \
    curl \
    build-essential \
    pipx \
    && rm -rf /var/lib/apt/lists/*

# Install ruff for code formatting in dev environment
RUN pipx install ruff
ENV PATH="/root/.local/bin:${PATH}"

# Configure SSH
RUN mkdir -p /run/sshd /root/.ssh && \
    chmod 700 /root/.ssh

RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config

COPY .docker/authorized_keys /root/.ssh/authorized_keys

RUN chmod 600 /root/.ssh/authorized_keys

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-e"]