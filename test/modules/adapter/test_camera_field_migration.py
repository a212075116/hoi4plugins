import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'test/tools'), str(ROOT / 'test/modules/camera')]
TARGET = ROOT / 'test/tools/migrate_image.py'
if '--target' in sys.argv:
    index = sys.argv.index('--target')
    TARGET = pathlib.Path(sys.argv[index + 1]).resolve()
    del sys.argv[index:index + 2]
BASE_SHA = '7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5'
NEW_SHA = 'a' * 64


def load():
    spec = importlib.util.spec_from_file_location('camera_migration_under_test', TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MigrationTests(unittest.TestCase):
    def scenario(self, reviewed=None, status='MOVED', getter=True, same=False):
        module = load()
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / 'bindings').mkdir()
            (root / 'bindings' / (BASE_SHA + '.profile')).write_bytes((ROOT / 'bindings' / (BASE_SHA + '.profile')).read_bytes())
            output = root / 'out'
            sha = BASE_SHA if same else NEW_SHA
            original = module.read_profile(ROOT / 'bindings' / (BASE_SHA + '.symbols'))
            rows = [dict(key=field, status=status, votes={hex(int(original['field.' + field], 0) + 8): 3})
                    for field in module.CAMERA_FIELDS.values()]
            requested = []

            class Bindings:
                tables = {'CInGameIdler': 1234}

                def __init__(self, path):
                    pass

                def find_getter(self, field):
                    requested.append(field)
                    if not getter:
                        raise module.AdapterError('GETTER_NOT_FOUND', 'fixture missing getter')
                    return {'slot': 36}

            def symbols(base, target, same_image, destination):
                ordered = dict(original)
                ordered['image_sha256'] = sha
                if not same_image:
                    ordered.update({key: '0' for key in ordered if key.startswith('approve.')})
                path = destination / (sha + '.symbols')
                path.write_text(''.join(k + '=' + v + '\n' for k, v in ordered.items()), encoding='ascii')
                return dict(ordered=ordered, profile=str(path), fields=[], groups=['camera_write'],
                            symbol_failures=[], incomplete_groups=[], summary={})

            def registry(base, target, same_image, destination):
                path = destination / (sha + '.registry')
                path.write_text('runtime_registration=' + ('1' if same_image else '0') + '\n')
                return dict(profile=str(path), summary={}, complete=True, static_token_count=1)

            args = ['migrate', '--image', str(root / 'target.exe'), '--baseline-image', str(root / 'base.exe'),
                    '--output-directory', str(output)]
            if reviewed is not None:
                review = root / 'review.txt'
                review.write_text(reviewed, encoding='ascii')
                args += ['--review', str(review)]
            with patch.object(sys, 'argv', args), patch.object(module, 'ROOT', root), \
                    patch.object(module, 'Image', side_effect=[types.SimpleNamespace(sha=BASE_SHA), types.SimpleNamespace(sha=sha)]), \
                    patch.object(module, 'migrate_symbols', side_effect=symbols), patch.object(module, 'migrate_registry', side_effect=registry), \
                    patch.object(module, 'field_report', return_value={'fields': rows}), patch.object(module, 'brief', return_value={}), \
                    patch.object(module, 'ImageBindings', Bindings), contextlib.redirect_stdout(io.StringIO()):
                module.main()
            symbols_out = module.read_profile(output / (sha + '.symbols'))
            camera_out = module.read_profile(output / (sha + '.profile'))
            report = json.loads((output / 'migration.json').read_text())
            return symbols_out, camera_out, report, requested

    def assert_consistent(self, symbols, camera):
        for name, field in load().CAMERA_FIELDS.items():
            self.assertEqual(int(symbols['field.' + field], 0), int(camera[name], 0), name)

    def test_review_overrides_witness_for_both_profiles(self):
        review = '\n'.join('field.' + field + '=' + hex(value) + ' # independently reviewed'
                           for field, value in zip(load().CAMERA_FIELDS.values(), (0x728, 0x688, 0x6a0, 0x6a4)))
        symbols, camera, report, requested = self.scenario(review)
        self.assert_consistent(symbols, camera)
        self.assertEqual(requested, [0x728])
        self.assertEqual(set(report['camera']['origin'].values()), {'REVIEWED'})
        self.assertEqual(camera['runtime_read'], '0')
        self.assertTrue(all(v == '0' for k, v in symbols.items() if k.startswith('approve.')))

    def test_unanimous_fields(self):
        symbols, camera, report, requested = self.scenario()
        self.assert_consistent(symbols, camera)
        self.assertEqual(requested, [int(camera['camera_pointer'], 0)])
        self.assertTrue(report['camera']['located'])

    def test_no_unanimous_evidence_does_not_carry_old_offsets(self):
        for status in ('NO_WITNESS', 'MOSTLY_SAME', 'SPLIT'):
            with self.subTest(status=status):
                symbols, camera, report, requested = self.scenario(status=status)
                self.assert_consistent(symbols, camera)
                self.assertTrue(all(int(camera[k], 0) == 0 for k in load().CAMERA_KEYS))
                self.assertFalse(report['camera']['located'])
                self.assertEqual(camera['runtime_read'], '0')
                self.assertEqual(requested, [])

    def test_review_can_supply_missing_evidence(self):
        review = '\n'.join('field.' + field + '=0x100 # explicit review' for field in load().CAMERA_FIELDS.values())
        symbols, camera, report, requested = self.scenario(review, status='NO_WITNESS')
        self.assert_consistent(symbols, camera)
        self.assertTrue(report['camera']['located'])

    def test_partial_review_keeps_remaining_fields_unresolved(self):
        symbols, camera, report, requested = self.scenario('field.camera.height=0x100 # partial review', status='NO_WITNESS')
        self.assert_consistent(symbols, camera)
        self.assertEqual(int(camera['height'], 0), 0x100)
        self.assertEqual(int(camera['maximum'], 0), 0)
        self.assertFalse(report['camera']['located'])
        self.assertEqual(requested, [])

    def test_explicit_zero_disables_candidate(self):
        symbols, camera, report, requested = self.scenario('field.camera.height=0 # explicitly disable')
        self.assert_consistent(symbols, camera)
        self.assertFalse(report['camera']['located'])
        self.assertEqual(camera['runtime_read'], '0')
        self.assertEqual(requested, [])

    def test_getter_failure_preserves_consistent_disabled_candidates(self):
        for same in (False, True):
            with self.subTest(same=same):
                symbols, camera, report, requested = self.scenario(getter=False, same=same)
                self.assert_consistent(symbols, camera)
                self.assertFalse(report['camera']['located'])
                self.assertFalse(report['camera']['approved'])
                self.assertEqual(camera['runtime_read'], '0')

    def test_same_image_preserves_profile_bytes(self):
        symbols, camera, report, requested = self.scenario(same=True)
        self.assert_consistent(symbols, camera)
        self.assertEqual(camera, load().read_profile(ROOT / 'bindings' / (BASE_SHA + '.profile')))

    def test_partial_review_cannot_hide_unknown_fields(self):
        with self.assertRaises(SystemExit):
            self.scenario('field.camera.typo=0x100 # typo')

    def test_invalid_review_offsets(self):
        for value in ('-1', '0x10000'):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                self.scenario('field.camera.height=' + value + ' # invalid')

    def test_same_image_review_is_not_silently_ignored(self):
        with self.assertRaises(SystemExit):
            self.scenario('field.camera.height=0x100 # request review', same=True)

    def test_review_cannot_approve_profiles(self):
        for key in ('approve.camera_write', 'runtime_read'):
            with self.subTest(key=key), self.assertRaises(SystemExit):
                self.scenario(key + '=1 # cannot authorize')


if __name__ == '__main__':
    unittest.main()
