# FAZ 7.1 application exact temporary security residual

Advisory: `CVE-2026-82049`
Package/version: `CPython 3.11.16`
Classification: `REVIEWER_ACCEPTED_TEMPORARY_UNREACHABLE_NO_SAME_SERIES_RELEASE_FIX`
Owner: FAZ7 security review

Runtime authority:

```text
python:3.11.16-slim-trixie
sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72
DEBIAN_SUITE=trixie
target=linux/amd64
```

Containment required for acceptance:

- raw Grype finding remains present in the application evidence;
- CISA KEV match count is zero;
- frozen runtime application source contains no `import tarfile`, `from tarfile`, `tarfile.extract*`, `extractall`, or `shutil.unpack_archive`;
- no public application source path advertises tar/tar.gz/tgz archive ingestion;
- runtime helper scripts do not invoke tarfile extraction;
- API, report, Commerce and FAZ6 replay regressions remain green.

This is an exact temporary residual only. It is not a generic Python HIGH waiver, scanner suppression, or SiteScore-authored VEX.

Expiry / automatic re-review trigger: first of a fixed Python 3.11.x security release, a suitable official CPython 3.11 backport, introduction of any tar/tar.gz ingestion or extraction path, or before PUBLIC_LAUNCH authorization.
