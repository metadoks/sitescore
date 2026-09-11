# FAZ 7.1 n8n nodemailer residual risk record

Advisory: `GHSA-p6gq-j5cr-w38f`
Package/version: `nodemailer@8.0.10`
Owner: SiteScore owner/operator
Status: conditionally accepted only if it is the sole residual HIGH after exact-candidate OpenVEX/KEV reconciliation
Expiry: `2026-10-11`

Containment controls required for acceptance:

- Frozen SiteScore n8n workflows do not use `n8n-nodes-base.emailSend`.
- `NODES_EXCLUDE` contains `emailSend`, `executeCommand`, `localFileTrigger`, and `snowflake`.
- No SMTP transport is configured in the frozen n8n runtime definition.
- Editor/admin/API exposure remains non-public in the target deployment design; the current compose bind remains loopback-only.
- No second residual CRITICAL/HIGH exception is authorized.

Re-review is mandatory before expiry and immediately if any of the following changes: n8n candidate identity, nodemailer remediation status, workflow bytes, node exclusions, SMTP configuration, network exposure, CISA KEV status, or a new reachable advisory affecting the enabled runtime.
