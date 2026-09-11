#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: n8n_prune_closure.py <compiled-node-modules> <evidence-dir>")

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)


def instances():
    rows = []
    for pattern in ('.pnpm/*/node_modules/*/package.json', '.pnpm/*/node_modules/@*/*/package.json'):
        for manifest in root.glob(pattern):
            try:
                metadata = json.loads(manifest.read_text())
            except Exception:
                continue
            real_dir = manifest.parent.resolve()
            pnpm_root = (root / '.pnpm').resolve()
            store_candidates = [p.resolve() for p in real_dir.parents if p.parent.resolve() == pnpm_root]
            if len(store_candidates) != 1:
                raise SystemExit(f'unexpected resolved pnpm store candidates: dir={real_dir} candidates={store_candidates}')
            real_store = store_candidates[0]
            if real_store.parent.resolve() != pnpm_root:
                raise SystemExit(f'unexpected resolved pnpm store layout: dir={real_dir} store={real_store}')
            rows.append({
                'name': metadata.get('name'),
                'version': metadata.get('version'),
                'manifest': str(manifest),
                'dir': str(real_dir),
                'store': str(real_store),
            })
    unique = {row['dir']: row for row in rows if row['name'] and row['version']}
    return sorted(unique.values(), key=lambda row: (row['name'], row['version'], row['dir']))


before = instances()
json.dump(before, open(out / 'inventory.before.json', 'w'), indent=2, sort_keys=True)
bykey = {}
for row in before:
    bykey.setdefault((row['name'], row['version']), []).append(row)

snow = bykey.get(('snowflake-sdk', '2.1.0'), [])
toml = bykey.get(('toml', '3.0.0'), [])
n8n_base = bykey.get(('n8n-nodes-base', '2.37.10'), [])
if len(snow) != 1 or len(toml) != 1:
    raise SystemExit(f'exact target multiplicity failed: snow={len(snow)} toml={len(toml)}')
if len(n8n_base) != 1:
    raise SystemExit(f'exact n8n-nodes-base@2.37.10 multiplicity failed: {len(n8n_base)}')

why_snow = json.load(open(out / 'pnpm-why-prod-snowflake-sdk.json'))
why_toml = json.load(open(out / 'pnpm-why-prod-toml.json'))
if len(why_snow) != 1 or why_snow[0].get('name') != 'snowflake-sdk' or why_snow[0].get('version') != '2.1.0':
    raise SystemExit(f'unexpected snowflake pnpm why root: {why_snow}')
snow_parents = sorted(f"{d.get('name')}@{d.get('version')}" for d in (why_snow[0].get('dependents') or []))
if snow_parents != ['n8n-nodes-base@2.37.10']:
    raise SystemExit(f'unexpected snowflake production parents: {snow_parents}')
if len(why_toml) != 1 or why_toml[0].get('name') != 'toml' or why_toml[0].get('version') != '3.0.0':
    raise SystemExit(f'unexpected toml pnpm why root: {why_toml}')
toml_dependents = why_toml[0].get('dependents') or []
toml_parents = sorted(f"{d.get('name')}@{d.get('version')}" for d in toml_dependents)
if toml_parents != ['snowflake-sdk@2.1.0']:
    raise SystemExit(f'unexpected toml production parents: {toml_parents}')
nested = toml_dependents[0].get('dependents') or []
nested_ids = sorted(f"{d.get('name')}@{d.get('version')}" for d in nested)
if nested_ids != ['n8n-nodes-base@2.37.10']:
    raise SystemExit(f'unexpected transitive Snowflake chain: {nested_ids}')

targets = {
    Path(snow[0]['dir']).resolve(): 'snowflake-sdk@2.1.0',
    Path(toml[0]['dir']).resolve(): 'toml@3.0.0',
}
links = []
for base, dirs, files in os.walk(root, followlinks=False):
    for name in list(dirs) + list(files):
        path = Path(base) / name
        if not path.is_symlink():
            continue
        try:
            target = path.resolve(strict=True)
        except FileNotFoundError:
            continue
        if target in targets:
            links.append({'link': str(path), 'target': str(target), 'package': targets[target]})

linked_packages = sorted({row['package'] for row in links})
if linked_packages != ['snowflake-sdk@2.1.0', 'toml@3.0.0']:
    raise SystemExit(f'target filesystem links incomplete: {linked_packages}')

