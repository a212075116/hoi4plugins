"""Shared helper: attach frida and wait until the camera is actually readable."""
import os, sys, time, importlib.util

ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
JS_EXEC = os.path.join(ROOT, 'hoi4plugins', 'test', 'probes_js', '_exec_cmd.js')
HOST    = os.path.join(ROOT, 'hoi4plugins', 'test', 'probes_frida', 'frida_host.py')

def connect(js_path=None):
    spec = importlib.util.spec_from_file_location('fh', HOST)
    fh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fh)
    pid, session, sc, fresh = fh.connect(js_path or JS_EXEC, force_spawn=False)
    time.sleep(0.3)
    return sc.exports_sync

def wait_camera(e, timeout=150.0, poll=0.4, verbose=True):
    """Poll until idler+0x750 is a usable camera. Never a blind sleep."""
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        st = e.ready()
        if st.get('ok'):
            if verbose:
                print('camera ready after %.2fs  h=%.2f' % (time.time() - t0, st['h']))
            return st
        last = st
        time.sleep(poll)
    raise TimeoutError('camera not ready in %.1fs, last=%s' % (timeout, last))

def connect_and_wait(js_path=None, timeout=150.0):
    e = connect(js_path)
    wait_camera(e, timeout)
    return e
