FROM python:3.11.16-slim-bookworm@sha256:2e32f7d302adc1c37428355c1e646897c0c53f4fd60b6a551245fb90ee129f91 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /src

COPY deploy/containers/build-tools.lock /locks/build-tools.lock
COPY deploy/containers/api/requirements.lock /locks/runtime-requirements.lock

RUN python -m venv /opt/build-venv \
 && /opt/build-venv/bin/pip install --require-hashes -r /locks/build-tools.lock

COPY sitescore-core/ sitescore-core/
COPY sitescore-data/ sitescore-data/
COPY sitescore-providers/ sitescore-providers/
COPY sitescore-spatial/ sitescore-spatial/
COPY sitescore-metrics/ sitescore-metrics/
COPY sitescore-benchmarks/ sitescore-benchmarks/
COPY sitescore-pipeline/ sitescore-pipeline/
COPY sitescore-app/ sitescore-app/
COPY sitescore-report/ sitescore-report/
COPY sitescore-api/ sitescore-api/

RUN mkdir -p /wheels \
 && for package in \
      sitescore-core \
      sitescore-data \
      sitescore-providers \
      sitescore-spatial \
      sitescore-metrics \
      sitescore-benchmarks \
      sitescore-pipeline \
      sitescore-app \
      sitescore-report \
      sitescore-api; do \
      /opt/build-venv/bin/pip wheel \
        --no-deps \
        --no-build-isolation \
        --wheel-dir /wheels \
        "/src/${package}"; \
    done \
 && python -m venv /opt/venv \
 && /opt/venv/bin/pip install --require-hashes -r /locks/runtime-requirements.lock \
 && /opt/venv/bin/pip install --no-deps /wheels/*.whl

FROM python:3.11.16-slim-bookworm@sha256:2e32f7d302adc1c37428355c1e646897c0c53f4fd60b6a551245fb90ee129f91 AS runtime-base

ARG DEBIAN_SNAPSHOT=20260821T000000Z
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY deploy/containers/api/apt-runtime.lock /tmp/apt-runtime.lock
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      "deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}/ bookworm main" \
      "deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}/ bookworm-security main" \
      > /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && xargs -r apt-get install -y --no-install-recommends < /tmp/apt-runtime.lock \
 && rm -rf /var/lib/apt/lists/* /tmp/apt-runtime.lock

COPY --from=builder /opt/venv /opt/venv
COPY deploy/containers/runtime/api-web.sh /opt/sitescore/bin/api-web
COPY deploy/containers/runtime/api-worker.sh /opt/sitescore/bin/api-worker
COPY deploy/containers/runtime/api-beat.sh /opt/sitescore/bin/api-beat
COPY deploy/containers/verify_image_contract.py /opt/sitescore/verify_image_contract.py
RUN chmod 0555 /opt/sitescore/bin/api-web /opt/sitescore/bin/api-worker /opt/sitescore/bin/api-beat \
 && chmod 0444 /opt/sitescore/verify_image_contract.py

WORKDIR /app
USER 10001:10001

FROM runtime-base AS test
USER 0:0
COPY deploy/containers/test-tools.lock /locks/test-tools.lock
RUN /opt/venv/bin/pip install --require-hashes -r /locks/test-tools.lock
COPY sitescore-api/tests/ /tests/sitescore-api/
COPY sitescore-report/tests/ /tests/sitescore-report/
USER 10001:10001
CMD ["python", "-m", "pytest", "-q", "/tests/sitescore-api", "/tests/sitescore-report"]

FROM runtime-base AS runtime
CMD ["/opt/sitescore/bin/api-web"]
