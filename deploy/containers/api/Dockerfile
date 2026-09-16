ARG SOURCE_REVISION=unknown
ARG SOURCE_VERSION=unknown

FROM python:3.11.16-slim-trixie@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72 AS builder

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

FROM python:3.11.16-slim-trixie@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72 AS runtime-base

ARG SOURCE_REVISION
ARG SOURCE_VERSION
ARG DEBIAN_SNAPSHOT=20260910T000000Z
LABEL org.opencontainers.image.source="https://github.com/metadoks/sitescore" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.version="${SOURCE_VERSION}" \
      org.opencontainers.image.title="sitescore-api"
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/xdg-cache \
    MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY deploy/containers/api/apt-runtime.lock /tmp/apt-runtime.lock
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      "deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}/ trixie main" \
      "deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}/ trixie-security main" \
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
COPY sitescore-api/ /testsrc/sitescore-api/
COPY sitescore-report/ /testsrc/sitescore-report/
USER 10001:10001
WORKDIR /testsrc
CMD ["python", "-m", "pytest", "-q", "/testsrc/sitescore-api/tests", "/testsrc/sitescore-report/tests"]

FROM runtime-base AS runtime
CMD ["/opt/sitescore/bin/api-web"]
