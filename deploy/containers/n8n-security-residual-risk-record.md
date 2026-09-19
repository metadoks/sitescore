# FAZ 7.1 n8n exact residual security risk record

This file records only residuals explicitly authorized by the Reviewer. It is not OpenVEX and does not suppress scanner output.

## @tiptap/core 3.27.0

Advisory: `GHSA-j95f-988m-3j2f`
Disposition: Reviewer-authorized editor/UI-only residual, conditional on terminal containment proof.
Containment: the frozen production workflows contain no Tiptap or Markdown node path; n8n editor/admin/API exposure remains loopback-only/non-public.
Re-review trigger: before public launch, editor exposure change, workflow change introducing Markdown/editor parsing, or upstream Tiptap-family adoption.

## pcre2 10.47-r1

Advisory: `CVE-2026-89157`
Disposition: architecture-not-affected residual only for the product target `linux/amd64`.
Evidence requirement: raw finding retained; final image architecture must be amd64; scanner must report no fixed package version.
Re-review trigger: package fix publication or before public launch.

`CVE-2026-89161` is NOT accepted by this record and remains blocking unless remediated or separately authorized.

## zlib 1.3.2-r0

Advisory: `CVE-2026-85091`
Disposition: Reviewer-accepted upstream-unfixed residual only when the exact final scan reports no fixed version and Alpine 3.24 repository evidence shows no fixed/backported package selected.
Owner: FAZ7 security review.
Re-review trigger: package fix publication or before public launch.

Raw Grype findings remain visible for every residual above. No scanner ignore, suppression, or SiteScore-authored VEX is permitted.
