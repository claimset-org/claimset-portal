FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# git: the claimset package is installed from its repository at a pinned commit.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 portal

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install .

# Named volumes take their owner from these folders when first created, so the app (not root) can write to them.
RUN mkdir -p /srv/published /srv/registry /srv/submissions && chown portal /srv/published /srv/registry /srv/submissions

USER portal
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status == 200 else 1)"
CMD ["portal", "serve", "--port", "8000"]
