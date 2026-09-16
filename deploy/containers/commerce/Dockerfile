ARG SOURCE_REVISION=unknown
ARG SOURCE_VERSION=unknown

FROM python:3.11.16-slim-trixie@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /src

COPY deploy/containers/build-tools.lock /locks/build-tools.lock
COPY deploy/containers/commerce/requirements.lock /locks/runtime-requirements.lock
RUN python -m venv /opt/build-venv \
 && /opt/build-venv/bin/pip install --require-hashes -r /locks/build-tools.lock

COPY sitescore-commerce/ sitescore-commerce/
RUN mkdir -p /wheels \
 && /opt/build-venv/bin/pip wheel \
      --no-deps \
      --no-build-isolation \
      --wheel-dir /wheels \
      /src/sitescore-commerce \
 && python -m venv /opt/venv \
 && /opt/venv/bin/pip install --require-hashes -r /locks/runtime-requirements.lock \
 && /opt/venv/bin/pip install --no-deps /wheels/*.whl

FROM python:3.11.16-slim-trixie@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72 AS runtime-base

ARG SOURCE_REVISION
ARG SOURCE_VERSION
ARG DEBIAN_SNAPSHOT=20260916T000000Z
LABEL org.opencontainers.image.source="https://github.com/metadoks/sitescore" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.version="${SOURCE_VERSION}" \
      org.opencontainers.image.title="sitescore-commerce"
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/xdg-cache \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY deploy/containers/apt-security-runtime.lock /tmp/apt-security-runtime.lock
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf '%s\n' \
      "deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}/ trixie main" \
      "deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}/ trixie-security main" \
      > /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && xargs -r apt-get install -y --only-upgrade --no-install-recommends < /tmp/apt-security-runtime.lock \
 && while IFS='=' read -r package version; do \
      current="$(dpkg-query -W -f='${Version}' "$package" 2>/dev/null || true)"; \
      if [ -n "$current" ]; then test "$current" = "$version"; fi; \
    done < /tmp/apt-security-runtime.lock \
 && rm -rf /var/lib/apt/lists/* /tmp/apt-security-runtime.lock

COPY --from=builder /opt/venv /opt/venv
COPY deploy/containers/runtime/commerce-web.sh /opt/sitescore/bin/commerce-web
COPY deploy/containers/runtime/commerce-dispatcher-supervisor.py /opt/sitescore/bin/commerce-dispatcher-supervisor.py
COPY deploy/containers/verify_image_contract.py /opt/sitescore/verify_image_contract.py
RUN rm -rf \
      /usr/local/lib/python3.11/site-packages/setuptools \
      /usr/local/lib/python3.11/site-packages/setuptools-*.dist-info \
      /opt/venv/lib/python3.11/site-packages/setuptools \
      /opt/venv/lib/python3.11/site-packages/setuptools-*.dist-info \
 && chmod 0555 /opt/sitescore/bin/commerce-web /opt/sitescore/bin/commerce-dispatcher-supervisor.py \
 && chmod 0444 /opt/sitescore/verify_image_contract.py

WORKDIR /app
USER 10001:10001

FROM runtime-base AS test
USER 0:0
COPY deploy/containers/test-tools.lock /locks/test-tools.lock
RUN /opt/venv/bin/pip install --require-hashes -r /locks/test-tools.lock
COPY sitescore-commerce/ /testsrc/sitescore-commerce/
USER 10001:10001
WORKDIR /testsrc/sitescore-commerce
CMD ["python", "-m", "pytest", "-q", "tests"]

FROM runtime-base AS runtime
CMD ["/opt/sitescore/bin/commerce-web"]
