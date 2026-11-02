#!/usr/bin/env python3
"""Package an existing Turnip bundle without host ownership or root-directory entries."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import stat
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = Path('opt/mix-steamvr-turnip')


def digest(path):
    with path.open('rb') as stream:
        return stream_digest(stream)


def stream_digest(stream):
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True, help='Existing bundle containing opt/mix-steamvr-turnip')
    parser.add_argument('--output', type=Path, required=True, help='New directory inside this checkout/build')
    args = parser.parse_args()
    bundle, output = args.bundle.resolve(), args.output.resolve()
    if not output.is_relative_to(ROOT / 'build') or output == ROOT / 'build' or output.exists():
        parser.error('--output must be a new directory inside this checkout/build')
    source = bundle / PREFIX
    if not source.is_dir() or (bundle / 'opt').is_symlink() or source.is_symlink():
        parser.error('--bundle must contain a real opt/mix-steamvr-turnip directory')
    paths = [source, *sorted(source.rglob('*'))]
    files = {}
    for path in paths:
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            parser.error('Only regular files and directories may be packaged: ' + str(path))
        if stat.S_ISREG(mode):
            files[str(path.relative_to(bundle))] = digest(path)
    for required in ('lib/libvulkan_freedreno.so', 'share/vulkan/icd.d/freedreno_icd.aarch64.json'):
        if str(PREFIX / required) not in files:
            parser.error('Missing Turnip payload: ' + required)
    output.mkdir(parents=True)
    archive = output / 'a081-turnip-split-kms-arm64.tar.gz'
    with archive.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as tar:
                for path in paths:
                    info = tar.gettarinfo(str(path), arcname=str(path.relative_to(bundle)))
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = 'root'
                    info.mode = 0o755 if info.isdir() or info.mode & 0o111 else 0o644
                    if info.isfile():
                        with path.open('rb') as stream:
                            tar.addfile(info, stream)
                    else:
                        tar.addfile(info)
    with tarfile.open(archive) as tar:
        for member in tar:
            if member.isfile():
                with tar.extractfile(member) as stream:
                    if stream_digest(stream) != files[member.name]:
                        raise RuntimeError('Payload changed during packaging: ' + member.name)
    manifest = {'prefix': '/' + str(PREFIX), 'source_bundle': str(bundle),
                'files_sha256': files, 'package_script_sha256': digest(Path(__file__)),
                'archive_sha256': digest(archive), 'archive_bytes': archive.stat().st_size,
                'ownership': 'root:root; directories/executables 0755; other files 0644',
                'excluded_parent_entries': ['.', 'opt', 'SHA256SUMS'],
                'scope': 'Packaging only; no rebuild, installation, or device validation'}
    (output / 'package-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text(''.join(
        f'{digest(path)}  {path.name}\n' for path in (archive, output / 'package-manifest.json')))
    print(json.dumps({'archive': str(archive), 'sha256': manifest['archive_sha256'],
                      'bytes': manifest['archive_bytes']}, indent=2))


if __name__ == '__main__':
    main()
