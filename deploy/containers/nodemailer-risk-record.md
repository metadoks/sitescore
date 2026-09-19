# FAZ 7.1 n8n nodemailer residual risk record

Advisories:
- `GHSA-p6gq-j5cr-w38f`
- `GHSA-2x7j-588g-ccc2`

Package/version: `nodemailer@8.0.10`
Owner: FAZ7 security review
Status: Reviewer-authorized exact residuals only while containment remains true
Expiry/re-review trigger: before public launch, upstream n8n adoption, nodemailer fix adoption, or any containment change

Containment controls required for acceptance:

- Frozen SiteScore n8n workflows do not use `n8n-nodes-base.emailSend`.
- `NODES_EXCLUDE` contains `emailSend`, `executeCommand`, `localFileTrigger`, and `snowflake`.
- No SMTP / `N8N_EMAIL_MODE` / `N8N_SMTP` transport is configured.
- Editor/admin/API exposure remains non-public; deployment compose binds n8n to loopback.
- Raw Grype findings remain present in terminal evidence.
- No nodemailer major/family leap or source patch is authorized in this checkpoint.
