#!/usr/bin/env python3
"""Offline checks; never launch the game or contact a network service."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_linux_data as data

EXPANDER = ROOT / 'build/data-tools/ttt2_expand_lzx'

class DataPreparationTest(unittest.TestCase):
    @unittest.skipUnless(EXPANDER.is_file(), 'ttt2_expand_lzx not built')
    def test_lzx_container_expanded_in_place(self):
        payload = struct.pack('>I', 20) + b'ftypnrfi' + bytes(range(100))
        # One stored chunk: magic, version, hash, flags (u32 size table), size, 00 00, bytes.
        container = (bytes.fromhex('0ff512ed') + bytes(8) + struct.pack('>I', 1 << 22) +
                     struct.pack('>I', len(payload)) + b'\0\0' + payload)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'data100.bin').write_bytes(container)
            (directory / 'data100.ofs').write_bytes(b'index')
            self.assertEqual(data.expand_containers(directory, EXPANDER), 1)
            self.assertEqual((directory / 'data100.bin').read_bytes(), payload)
            self.assertEqual(data.expand_containers(directory, EXPANDER), 0)

    def test_hash_rejects_changed_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'file'
            path.write_bytes(b'original')
            expected = hashlib.sha256(b'original').hexdigest()
            data.verify(path, expected)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'damaged'):
                data.verify(path, expected)

    def test_existing_data_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'game'
            destination.mkdir()
            sentinel = destination / 'save'
            sentinel.write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                data.prepare(Path('absent.iso'), Path('absent.zip'), destination, Path('absent'), Path('absent'), Path('absent'))
            self.assertEqual(sentinel.read_bytes(), b'keep')

    def test_broken_symlink_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'game'
            destination.symlink_to('missing-target')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                data.prepare(Path('absent.iso'), Path('absent.zip'), destination, Path('absent'), Path('absent'), Path('absent'))
            self.assertTrue(destination.is_symlink())

    @unittest.skipUnless((ROOT / 'game/Default.xex').is_file(), 'requires locally prepared owner-supplied data')
    def test_tu3_constructor_and_vtable_coverage(self):
        path = ROOT / 'game/Default.xex'
        data.verify(path, data.UPDATED_SHA256)
        raw = path.read_bytes()
        image = raw[struct.unpack_from('>I', raw, 8)[0]:]
        config = tomllib.loads((ROOT / 'ttt2_config.toml').read_text())
        explicit = {int(address, 16) for address in config['functions']}
        # Regression for the first two actual native-startup aborts.
        self.assertIn(0x82D94A08, explicit)
        self.assertIn(0x8235E238, explicit)
        self.assertEqual(struct.unpack_from('>I', image, 0x35E238)[0], 0x98830037)
        self.assertEqual(struct.unpack_from('>I', image, 0x35E23C)[0], 0x4E800020)
        self.assertTrue((ROOT / 'game/default.xex').samefile(path))
        self.assertGreater((ROOT / 'game/update/data100.bin').stat().st_size, 0)
        self.assertGreater((ROOT / 'game/update/data100.ofs').stat().st_size, 0)

    def test_parser_callback_coverage(self):
        # The parser installs this callback indirectly; it must be an explicit
        # codegen entry even when the conservative address scan misses it.
        config = tomllib.loads((ROOT / 'ttt2_config.toml').read_text())
        self.assertIn('0x82C77940', config['functions'], 'Missing parser callback hint')
        self.assertEqual(config['functions']['0x82C77940']['name'], 'sub_82C77940')
        generated = ROOT / 'generated/default/ttt2_init.cpp'
        if generated.is_file():
            self.assertIn('{ 0x82C77940, sub_82C77940 }', generated.read_text())

    @unittest.skipUnless((ROOT / 'generated/default/ttt2_init.cpp').is_file(), 'requires local codegen')
    def test_overlap_branch_uses_emitting_function(self):
        # Before the TTT2 SDK repair this emitted REX_FATAL even though the
        # target label was present in sub_82C22FD0's own body.
        bodies = [path.read_text() for path in (ROOT / 'generated/default').glob('ttt2_recomp.*.cpp')]
        body = next(text for text in bodies if 'DEFINE_REX_FUNC(sub_82C22FD0)' in text)
        self.assertNotIn('Unresolved branch from 0x82C23084 to 0x82C23068', body)
        self.assertIn('if (!ctx.cr6.lt) goto loc_82C23068;', body)
        for text in bodies:
            self.assertFalse('Unresolved branch from' in text, 'Codegen emitted an unresolved branch')
            self.assertFalse('Unresolved call from' in text, 'Codegen emitted an unresolved call')

if __name__ == '__main__':
    unittest.main()
