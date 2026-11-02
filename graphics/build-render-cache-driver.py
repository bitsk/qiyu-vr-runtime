#!/usr/bin/env python3
"""Build opt-in A081 SteamVR rendering workarounds; never deploys."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'build/steamos-turnip-split-kms-r1'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--query-wait', action='store_true',
               help='Include the optional bounded query-poll sleep experiment')
p.add_argument('--three-images', action='store_true',
               help='Include an opt-in three-image minimum for display swapchains')
a = p.parse_args()
out = a.output.resolve()
assert out.is_relative_to(ROOT / 'build') and not out.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parent = json.loads((BASE / 'build-manifest.json').read_text())
assert parent['driver_sha256'] == '0b4757728abda8b4b501f8e06824dfc249aa7bfa7f0b1709967c137d0d1ab7d7'
assert sha(BASE / 'bundle/opt/mix-steamvr-turnip/lib/libvulkan_freedreno.so') == parent['driver_sha256']
source = out / 'source'
shutil.copytree(BASE / 'source', source, ignore=shutil.ignore_patterns('.git'))
patch = ROOT / 'steamos-mix/turnip-depth-cache.patch'
for extra in (['--dry-run'], []):
    subprocess.run(['patch', *extra, '-p1', '-i', str(patch)], cwd=source, check=True)
extra_patches = []
for enabled, name in ((a.query_wait, 'turnip-query-wait.patch'),
                      (a.three_images, 'turnip-display-images.patch')):
    if not enabled:
        continue
    query_patch = ROOT / 'steamos-mix' / name
    for extra in (['--dry-run'], []):
        subprocess.run(['patch', *extra, '-p1', '-i', str(query_patch)],
                       cwd=source, check=True)
    shutil.copy2(query_patch, out / query_patch.name)
    extra_patches.append({'file': query_patch.name, 'sha256': sha(query_patch)})
configure = list(parent['reproduction']['configure'])
configure[2:4] = [str(out / 'compile'), str(source)]
commands = [configure, ['/usr/bin/ninja', '-C', str(out / 'compile'), '-j12',
                       'src/freedreno/vulkan/libvulkan_freedreno.so']]
env = dict(os.environ)
env['PATH'] = parent['reproduction']['environment']['PATH']
for name, command in zip(('configure.log', 'build.log'), commands):
    with (out / name).open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
lib = out / 'libvulkan_freedreno.so'
shutil.copy2(out / 'compile/src/freedreno/vulkan/libvulkan_freedreno.so', lib)
shutil.copy2(patch, out / patch.name)
shutil.copy2(source / 'docs/license.rst', out / 'Mesa-license.rst')
manifest = dict(parent_driver_sha256=parent['driver_sha256'],
    source_commit=parent['source_commit'], parent_patch_sha256=parent['patch_sha256'],
    patch_sha256=sha(patch), driver_sha256=sha(lib), commands=commands,
    opt_in={'TU_DEBUG': 'a081-ccu-depth'}, default_behavior_changed=False,
    scope='Depth CCU clean and invalidate at existing flush boundaries. Rendering workaround; missing transition not yet isolated.',
    tracking_and_controllers_changed=False, device_tested=False)
if extra_patches:
    manifest['additional_patches'] = extra_patches
if a.query_wait:
    manifest['query_wait'] = {'environment': 'TU_A081_QUERY_SLEEP_US',
        'default_us': 0, 'maximum_us': 1000, 'candidate_us': 20,
        'availability_check_and_timeout_preserved': True,
        'acceptance': 'Requires device comparison; not accepted by building'}
if a.three_images:
    manifest['display_images'] = {'environment': 'TU_A081_THREE_IMAGES',
        'default': False, 'minimum_when_enabled': 3,
        'acceptance': 'Requires frame cadence, queue latency, and visual comparison'}
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
