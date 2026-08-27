# Standalone Testnet runtime image only. This is not a Dokploy deployment contract.
FROM python:3.11.16-slim-bookworm@sha256:0bee7276f83efd4a1ee05bbbf4281d95ed28e079220a9457f25a93e3f1e3c31b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VERUS_NETWORK=testnet \
    VERUS_UAI_INTEGRATION_ENABLED=false

WORKDIR /app

COPY requirements.runtime.lock ./requirements.runtime.lock
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.runtime.lock

COPY . ./verus_agent

RUN useradd --create-home --uid 10001 verusagent \
    && chown -R verusagent:verusagent /app

USER verusagent
EXPOSE 9124

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9124/health', timeout=3).read()"]

CMD ["python", "-m", "verus_agent.agent"]
