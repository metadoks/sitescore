#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'deploy/containers/artifacts/n8n-vendor-openvex-reconciliation')

def load(name):
    return json.load(open(ROOT / name, encoding='utf-8'))

def norm_id(value):
    if not value:
        return None
    s = str(value).strip()
    m = re.search(r'(?i)\b(CVE-\d{4}-\d{4,})\b', s)
    if m:
        return m.group(1).upper()
    m = re.search(r'(?i)\b(GHSA-[0-9A-Za-z]{4}-[0-9A-Za-z]{4}-[0-9A-Za-z]{4})\b', s)
    if m:
        return m.group(1).upper()
    return None

def extract_ids(obj):
    found = set()
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in {'id', '@id', 'name', 'url', 'dataSource'} and isinstance(v, str):
                    n = norm_id(v)
                    if n:
                        found.add(n)
                if k in {'urls', 'aliases', 'relatedVulnerabilities', 'advisories'}:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            n = norm_id(x)
            if n:
                found.add(n)
    walk(obj)
    return found

def scanner_aliases(match):
    ids = set()
    v = match.get('vulnerability') or {}
    n = norm_id(v.get('id'))
    if n:
        ids.add(n)
    ids |= extract_ids(v.get('urls') or [])
    ids |= extract_ids(v.get('advisories') or [])
    for related in match.get('relatedVulnerabilities') or []:
        n = norm_id((related or {}).get('id'))
        if n:
            ids.add(n)
        ids |= extract_ids((related or {}).get('urls') or [])
    ids |= extract_ids(v.get('epss') or [])
    ids |= extract_ids(v.get('cwes') or [])
    return sorted(ids)

def vex_aliases(statement):
    return sorted(extract_ids((statement or {}).get('vulnerability') or {}))

def parse_purl(purl):
    s = unquote(str(purl or ''))
    m = re.match(r'^pkg:([^/]+)/(?:(.*?)/)?([^/@]+)(?:@([^?]+))?(?:\?.*)?$', s)
    if not m:
        return {'raw': s, 'type': None, 'namespace': None, 'name': None, 'version': None}
    return {'raw': s, 'type': m.group(1), 'namespace': m.group(2), 'name': m.group(3), 'version': m.group(4)}

def product_applicability(statement, artifact, selected_version):
    products = statement.get('products') or []
    if not isinstance(products, list):
        return False, ['products_not_list'], []
    evidence = []
    reasons = []
    artifact_name = str(artifact.get('name') or '')
    artifact_version = str(artifact.get('version') or '')
    artifact_type = str(artifact.get('type') or '')
    for product in products:
        if isinstance(product, str):
            product = {'@id': product}
        if not isinstance(product, dict):
            continue
        pid = str(product.get('@id') or product.get('id') or '')
        pp = parse_purl(pid)
        parent_ok = False
        parent_reason = ''
        if pid == 'pkg:docker/n8nio/n8n':
            parent_ok = True
            parent_reason = 'exact_n8nio_n8n_product_id_from_exact_release_asset'
        elif pp['type'] == 'docker' and pp['namespace'] == 'n8nio' and pp['name'] == 'n8n' and pp['version'] == selected_version:
            parent_ok = True
            parent_reason = 'versioned_n8nio_n8n_product_matches_selected_release'
        if not parent_ok:
            evidence.append({'product_id': pid, 'parent_match': False, 'reason': 'product_id_not_selected_n8nio_n8n'})
            continue
        subs = product.get('subcomponents') or []
        if not subs:
            evidence.append({'product_id': pid, 'parent_match': True, 'parent_reason': parent_reason, 'subcomponent_required': False, 'applicable': True})
            return True, reasons, evidence
        exact_sub = False
        sub_evidence = []
        for sub in subs:
            sid = sub.get('@id') if isinstance(sub, dict) else sub
            sp = parse_purl(sid)
            name_ok = sp['name'] == artifact_name
            version_ok = sp['version'] == artifact_version
            type_ok = (not sp['type']) or sp['type'] == artifact_type
            ok = bool(name_ok and version_ok and type_ok)
            sub_evidence.append({'subcomponent_id': sid, 'parsed': sp, 'artifact_name': artifact_name, 'artifact_version': artifact_version, 'artifact_type': artifact_type, 'name_match': name_ok, 'version_match': version_ok, 'type_match': type_ok, 'exact_match': ok})
            exact_sub = exact_sub or ok
        evidence.append({'product_id': pid, 'parent_match': True, 'parent_reason': parent_reason, 'subcomponent_required': True, 'subcomponents': sub_evidence, 'applicable': exact_sub})
        if exact_sub:
            return True, reasons, evidence
        reasons.append('parent_product_matches_but_no_exact_scanned_subcomponent_match')
    if not evidence:
        reasons.append('no_usable_product_entries')
    return False, reasons, evidence

