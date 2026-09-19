# FAZ 7.1 n8n exact residual security risk record

This file records only residuals explicitly authorized by the Reviewer. It is not OpenVEX and does not suppress scanner output.

## @tiptap/core 3.27.0

Advisory: `GHSA-j95f-988m-3j2f`
Disposition: Reviewer-authorized editor/UI-only residual, conditional on terminal containment proof.
Containment: frozen production workflows contain no Tiptap or Markdown node path; n8n editor/admin/API exposure remains loopback-only/non-public.
Re-review trigger: before public launch, editor exposure change, workflow change introducing Markdown/editor parsing, or upstream Tiptap-family adoption.

## zlib 1.3.2-r0

Advisory: `CVE-2026-85091`
Disposition: `REVIEWER_ACCEPTED_UPSTREAM_UNFIXED_RESIDUAL` only while the exact final scan reports no fixed Alpine 3.24 package version and CISA KEV remains zero.
Owner: FAZ7 security review.
Re-review trigger: package fix publication or before public launch.

## pcre2 / Git capability

No pcre2 residual is authorized in the final candidate. The Git and Git Tool nodes are excluded, runtime package `git` is pruned, and terminal evidence must prove both `git` and `pcre2` absent.

Raw Grype findings remain visible for every surviving authorized residual. No scanner ignore, suppression, or SiteScore-authored VEX is permitted.
