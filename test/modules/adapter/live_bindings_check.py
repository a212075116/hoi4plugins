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
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ' + name, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True, encoding='mbcs').stdout
    return [int(line.split('","')[1]) for line in out.splitlines() if line.startswith('"' + name + '"')]


def close(name, timeout=60):
    for pid in pids(name):
        subprocess.run(['powershell', '-NoProfile', '-Command',
                        '(Get-Process -Id %d).CloseMainWindow() | Out-Null' % pid], capture_output=True)
    start = time.time()
    while pids(name) and time.time() - start < timeout:
        time.sleep(1)
    graceful = not pids(name)
    if not graceful:
        subprocess.run(['taskkill', '/F', '/IM', name], capture_output=True)
        while pids(name):
            time.sleep(0.5)
    return graceful


def text(path):
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def wait(condition, timeout, name):
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return time.time() - start
        if not pids(name):
            raise RuntimeError('game exited while waiting')
        time.sleep(1)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--start-tag', default='CHI')
    parser.add_argument('--settle', type=float, default=30.0)
    args = parser.parse_args()
    exe = args.exe.resolve()
    name = exe.name
    args.output.mkdir(parents=True, exist_ok=True)
    for other in {'hoi4.exe', name}:
        close(other)
    if FUNCTION_LOG.exists():
        FUNCTION_LOG.replace(FUNCTION_LOG.with_suffix('.log.prev'))
    report = dict(exe=str(exe), sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                  plugin_sha256=hashlib.sha256((GAME / 'hoi4_mod_plugin.dll').read_bytes()).hexdigest())
    launched = time.time()
    subprocess.Popen([str(exe), '-gdpr-compliant', '-nolauncher', '-start_tag=' + args.start_tag], cwd=str(GAME))
    try:
        report['in_game_seconds'] = wait(lambda: IN_GAME in text(GAME_LOG) and GAME_LOG.stat().st_mtime > launched,
                                         400, name)
        if report['in_game_seconds'] is not None:
            time.sleep(args.settle)
            pid = pids(name)[0]
            report['commands'] = {}
            for command in COMMANDS:
                p = subprocess.run([str(GAME / 'hoi4_debug_console.exe'), '--pid', str(pid), '--command', command],
                                   capture_output=True, timeout=60)
                report['commands'][command] = dict(exit=p.returncode,
                                                   stdout=p.stdout.decode('utf-8', 'replace').splitlines()[-30:])
    except RuntimeError as error:
        report['failure'] = str(error)
    report['alive_before_close'] = bool(pids(name))
    report['graceful_close'] = close(name) if report['alive_before_close'] else None
    log = text(FUNCTION_LOG)
    (args.output / 'function_log.log').write_text(log, encoding='utf-8')
    states = {}
    for line in log.splitlines():
        if '] [function:' in line and ' : ' in line:
            head, value = line.split(' : ', 1)
            states[head.split('] ')[-1]] = dict(available='[function:available]' in head, state=value)
    report['final_states'] = states
    report['unavailable'] = sorted(k for k, v in states.items() if not v['available'])
    (args.output / 'live.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(dict(sha256=report['sha256'][:16], in_game=report.get('in_game_seconds'),
                          failure=report.get('failure'), unavailable=report['unavailable'],
                          graceful_close=report['graceful_close']), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
