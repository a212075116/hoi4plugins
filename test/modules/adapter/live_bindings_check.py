"""Launch one game image with the deployed plugin, wait for the map, record function states and read-only commands."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import time

GAME = pathlib.Path(__file__).resolve().parents[4]
FUNCTION_LOG = GAME / 'hoi4plugin_function_log.log'
GAME_LOG = pathlib.Path.home() / 'Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
IN_GAME = 'Launching SINGLEPLAYER-game'
COMMANDS = ['plugin_script_bindings', 'plugin_camera_read', 'achievementstatus', 'achievementsource']


def pids(name):
    stem = name[:-4] if name.lower().endswith('.exe') else name
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          '[Console]::OutputEncoding=[Text.Encoding]::UTF8; '
                          '(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq $env:LIVE_STEM }).Id'],
                         capture_output=True, text=True, encoding='utf-8', timeout=60, check=True,
                         env=dict(__import__('os').environ, LIVE_STEM=stem)).stdout
    return [int(x) for x in out.split()]


def request_close(process):
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    sent = False

    @callback_type
    def visit(window, unused):
        nonlocal sent
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
        if pid.value == process.pid and process.poll() is None:
            sent = bool(user32.PostMessageW(window, 0x0010, 0, 0)) or sent
        return True

    if not user32.EnumWindows(visit, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return sent


def close(process, timeout=60):
    if process.poll() is not None:
        return True
    request_close(process)
    try:
        process.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        return False


def text(path):
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def wait(condition, timeout, process):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if process.poll() is not None:
            raise RuntimeError('game exited while waiting: ' + str(process.returncode))
        if condition():
            return time.monotonic() - start
        time.sleep(min(1, max(0, timeout - (time.monotonic() - start))))
    return None


def output_lines(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8', 'replace')
    return (value or '').splitlines()[-30:]


def run_command(command, timeout):
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout)
        return dict(exit=result.returncode, stdout=output_lines(result.stdout), stderr=output_lines(result.stderr))
    except subprocess.TimeoutExpired as error:
        return dict(exit=None, timeout=timeout, stdout=output_lines(error.stdout), stderr=output_lines(error.stderr))


def positive(value):
    import math
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('must be finite and positive')
    return number


def nonnegative(value):
    if value == '0':
        return 0.0
    return positive(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--start-tag', default='CHI')
    parser.add_argument('--settle', type=nonnegative, default=30.0)
    parser.add_argument('--ready-timeout', type=positive, default=400.0)
    parser.add_argument('--close-timeout', type=positive, default=60.0)
    parser.add_argument('--smoke', action='store_true', help='run test/tools/run_normalization_smoke.py before closing')
    parser.add_argument('--smoke-skip', action='append', default=[])
    parser.add_argument('--extra-command', action='append', default=[], help='additional console line, may change the unsaved session')
    args = parser.parse_args()
    exe = args.exe.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    report = dict(exe=str(exe), accepted=False, failures=[], commands={})
    process = None
    try:
        existing = sorted({pid for name in {'hoi4.exe', exe.name} for pid in pids(name)})
        if existing:
            raise RuntimeError('EXISTING_GAME: close it manually before testing: ' + str(existing))
        if args.smoke and (args.output / 'smoke').exists():
            raise RuntimeError('EXISTING_SMOKE_OUTPUT: choose a fresh output directory')
        report['sha256'] = hashlib.sha256(exe.read_bytes()).hexdigest()
        report['plugin_sha256'] = hashlib.sha256((GAME / 'hoi4_mod_plugin.dll').read_bytes()).hexdigest()
        if FUNCTION_LOG.exists():
            FUNCTION_LOG.replace(FUNCTION_LOG.with_suffix('.log.prev'))
        launched = time.time()
        process = subprocess.Popen([str(exe), '-gdpr-compliant', '-nolauncher', '-start_tag=' + args.start_tag], cwd=str(GAME))
        report['pid'] = process.pid

        def in_game():
            try:
                return GAME_LOG.stat().st_mtime > launched and IN_GAME in text(GAME_LOG)
            except OSError:
                return False

        report['in_game_seconds'] = wait(in_game, args.ready_timeout, process)
        if report['in_game_seconds'] is None:
            raise RuntimeError('READINESS_TIMEOUT')
        if args.settle:
            try:
                process.wait(timeout=args.settle)
                raise RuntimeError('GAME_EXITED_DURING_SETTLE: ' + str(process.returncode))
            except subprocess.TimeoutExpired:
                pass
        for command in COMMANDS + args.extra_command:
            if process.poll() is not None:
                raise RuntimeError('GAME_EXITED_BEFORE_COMMAND: ' + command)
            result = run_command([str(GAME / 'hoi4_debug_console.exe'), '--pid', str(process.pid), '--command', command], 60)
            report['commands'][command] = result
            if result['exit'] != 0:
                raise RuntimeError('COMMAND_FAILED: ' + command)
        if args.smoke:
            smoke = args.output / 'smoke'
            command = [__import__('sys').executable, str(GAME / 'hoi4plugins/test/tools/run_normalization_smoke.py'),
                       '--pid', str(process.pid), '--helper', str(GAME / 'hoi4_debug_console.exe'), '--report', str(smoke)]
            for label in args.smoke_skip:
                command += ['--skip', label]
            report['smoke'] = run_command(command, 600)
            report['smoke']['checks'] = None
            if report['smoke']['exit'] != 0:
                raise RuntimeError('SMOKE_PROCESS_FAILED')
            checks = json.loads((smoke / 'comparison.json').read_text(encoding='utf-8'))['checks']
            report['smoke']['checks'] = checks
            if not isinstance(checks, dict) or not checks or any(v is not True for v in checks.values()):
                raise RuntimeError('SMOKE_CHECKS_FAILED')
    except (Exception, KeyboardInterrupt) as error:
        report['failures'].append(type(error).__name__ + ': ' + str(error))
    finally:
        report['alive_before_close'] = process is not None and process.poll() is None
        report['graceful_close'] = None
        if process is not None:
            if not report['alive_before_close']:
                report['failures'].append('GAME_EXITED_BEFORE_CLOSE: ' + str(process.poll()))
            try:
                report['graceful_close'] = close(process, args.close_timeout)
                if not report['graceful_close']:
                    report['failures'].append('CLOSE_TIMEOUT: process left running; do not restart')
            except (Exception, KeyboardInterrupt) as error:
                report['failures'].append('CLOSE_FAILED: ' + type(error).__name__ + ': ' + str(error))
            report['process_exit'] = process.poll()
            if report['process_exit'] not in (None, 0):
                report['failures'].append('GAME_EXIT_NONZERO: ' + str(report['process_exit']))
        report['still_running'] = process is not None and process.poll() is None
        log = text(FUNCTION_LOG) if process is not None else ''
        (args.output / 'function_log.log').write_text(log, encoding='utf-8')
        states = {}
        for line in log.splitlines():
            if '] [function:' in line and ' : ' in line:
                head, value = line.split(' : ', 1)
                states[head.split('] ')[-1]] = dict(available='[function:available]' in head, state=value)
        report['final_states'] = states
        report['unavailable'] = sorted(k for k, v in states.items() if not v['available'])
        identity = states.get('adapter.identity', {}).get('state', '')
        if process is not None and identity != report.get('sha256'):
            report['failures'].append('PLUGIN_NOT_LOADED_FOR_IMAGE:' + (identity or 'NO_FUNCTION_LOG'))
        report['accepted'] = not report['failures']
        report['failure'] = '; '.join(report['failures']) or None
        report['exit'] = 0 if report['accepted'] else 1
        (args.output / 'live.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({k: report.get(k) for k in ('sha256', 'pid', 'accepted', 'failure', 'unavailable',
                                                     'graceful_close', 'still_running')}, indent=2, ensure_ascii=False))
    return report['exit']


if __name__ == '__main__':
    raise SystemExit(main())
