"""Install checksum-pinned development tools for the rules proof lane."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-cache', type=Path, help='Optional read-only cache of archives; identities are still verified')
    args = parser.parse_args()
    system = platform.system().lower()
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'AMD64': 'x64'}.get(platform.machine())
    host = f'{system}-{arch}'
    pin = json.loads((ROOT / 'toolchain.json').read_text())
    if host not in pin['sha256']:
        raise ValueError('Proof compilation supports macOS/Linux x64/arm64; native CI consumes the emitted modules')
    tools = ROOT / '.tools'
    tools.mkdir(exist_ok=True)
    lean_host = system + ('_aarch64' if arch == 'arm64' else '')
    for name, url, expected in (
        (f'bend-{pin["bend"]}-{host}.tar.gz', f'https://github.com/bendlang/bend/releases/download/v{pin["bend"]}/bend-{pin["bend"]}-{host}.tar.gz', pin['sha256'][host]),
        (f'lean-{pin["lean"]["version"]}-{lean_host}.tar.zst', f'https://github.com/leanprover/lean4/releases/download/v{pin["lean"]["version"]}/lean-{pin["lean"]["version"]}-{lean_host}.tar.zst', pin['lean']['sha256'][host]),
    ):
        executable = tools / ('bend/bin/bend' if name.startswith('bend-') else f'lean-{pin["lean"]["version"]}-{lean_host}/bin/lean')
        marker = tools / (name + '.installed.json')
        if marker.is_file() and executable.is_file():
            installed = json.loads(marker.read_text())
            if installed == {'archiveSha256': expected, 'executableSha256': sha256(executable)}:
                print(f'Reused verified installation: {name}')
                continue
        archive = tools / name
        if not archive.is_file() and args.archive_cache and (args.archive_cache / name).is_file():
            shutil.copyfile(args.archive_cache / name, archive)
        if not archive.is_file():
            request = urllib.request.Request(url, headers={'User-Agent': 'inherent-design-rules-tools/1'})
            with urllib.request.urlopen(request, timeout=60) as source, archive.open('xb') as output:
                shutil.copyfileobj(source, output)
        if sha256(archive) != expected:
            raise ValueError(f'Pinned proof tool SHA-256 mismatch: {name}')
        subprocess.run(['tar', '-xf', str(archive), '-C', str(tools)], check=True)
        marker.write_text(json.dumps({'archiveSha256': expected, 'executableSha256': sha256(executable)}) + '\n')
        archive.unlink()
        print(f'Installed and SHA-256 verified: {name}')


if __name__ == '__main__':
    main()
