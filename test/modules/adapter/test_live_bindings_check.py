import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TARGET = pathlib.Path(__file__).with_name('live_bindings_check.py')
if '--target' in sys.argv:
    index = sys.argv.index('--target')
    TARGET = pathlib.Path(sys.argv[index + 1]).resolve()
    del sys.argv[index:index + 2]


def load():
    spec = importlib.util.spec_from_file_location('live_runner_under_test', TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Process:
    pid = 4321

    def __init__(self):
        self.closed = False

    def poll(self):
        return 0 if self.closed else None

    @property
    def returncode(self):
        return self.poll()

    def wait(self, timeout):
        if not self.closed:
            raise subprocess.TimeoutExpired('fake-game', timeout)
        return 0


class RunnerTests(unittest.TestCase):
    def scenario(self, mode):
        module = load()
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            exe = root / 'hoi4.exe'
            exe.write_bytes(b'fixture-exe')
            (root / 'hoi4_mod_plugin.dll').write_bytes(b'fixture-plugin')
            module.GAME = root
            module.FUNCTION_LOG = root / 'function.log'
            module.GAME_LOG = root / 'game.log'
            process = Process()
            if mode == 'settle_exit':
                process.wait = lambda timeout: 0
            launched, closes, commands = [], [], []
            if mode == 'stale_smoke':
                (root / 'out/smoke').mkdir(parents=True)

            def launch(*args, **kwargs):
                if mode == 'launch_error':
                    raise OSError('fixture launch failure')
                launched.append(args)
                sha = module.hashlib.sha256(exe.read_bytes()).hexdigest()
                if mode != 'identity':
                    module.FUNCTION_LOG.write_text('[t] [function:available] adapter.identity : ' + sha)
                return process

            def close(target, *args, **kwargs):
                closes.append(target)
                if mode == 'close_error':
                    raise OSError('fixture close failure')
                process.closed = mode != 'close_timeout'
                return process.closed

            def wait(*args, **kwargs):
                if mode == 'readiness_timeout':
                    return None
                if mode == 'early_exit':
                    process.closed = True
                    raise RuntimeError('game exited while waiting')
                if mode == 'interrupt':
                    raise KeyboardInterrupt()
                return 0.01

            def run(command, **kwargs):
                commands.append(command)
                if mode == 'helper_error':
                    raise OSError('fixture helper failure')
                if mode == 'command_timeout':
                    raise subprocess.TimeoutExpired(command, 60, output=b'partial', stderr=b'timeout detail')
                if '--report' in command:
                    if mode == 'smoke_timeout':
                        raise subprocess.TimeoutExpired(command, 600, output=b'partial smoke')
                    smoke = pathlib.Path(command[command.index('--report') + 1])
                    smoke.mkdir()
                    if mode == 'smoke_bad_json':
                        (smoke / 'comparison.json').write_text('{')
                    elif mode != 'smoke_missing':
                        checks = {'one': mode != 'smoke_false'}
                        if mode == 'smoke_empty':
                            checks = {}
                        if mode == 'smoke_not_bool':
                            checks = {'one': 1}
                        (smoke / 'comparison.json').write_text(json.dumps({'checks': checks}))
                    return subprocess.CompletedProcess(command, 1 if mode == 'smoke_exit' else 0, b'smoke', b'')
                return subprocess.CompletedProcess(command, 1 if mode == 'command_exit' else 0, b'result', b'fixture stderr')

            args = ['runner', '--exe', str(exe), '--output', str(root / 'out'), '--settle', '1' if mode == 'settle_exit' else '0']
            if mode.startswith('smoke') or mode in ('success', 'stale_smoke'):
                args.append('--smoke')
            with patch.object(sys, 'argv', args), patch.object(module, 'pids', side_effect=lambda name: [9999] if mode == 'existing' else ([4321] if launched and not process.closed else [])), \
                    patch.object(module, 'close', side_effect=close), patch.object(module, 'wait', side_effect=wait), \
                    patch.object(module.subprocess, 'Popen', side_effect=launch), patch.object(module.subprocess, 'run', side_effect=run), \
                    patch.object(module.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
                try:
                    result = module.main()
                except BaseException as error:
                    result = 'UNHANDLED:' + type(error).__name__
            path = root / 'out/live.json'
            report = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            return result, report, launched, closes, commands, process

    def test_success(self):
        code, report, launched, closes, commands, process = self.scenario('success')
        self.assertEqual(code, 0)
        self.assertTrue(report['accepted'])
        self.assertEqual(closes, [process])
        self.assertEqual(len(commands), 5)

    def test_failures_are_reported_and_nonzero(self):
        for mode in ('readiness_timeout', 'early_exit', 'launch_error', 'command_timeout', 'command_exit',
                     'smoke_exit', 'smoke_false', 'smoke_missing', 'smoke_bad_json', 'identity', 'close_timeout', 'interrupt'):
            with self.subTest(mode=mode):
                code, report, launched, closes, commands, process = self.scenario(mode)
                self.assertIsInstance(code, int)
                self.assertNotEqual(code, 0)
                self.assertFalse(report['accepted'])
                self.assertTrue(report['failure'])
                self.assertEqual(closes, [process] if launched else [])
                if mode == 'command_exit':
                    self.assertEqual(report['commands']['plugin_script_bindings']['stderr'], ['fixture stderr'])
                if mode == 'command_timeout':
                    self.assertEqual(report['commands']['plugin_script_bindings']['stderr'], ['timeout detail'])

    def test_more_failure_paths(self):
        for mode in ('settle_exit', 'helper_error', 'close_error', 'smoke_timeout', 'smoke_empty', 'smoke_not_bool', 'stale_smoke'):
            with self.subTest(mode=mode):
                code, report, launched, closes, commands, process = self.scenario(mode)
                self.assertIsInstance(code, int)
                self.assertNotEqual(code, 0)
                self.assertFalse(report['accepted'])
                self.assertTrue(report['failure'])
                if mode == 'stale_smoke':
                    self.assertEqual((launched, closes, commands), ([], [], []))

    def test_existing_game_is_untouched(self):
        code, report, launched, closes, commands, process = self.scenario('existing')
        self.assertNotEqual(code, 0)
        self.assertIn('EXISTING_GAME', report['failure'])
        self.assertEqual((launched, closes, commands), ([], [], []))

    def test_no_force_kill(self):
        source = TARGET.read_text(encoding='utf-8')
        self.assertNotIn('taskkill', source.lower())
        self.assertNotIn('.terminate(', source)
        self.assertNotIn('.kill(', source)

    def test_close_timeout_is_bounded(self):
        module = load()
        process = Process()
        with patch.object(module, 'request_close', return_value=True) as request:
            self.assertFalse(module.close(process, timeout=0.01))
        request.assert_called_once_with(process)
        self.assertIsNone(process.poll())

    def test_wait_timeout_and_exit(self):
        module = load()
        process = Process()
        self.assertIsNone(module.wait(lambda: False, 0, process))
        process.closed = True
        with self.assertRaises(RuntimeError):
            module.wait(lambda: True, 1, process)

    def test_invalid_deadlines(self):
        module = load()
        for value in ('0', '-1', 'nan', 'inf'):
            with self.subTest(value=value), self.assertRaises(module.argparse.ArgumentTypeError):
                module.positive(value)
        self.assertEqual(module.nonnegative('0'), 0)

    def test_process_scan_failure_is_not_empty(self):
        module = load()
        with patch.object(module.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'powershell')):
            with self.assertRaises(subprocess.CalledProcessError):
                module.pids('hoi4.exe')


if __name__ == '__main__':
    unittest.main()
