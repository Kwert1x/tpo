FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        curl \
        git \
        ipmitool \
        python3 \
        python3-pip \
        python3-venv \
        qemu-system-arm \
    && python3 -m venv /opt/tpo-venv \
    && /opt/tpo-venv/bin/pip install --no-cache-dir \
        locust==2.32.6 \
        pytest==8.3.5 \
        pytest-html==4.1.1 \
        requests==2.32.3 \
        selenium==4.25.0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN jenkins-plugin-cli --plugins \
    credentials-binding \
    git \
    junit \
    workflow-aggregator

ENV PATH="/opt/tpo-venv/bin:${PATH}"
ENV SELENIUM_BROWSER="chrome"
ENV SELENIUM_HEADLESS="1"

USER jenkins
