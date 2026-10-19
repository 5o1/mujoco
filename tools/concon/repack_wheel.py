#!/usr/bin/env python3
"""Package the locally built 3.16.0 engine with its official Python bindings.

This produces a Linux-specific local wheel, not an upstream or manylinux build.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile


def digest(data):
    return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-wheel', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    version = '3.16.0+concon.sdf3689.1'
    old_info = 'mujoco-3.16.0.dist-info'
    new_info = f'mujoco-{version}.dist-info'
    fields = args.official_wheel.name[:-4].split('-')
    if fields[:2] != ['mujoco', '3.16.0']:
        raise ValueError('Expected the official MuJoCo 3.16.0 wheel')
    tag = '-'.join([fields[-3], fields[-2], 'linux_x86_64'])
    binary = args.library.read_bytes()
    provenance = {
        'distribution_version': version,
        'native_api_version': '3.16.0',
        'source_repository': 'https://github.com/5o1/mujoco',
        'source_commit': commit,
        'upstream_release_commit': 'a892750516336d8358949f4518fcc4fbbd85beae',
        'upstream_pr': 'https://github.com/google-deepmind/mujoco/pull/3689',
        'upstream_patch_commit': '89733a51f207c7fedafc855d22ffd4c38caa793a',
        'library_sha256': hashlib.sha256(binary).hexdigest(),
        'official_wheel_sha256': hashlib.sha256(args.official_wheel.read_bytes()).hexdigest(),
        'packaging': 'Official CPython bindings and plugins, locally rebuilt ABI-compatible engine. Linux x86_64 only; no manylinux claim.',
    }
    entries = {}
    with zipfile.ZipFile(args.official_wheel) as wheel:
        for name in wheel.namelist():
            if name.endswith('/') or name == old_info + '/RECORD':
                continue
            data = wheel.read(name)
            name = name.replace(old_info + '/', new_info + '/', 1)
            if name == 'mujoco/libmujoco.so.3.16.0':
                data = binary
            elif name == new_info + '/METADATA':
                data = data.replace(b'Version: 3.16.0\n', f'Version: {version}\n'.encode(), 1)
            elif name == new_info + '/WHEEL':
                text = data.decode().splitlines()
                data = ('\n'.join(line for line in text if not line.startswith('Tag: ')) + f'\nTag: {tag}\n').encode()
            entries[name] = data
    entries['mujoco/CONCON_PATCH.json'] = (json.dumps(provenance, indent=2) + '\n').encode()
    record = io.StringIO(newline='')
    writer = csv.writer(record)
    for name, data in sorted(entries.items()):
        writer.writerow([name, digest(data), len(data)])
    writer.writerow([new_info + '/RECORD', '', ''])
    entries[new_info + '/RECORD'] = record.getvalue().encode()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / f'mujoco-{version}-{tag}.whl'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as wheel:
        for name, data in entries.items():
            wheel.writestr(name, data)
    print(target)


if __name__ == '__main__':
    main()