g = load('n8n.grype.json')
vex = load('upstream.openvex.json')
kev_data = load('cisa-kev.json')
release = load('release-context.json')
verification = load('openvex-asset-verification.json')
if not verification.get('verified'):
    raise SystemExit('OpenVEX release asset digest verification is not true')
selected_version = str(release['selected_version'])
kev = {norm_id(v.get('cveID')) for v in kev_data.get('vulnerabilities', []) if norm_id(v.get('cveID'))}

vex_entries = []
for idx, st in enumerate(vex.get('statements', [])):
    vex_entries.append({'index': idx, 'aliases': vex_aliases(st), 'statement': st})

blocking_keys = [
    'N8N_CISA_KEV_MATCHES',
    'N8N_VENDOR_AFFECTED_CRITICAL','N8N_VENDOR_AFFECTED_HIGH',
    'N8N_VENDOR_UNDER_INVESTIGATION_CRITICAL','N8N_VENDOR_UNDER_INVESTIGATION_HIGH',
    'N8N_VEX_SCANNER_CONFLICT_CRITICAL','N8N_VEX_SCANNER_CONFLICT_HIGH',
    'N8N_REMEDIABLE_UNDISPOSITIONED_CRITICAL','N8N_REMEDIABLE_UNDISPOSITIONED_HIGH',
    'N8N_UNDISPOSITIONED_CRITICAL','N8N_UNDISPOSITIONED_HIGH',
]
summary = {k: 0 for k in blocking_keys}
summary.update({
    'N8N_RAW_CRITICAL': 0, 'N8N_RAW_HIGH': 0,
    'N8N_VEX_NOT_AFFECTED_ALLOWED_CRITICAL': 0, 'N8N_VEX_NOT_AFFECTED_ALLOWED_HIGH': 0,
    'N8N_UPSTREAM_UNFIXED_NO_KEV_RISK_RECORDED_CRITICAL': 0,
    'N8N_UPSTREAM_UNFIXED_NO_KEV_RISK_RECORDED_HIGH': 0,
})
rows = []
for match in g.get('matches', []):
    v = match.get('vulnerability') or {}
    severity = str(v.get('severity') or '').upper()
    if severity not in {'CRITICAL','HIGH'}:
        continue
    summary[f'N8N_RAW_{severity}'] += 1
    artifact = match.get('artifact') or {}
    aliases = scanner_aliases(match)
    cve_aliases = [a for a in aliases if a.startswith('CVE-')]
    kev_hits = sorted(set(cve_aliases) & kev)
    fix = v.get('fix') or {}
    fixed_versions = list(fix.get('versions') or [])
    fix_state = str(fix.get('state') or '').lower()

    candidate_vex = []
    applicable = []
    for ve in vex_entries:
        shared = sorted(set(aliases) & set(ve['aliases']))
        if not shared:
            continue
        ok, reasons, evidence = product_applicability(ve['statement'], artifact, selected_version)
        item = {'statement_index': ve['index'], 'shared_aliases': shared, 'vex_aliases': ve['aliases'], 'status': str(ve['statement'].get('status') or ''), 'product_applicable': ok, 'product_applicability_reasons': reasons, 'product_applicability_evidence': evidence, 'statement': ve['statement']}
        candidate_vex.append(item)
        if ok:
            applicable.append(item)

    statuses = {str(x['status']).lower() for x in applicable}
    if kev_hits:
        disposition = 'BLOCKED_KEV'; rationale = f'CISA KEV alias match: {kev_hits}'; summary['N8N_CISA_KEV_MATCHES'] += 1
    elif len(statuses) > 1:
        disposition = 'BLOCKED_UNDISPOSITIONED'; rationale = f'conflicting applicable vendor VEX statuses: {sorted(statuses)}'; summary[f'N8N_UNDISPOSITIONED_{severity}'] += 1
    elif 'affected' in statuses:
        disposition = 'BLOCKED_VENDOR_AFFECTED'; rationale = 'applicable exact-release vendor OpenVEX status=affected'; summary[f'N8N_VENDOR_AFFECTED_{severity}'] += 1
    elif 'under_investigation' in statuses:
        disposition = 'BLOCKED_VENDOR_UNDER_INVESTIGATION'; rationale = 'applicable exact-release vendor OpenVEX status=under_investigation'; summary[f'N8N_VENDOR_UNDER_INVESTIGATION_{severity}'] += 1
    elif 'fixed' in statuses:
        disposition = 'BLOCKED_VEX_SCANNER_CONFLICT'; rationale = 'applicable vendor OpenVEX says fixed while raw scanner still reports selected image/package vulnerable'; summary[f'N8N_VEX_SCANNER_CONFLICT_{severity}'] += 1
    elif statuses == {'not_affected'}:
        statements = [x['statement'] for x in applicable]
        sufficient = all((s.get('justification') and (s.get('impact_statement') or s.get('action_statement'))) for s in statements)
        if sufficient:
            disposition = 'VEX_NOT_AFFECTED_ALLOWED'; rationale = 'applicable exact-release vendor OpenVEX status=not_affected with justification/statement retained'; summary[f'N8N_VEX_NOT_AFFECTED_ALLOWED_{severity}'] += 1
        else:
            disposition = 'BLOCKED_UNDISPOSITIONED'; rationale = 'vendor not_affected statement lacks required justification/impact or action statement'; summary[f'N8N_UNDISPOSITIONED_{severity}'] += 1
    elif applicable:
        disposition = 'BLOCKED_UNDISPOSITIONED'; rationale = f'unsupported/ambiguous applicable VEX status set: {sorted(statuses)}'; summary[f'N8N_UNDISPOSITIONED_{severity}'] += 1
    elif fixed_versions or fix_state == 'fixed':
        disposition = 'BLOCKED_REMEDIABLE_UNDISPOSITIONED'; rationale = 'no applicable vendor VEX statement; scanner reports fixed version/fixed state'; summary[f'N8N_REMEDIABLE_UNDISPOSITIONED_{severity}'] += 1
    elif fix_state in {'not-fixed','wont-fix'}:
        disposition = 'UPSTREAM_UNFIXED_NO_KEV_RISK_RECORDED'; rationale = f'no applicable vendor VEX; scanner fix state={fix_state}; no CISA KEV alias match'; summary[f'N8N_UPSTREAM_UNFIXED_NO_KEV_RISK_RECORDED_{severity}'] += 1
    else:
        disposition = 'BLOCKED_UNDISPOSITIONED'; rationale = f'no applicable vendor VEX and scanner fix state={fix_state or "unknown"}'; summary[f'N8N_UNDISPOSITIONED_{severity}'] += 1

    rows.append({
        'scanner_advisory_id': v.get('id'), 'scanner_alias_ids': aliases,
        'severity': severity, 'package_name': artifact.get('name'), 'package_type': artifact.get('type'), 'installed_version': artifact.get('version'), 'package_purl': artifact.get('purl'),
        'scanner_namespace': v.get('namespace'), 'scanner_data_source': v.get('dataSource'), 'fix_state': fix_state or 'unknown', 'fixed_versions': fixed_versions,
        'CISA_KEV_alias_matches': kev_hits, 'candidate_vendor_vex_statements_after_alias_reconciliation': candidate_vex,
        'applicable_vendor_vex_statements': applicable, 'final_disposition': disposition, 'rationale': rationale,
    })

summary['N8N_ACTIONABLE_GATE'] = 'PASS' if not any(summary[k] for k in blocking_keys) else 'FAIL'
summary['SELECTED_N8N_VERSION'] = selected_version
summary['SELECTED_N8N_DIGEST'] = release['selected_digest']
summary['OPENVEX_ASSET_SHA256_VERIFIED'] = True
json.dump(rows, open(ROOT/'n8n.vendor-openvex-reconciliation.json','w',encoding='utf-8'), indent=2, sort_keys=True)
json.dump(summary, open(ROOT/'n8n.vendor-openvex-summary.json','w',encoding='utf-8'), indent=2, sort_keys=True)
with open(ROOT/'gate.txt','w',encoding='utf-8') as f:
    f.write(summary['N8N_ACTIONABLE_GATE']+'\n')
for k, value in summary.items():
    print(f'{k}={value}')
