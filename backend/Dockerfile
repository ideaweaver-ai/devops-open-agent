FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates openssh-client \
    && ARCH="$(uname -m)" \
    && case "$ARCH" in \
        x86_64) KUBECTL_ARCH=amd64 ;; \
        aarch64|arm64) KUBECTL_ARCH=arm64 ;; \
        *) echo "Unsupported architecture: $ARCH" && exit 1 ;; \
       esac \
    && curl -fsSLo /usr/local/bin/kubectl \
        "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/${KUBECTL_ARCH}/kubectl" \
    && chmod +x /usr/local/bin/kubectl \
    && TRIVY_VERSION=$(curl -fsSL https://api.github.com/repos/aquasecurity/trivy/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/') \
    && case "$KUBECTL_ARCH" in \
        amd64) TRIVY_ARCH=Linux-64bit ;; \
        arm64) TRIVY_ARCH=Linux-ARM64 ;; \
       esac \
    && curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_${TRIVY_ARCH}.tar.gz" \
       | tar -xzf - -C /usr/local/bin trivy \
    && chmod +x /usr/local/bin/trivy \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