parent_map = {
    'parents': {'snowflake-sdk@2.1.0': snow_parents, 'toml@3.0.0': toml_parents},
    'transitive_chain': {'toml@3.0.0': ['snowflake-sdk@2.1.0', 'n8n-nodes-base@2.37.10']},
    'pnpm_why_snowflake': why_snow,
    'pnpm_why_toml': why_toml,
    'filesystem_links': links,
    'authorized_removed_packages': ['snowflake-sdk@2.1.0', 'toml@3.0.0'],
    'shared_parent_analysis': {'snowflake_sdk_external_parents': [], 'toml_external_parents': []},
}
json.dump(parent_map, open(out / 'parent-map.json', 'w'), indent=2, sort_keys=True)

for row in links:
    path = Path(row['link'])
    if path.is_symlink():
        path.unlink()

n8n_store = Path(n8n_base[0]['store']).resolve()
authorized = {'snowflake-sdk@2.1.0', 'toml@3.0.0'}
delete_targets = []
for row in (snow[0], toml[0]):
    pkg_dir = Path(row['dir']).resolve()
    store = Path(row['store']).resolve()
    metadata = json.loads((pkg_dir / 'package.json').read_text())
    ident = f"{metadata.get('name')}@{metadata.get('version')}"
    if ident not in authorized:
        raise SystemExit(f'unauthorized resolved delete identity: {ident}')
    expected_store = pkg_dir.parents[1].resolve()
    if store != expected_store or store.parent.resolve() != (root / '.pnpm').resolve():
        raise SystemExit(f'resolved delete store mismatch for {ident}: store={store} expected={expected_store}')
    if store == n8n_store or n8n_store in store.parents:
        raise SystemExit(f'delete target overlaps n8n-nodes-base store: {ident}')
    delete_targets.append({'package': ident, 'dir': str(pkg_dir), 'store': str(store)})

if {row['package'] for row in delete_targets} != authorized or len({row['store'] for row in delete_targets}) != 2:
    raise SystemExit(f'expected delete-target set mismatch: {delete_targets}')
json.dump(delete_targets, open(out / 'delete-targets.json', 'w'), indent=2, sort_keys=True)

for row in delete_targets:
    store = Path(row['store'])
    if not store.exists():
        raise SystemExit(f'resolved delete store missing before prune: {store}')
    shutil.rmtree(store)

after = instances()
json.dump(after, open(out / 'inventory.after.json', 'w'), indent=2, sort_keys=True)
before_pairs = {(row['name'], row['version']) for row in before}
after_pairs = {(row['name'], row['version']) for row in after}
removed = sorted(f'{name}@{version}' for name, version in before_pairs - after_pairs)
added = sorted(f'{name}@{version}' for name, version in after_pairs - before_pairs)
authorized_removed = ['snowflake-sdk@2.1.0', 'toml@3.0.0']
shared_non_snowflake_removed = sorted(item for item in removed if item not in authorized_removed)
before_versions = {}
after_versions = {}
for name, version in before_pairs:
    before_versions.setdefault(name, set()).add(version)
for name, version in after_pairs:
    after_versions.setdefault(name, set()).add(version)
version_changes = []
for name in sorted(set(before_versions) & set(after_versions)):
    if before_versions[name] != after_versions[name]:
        version_changes.append({'name': name, 'before': sorted(before_versions[name]), 'after': sorted(after_versions[name])})

delta = {
    'removed': removed,
    'added': added,
    'version_changes': version_changes,
    'shared_non_snowflake_removed': shared_non_snowflake_removed,
}
json.dump(delta, open(out / 'package-delta.json', 'w'), indent=2, sort_keys=True)
print(json.dumps(delta, indent=2, sort_keys=True))
if removed != authorized_removed or added or version_changes or shared_non_snowflake_removed:
    raise SystemExit(f'unexpected prune delta: {delta}')
if len([row for row in after if row['name'] == 'n8n-nodes-base' and row['version'] == '2.37.10']) != 1:
    raise SystemExit('n8n-nodes-base@2.37.10 not preserved exactly once')
if any(row['name'] == 'snowflake-sdk' for row in after):
    raise SystemExit('snowflake-sdk remains')
if any(row['name'] == 'toml' and row['version'] == '3.0.0' for row in after):
    raise SystemExit('toml@3.0.0 remains')
