# -*- coding: utf-8 -*-
# frida_host.py -- 通用 Frida 宿主: 优先 attach 已在跑的 hoi4.exe, 不再每次关游戏
#
# 用法:
#   from frida_host import connect, find_pid, wait_in_game
#   pid, session, sc, fresh = connect('flirt/loader/_xxx.js')
#   r = sc.exports_sync.xxx()
#   # 注意: 默认不 kill 游戏, 下次直接 attach 复用
#
# 为什么这么做: spawn+等待进入对局每次要 ~20s 且要重建整个世界状态;
# attach 可以在同一个游戏会话上连续跑多个探针, 状态可比。
import frida, time, json, os, sys

W = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
EXE = W + '/hoi4.exe'
# 初始国家 tag 由环境变量 HOI4_START_TAG 决定 (默认 CHI)。
# 用 mod 地图时, 必须换成该地图上真实存在的 tag, 否则进图会失败。
DEFAULT_START_TAG = os.environ.get('HOI4_START_TAG', 'CHI')
ARGS = [EXE, '-gdpr-compliant', '-start_tag=' + DEFAULT_START_TAG, '-nolauncher']
IN_GAME_MARK = 'Launching SINGLEPLAYER-game'


def set_start_tag(tag):
    """显式指定初始国家 tag (覆盖环境变量)"""
    global ARGS, DEFAULT_START_TAG
    DEFAULT_START_TAG = tag
    ARGS = [a for a in ARGS if not a.startswith('-start_tag=')]
    ARGS = [ARGS[0], ARGS[1], '-start_tag=' + tag] + ARGS[2:]
    return ARGS


def find_pid():
    # Frida 17: frida.enumerate_processes() 已移除, 改用 device API
    try:
        dev = frida.get_local_device()
    except Exception:
        dev = frida.get_device_manager().get_device('local')
    for p in dev.enumerate_processes():
        if p.name.lower() == 'hoi4.exe':
            return p.pid
    return None


def in_game():
    try:
        return IN_GAME_MARK in open(LOG, encoding='utf-8', errors='ignore').read()
    except Exception:
        return False


def wait_in_game(timeout=240, tag=''):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if in_game():
            print('[%s进入游戏] %.0fs' % (tag, time.time() - t0), flush=True)
            return True
        time.sleep(1)
    print('[%s等待进入游戏超时] %.0fs' % (tag, time.time() - t0), flush=True)
    return False


def connect(js_path, force_spawn=False, wait=True, tag=''):
    """attach 或 spawn, load JS。返回 (pid, session, script, fresh)"""
    pid = find_pid()
    fresh = False
    if pid is None or force_spawn:
        if pid is not None:
            print('[%s关闭旧进程 %d]' % (tag, pid), flush=True)
            try:
                frida.kill(pid)
            except Exception:
                pass
            time.sleep(3)
        try:
            os.remove(LOG)
        except Exception:
            pass
        argv = list(ARGS)
        if len(sys.argv) > 2 and sys.argv[2].startswith('-start_tag='):
            argv = [a for a in argv if not a.startswith('-start_tag=')] + [sys.argv[2]]
        print('[%s新开进程] %s' % (tag, ' '.join(argv)), flush=True)
        pid = frida.spawn(argv)
        fresh = True
    else:
        print('[%s复用已有进程 pid=%d]' % (tag, pid), flush=True)
    session = frida.attach(pid)
    sc = session.create_script(open(js_path, encoding='utf-8').read())
    sc.load()
    if fresh:
        frida.resume(pid)
        if wait:
            wait_in_game(tag=tag)
    return pid, session, sc, fresh


def wait_stable(sc, fn='st', key='chi', tries=60, gap=5, need=4, tag=''):
    """轮询 rpc export 直到状态连续 need 次不变"""
    last = None; stable = 0; t0 = time.time()
    while time.time() - t0 < tries * gap:
        try:
            st = getattr(sc.exports_sync, fn)()
        except Exception as e:
            st = {'ok': False, 'err': str(e)}
        k = json.dumps(st, ensure_ascii=False, sort_keys=True)
        if k != last:
            print('[%s状态 %.0fs] %s' % (tag, time.time() - t0, k), flush=True)
            last = k; stable = 0
        else:
            stable += 1
        if ((st.get(key) or {}).get('fleets') is not None) and stable >= need:
            print('[%s稳定]' % tag, flush=True)
            return st
        time.sleep(gap)
    return None



# ---------------------------------------------------------------------------
# CGameState 就绪判据 (替代定时等待)
#
# 原理: base+0x332F260 是一个 CGameState* 槽。
#       主菜单时它为 0 或国家数 0; 进入正式战略地图后 +0x318 = 国家数 (原版 440)。
#       实测: *(slot)=0x19c64a9e8f0, +0x310=CCountry**, +0x318=440
# 用法: session, sc = connect(...); wait_game_ready(session)
# ---------------------------------------------------------------------------
GS_JS = r'''
var m = Process.enumerateModules(), exe = null;
for (var i = 0; i < m.length; i++) if (m[i].name.toLowerCase() === 'hoi4.exe') exe = m[i];
var base = exe.base;
var GS_SLOT = 0x332F260;
rpc.exports.gs = function () {
  try {
    var slot = base.add(GS_SLOT);
    var gs = slot.readPointer();
    if (gs.isNull()) return { ready: false, why: 'CGameState 为空(主菜单/未加载)' };
    var n = gs.add(0x318).readS32();
    var prov = gs.add(0x2B0).readPointer();
    return { ready: n > 0, countries: n, gs: gs.toString(), provinces: prov.toString() };
  } catch (e) { return { ready: false, err: String(e) }; }
};
'''


def wait_game_ready(session, tag='', extra_wait=5, timeout=300, gap=1.0):
    """轮询 CGameState 直到进入正式战略地图, 再等 extra_wait 秒认为就绪"""
    sc = session.create_script(GS_JS)
    sc.load()
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        try:
            r = sc.exports_sync.gs()
        except Exception as e:
            r = {'ready': False, 'err': str(e)}
        if r.get('ready'):
            print('[%s进入战略地图] %.0fs  国家数=%s  CGameState=%s' % (
                tag, time.time() - t0, r.get('countries'), r.get('gs')), flush=True)
            time.sleep(extra_wait)
            print('[%s就绪] 已额外等待 %ds' % (tag, extra_wait), flush=True)
            return r
        k = json.dumps({kk: vv for kk, vv in r.items() if kk != 'gs'}, sort_keys=True)
        if k != last:
            print('[%s未就绪 %.0fs] %s' % (tag, time.time() - t0, k), flush=True)
            last = k
        time.sleep(gap)
    print('[%s等待超时] %.0fs' % (tag, time.time() - t0), flush=True)
    return None

def detach(session):
    try:
        session.detach()
    except Exception:
        pass
