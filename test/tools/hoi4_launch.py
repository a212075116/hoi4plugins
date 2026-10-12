"""Launch hoi4 and wait by POLLING for a readiness marker, never a fixed sleep."""
import os, subprocess, time, sys, shutil

ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
EXE  = os.path.join(ROOT, 'hoi4.exe')
LOG  = os.path.join(ROOT, 'reports', 'mod_loader_tbb.log')
MSBUILD = r'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe'

def read_log():
    try:
        with open(LOG, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return ''

def proc_alive():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq hoi4.exe', '/NH'],
                         capture_output=True, text=True).stdout
    return 'hoi4.exe' in out

def kill():
    subprocess.run(['taskkill', '/F', '/IM', 'hoi4.exe'], capture_output=True)
    t0 = time.time()
    while proc_alive() and time.time() - t0 < 20:
        time.sleep(0.2)

def clear_log():
    try: os.remove(LOG)
    except Exception: pass

def wait_for(marker, timeout=180.0, poll=0.15, verbose=True):
    t0 = time.time()
    last = ''
    while time.time() - t0 < timeout:
        txt = read_log()
        if marker in txt:
            return time.time() - t0, txt
        if not proc_alive():
            raise RuntimeError('hoi4.exe died while waiting for %r' % marker)
        if verbose and txt != last:
            last = txt
        time.sleep(poll)
    raise TimeoutError('marker %r not seen in %.1fs' % (marker, timeout))

def launch(args=None, wait_marker=None, timeout=180.0):
    args = args or ['-gdpr-compliant', '-start_tag=CHI', '-nolauncher']
    kill(); clear_log()
    subprocess.Popen([EXE] + args, cwd=ROOT)
    if wait_marker is None:
        return None, None
    dt, txt = wait_for(wait_marker, timeout)
    return dt, txt

def status():
    lines = [l for l in read_log().splitlines()
             if any(k in l for k in ('[eff]', '[plugin]', '[scan]'))]
    return '\n'.join(lines[-8:])

if __name__ == '__main__':
    marker = sys.argv[1] if len(sys.argv) > 1 else '[plugin] Camera_RegisterCommands'
    dt, _ = launch(wait_marker=marker)
    print('ready in %.2fs (marker %s)' % (dt, marker))
    print(status())
BUILD = os.path.join(ROOT, 'hoi4plugins', 'build', 'Release')
DEPLOY = ['tbb.dll', 'hoi4_mod_plugin.dll', 'hoi4_debug_console.exe']

def deploy():
    """Kill hoi4 first, then copy build outputs to game root. Returns list of (name, bytes)."""
    kill()
    out = []
    for name in DEPLOY:
        src = os.path.join(BUILD, name)
        dst = os.path.join(ROOT, name)
        if not os.path.exists(src):
            raise RuntimeError('missing build output: ' + src)
        for attempt in range(40):
            try:
                shutil.copyfile(src, dst)
                break
            except PermissionError:
                time.sleep(0.25)
        else:
            raise RuntimeError('cannot overwrite %s (still locked)' % dst)
        out.append((name, os.path.getsize(dst)))
    return out

def build_and_launch(marker='[plugin] Camera_RegisterCommands', timeout=180.0,
                    args=None, skip_build=False):
    """deploy then launch, waiting by polling. Never sleeps blindly."""
    if not skip_build:
        rc = subprocess.run([MSBUILD, os.path.join(ROOT, 'hoi4plugins', 'hoi4plugins.sln'),
                             '/p:Configuration=Release', '/p:Platform=x64',
                             '/v:minimal', '/nologo'],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors='replace')
        out = rc.stdout or ''
        if rc.returncode != 0:
            lines = [l for l in out.splitlines() if 'error' in l.lower() or 'warning' in l.lower()]
            raise RuntimeError('build failed rc=%s\n%s' % (rc.returncode, '\n'.join(lines[-15:]) or out[-2000:]))
    info = deploy()
    dt, _ = launch(args=args, wait_marker=marker, timeout=timeout)
    return dt, info
