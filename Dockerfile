# Use Python 3.11.11 slim image
FROM python:3.11.11-slim-bullseye
LABEL maintainer=support@fast.bi

# Set working directory
WORKDIR /app

ENV HELM_VERSION="v3.17.3"
ENV KUBECTL_VERSION="v1.32.3"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    apache2-utils \
    && curl -LO https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz \
    && tar -zxvf helm-${HELM_VERSION}-linux-amd64.tar.gz \
    && mv linux-amd64/helm /usr/local/bin/helm \
    && curl -LO https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm -rf /var/lib/apt/lists/* linux-amd64 helm-${HELM_VERSION}-linux-amd64.tar.gz kubectl

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 6798

# Run the application with Gunicorn
# Set timeout to 30 minutes (1800 seconds) to allow for long-running Helm deployments
CMD ["gunicorn", "--bind", "0.0.0.0:6798", "--workers", "4", "--timeout", "1800", "app:create_app()"] 