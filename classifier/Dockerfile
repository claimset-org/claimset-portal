# The classifier service: OpenAlex's open topic model, CPU only. The model and OpenAlex's topic list are fetched
# at build, and the build fails if a model label matches no OpenAlex topic.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 CLASSIFIER_DIR=/opt/classifier \
    HF_HUB_DISABLE_TELEMETRY=1

RUN useradd --create-home --uid 10002 classifier
WORKDIR /srv
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY labels.py download.py server.py ./
ARG CLASSIFIER_MODEL_REVISION=main
RUN CLASSIFIER_MODEL_REVISION=${CLASSIFIER_MODEL_REVISION} python download.py \
 && chown -R classifier /opt/classifier

USER classifier
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/healthz').status == 200 else 1)"
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
