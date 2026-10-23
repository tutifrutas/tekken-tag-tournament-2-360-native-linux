#!/usr/bin/env python3
"""Prepare TTT2 TU3 data from the owner's ISO and title-update ZIP, without Wine."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
from stfs import STFS
from expand_archives import LZX_MAGIC, expected_sizes

BASE_SHA256 = 'e74e57de3e205517e5447cacdba68624544fbd313ddb8c5f174b8e3ff43283d8'
PATCH_SHA256 = 'c413fdfb2ba547e93fd16fa571c047f9914c5194526ddfa37c481ac84376f0e9'
UPDATED_SHA256 = '5ab29622d2dfb123dca5894e5a9d7f21dc88bb52367056830edd09dfaf162146'
TU_NAME = 'TU_174Q22P_0000008000000.00000000000O2'
TU_SHA256 = '61a98cfee1894cfbe0fcd5890e0fae919ac8730fe1686b56d6a0b4216bae71e7'

def verify(path: Path, expected: str) -> None:
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f'Unsupported or damaged game/update file: {path.name}')

def run(*args: str | Path) -> None:
    subprocess.run([str(arg) for arg in args], check=True)

def expand_containers(directory: Path, expander: Path) -> int:
    """Expand LZX containers in place. On the console the kernel does this transparently
    (XCTD); the game addresses every archive, and update:\\data100.bin, in expanded form."""
    archives = sorted(p.name for p in directory.glob('data*.bin') if p.name != 'data100.bin')
    sizes = expected_sizes(str(directory / 'nrfo.bin'), archives) if archives else {}
    expanded = 0
    for path in sorted(directory.glob('data*.bin')):
        with path.open('rb') as stream:
            if stream.read(4) not in (LZX_MAGIC, b'\x0f\xf5\x12\xee'):
                continue
        want = sizes.get(path.name)
        if path.name != 'data100.bin' and not want:
            raise ValueError(f'nrfo.bin has no expanded size for {path.name}')
        part = path.with_name(path.name + '.part')
        run(expander, path, part, *([str(want)] if want else []))
        if want and part.stat().st_size != want:
            part.unlink()
            raise ValueError(f'{path.name} expanded to the wrong size')
        part.replace(path)
        expanded += 1
    return expanded

def prepare(iso: Path, update: Path, destination: Path, extractor: Path, patcher: Path,
            expander: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise ValueError(f'Destination already exists; it was not modified: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ttt2-data-', dir=destination.parent) as temporary:
        work = Path(temporary)
        listing = work / 'files.txt'
        run(extractor, 'list', iso, listing)
        files = [line.split('\t', 1)[1] for line in listing.read_text().splitlines() if '\t' in line]
        xex = [name for name in files if name.lower() == 'default.xex']
        if len(xex) != 1:
            raise ValueError('Expected exactly one root Default.xex in the ISO')
        base = work / 'base.xex'
        run(extractor, 'extract', iso, xex[0], base)
        verify(base, BASE_SHA256)
        with zipfile.ZipFile(update) as archive:
            members = [info for info in archive.infolist() if info.filename == TU_NAME]
            if len(members) != 1 or members[0].file_size != 3153920:
                raise ValueError('Expected the TTT2 TU3 package in the ZIP')
            package = work / TU_NAME
            package.write_bytes(archive.read(members[0]))
        verify(package, TU_SHA256)
        stfs = STFS(package)
        try:
            if stfs.title_id != 0x4E4D0859 or stfs.media_id != 0x5D762D06:
                raise ValueError('Title update does not match TTT2 USA/Europe')
            entries = stfs.read_file_table()
            payload = {}
            for entry in entries:
                if entry['is_dir'] or entry['name'] not in {'Default.xexp', 'data100.bin', 'data100.ofs'}:
                    raise ValueError('Unexpected TU3 payload entry')
                if entry['name'] in payload:
                    raise ValueError('Duplicate TU3 payload entry')
                payload[entry['name']] = stfs.read_file(entry)
            if set(payload) != {'Default.xexp', 'data100.bin', 'data100.ofs'}:
                raise ValueError('Incomplete TU3 payload')
        finally:
            stfs.f.close()
        patch = work / 'Default.xexp'
        patch.write_bytes(payload.pop('Default.xexp'))
        verify(patch, PATCH_SHA256)
        stage = work / 'game'
        stage.mkdir()
        run(patcher, base, patch, stage / 'Default.xex')
        verify(stage / 'Default.xex', UPDATED_SHA256)
        # Extract only game assets, not the dashboard/system-update executables.
        assets = [name for name in files if re.fullmatch(r'data\d+\.(bin|ofs)', name, re.I) or name.lower() == 'nrfo.bin']
        if not assets:
            raise ValueError('The ISO has no game archives')
        for name in assets:
            run(extractor, 'extract', iso, name, stage / name)
        # TU3's archive and index form the separate update: device, never the disc root.
        (stage / 'update').mkdir()
        for name, data in payload.items():
            (stage / 'update' / name).write_bytes(data)
        expand_containers(stage, expander)
        expand_containers(stage / 'update', expander)
        # The SDK requests game:\\default.xex; Linux filenames are case-sensitive.
        (stage / 'default.xex').symlink_to('Default.xex')
        if destination.exists() or destination.is_symlink():
            raise ValueError('Destination appeared during extraction; refusing to replace it')
        stage.rename(destination)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path)
    parser.add_argument('--tu3', type=Path)
    parser.add_argument('--expand', type=Path, metavar='GAME_DIR',
                        help='only expand LZX archives in an already prepared game directory')
    parser.add_argument('--expander', type=Path, default=ROOT / 'build/data-tools/ttt2_expand_lzx')
    parser.add_argument('--output', type=Path, default=ROOT / 'game')
    parser.add_argument('--extractor', type=Path, default=ROOT / 'build/data-tools/xdvdfs/xdvdfs_tool')
    parser.add_argument('--patcher', type=Path, default=ROOT / 'build/data-tools/ttt2_patch_xex')
    args = parser.parse_args()
    if not args.expand and not (args.iso and args.tu3):
        parser.error('--iso and --tu3 are required unless --expand is given')
    try:
        if args.expand:
            game = args.expand.resolve()
            count = sum(expand_containers(directory, args.expander.resolve())
                        for directory in (game, game / 'update') if directory.is_dir())
            print(f'Expanded {count} LZX archives in {args.expand}')
            return 0
        prepare(*(p.resolve() for p in (args.iso, args.tu3, args.output, args.extractor,
                                         args.patcher, args.expander)))
    except (ValueError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f'Data preparation failed: {error}', file=sys.stderr)
        return 1
    print(f'Prepared TTT2 TU3 game data: {args.output}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
