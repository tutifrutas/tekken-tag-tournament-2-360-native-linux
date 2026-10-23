#!/usr/bin/env python3
"""Fetch pinned build sources and check the shared native RexGlue SDK."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ('tools/XenonRecomp', 'https://github.com/hedge-dev/XenonRecomp.git', 'ddd128bcca99fe8bfbb99bea583c972351fa6ace'),
)

def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)

def main() -> int:
    for relative, url, revision in SOURCES:
        path = ROOT / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            run('git', 'clone', '--no-checkout', url, str(path))
            run('git', '-C', str(path), 'checkout', '--detach', revision)
        actual = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != revision:
            raise ValueError(f'{relative}: expected {revision}, found {actual}; existing checkout was not changed')
        run('git', '-C', str(path), 'submodule', 'update', '--init', '--recursive')
    sdk = ROOT.parent / 'rexglue-sdk'
    if not (sdk / 'CMakeLists.txt').is_file():
        raise ValueError(f'Shared SDK not found at {sdk}; run: git clone '
                         f'--recurse-submodules https://github.com/tutifrutas/rexglue-sdk.git {sdk}')
    run('git', '-C', str(sdk), 'submodule', 'update', '--init', '--recursive')
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Bootstrap failed: {error}', file=sys.stderr)
        raise SystemExit(1)
