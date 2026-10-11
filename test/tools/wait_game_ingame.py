# -*- coding: utf-8 -*-
import os, subprocess, sys, time
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
LOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
MARK = 'Launching SINGLEPLAYER'

def ingame():
    if not os.path.exists(LOG):
        return False
    try:
        with open(LOG, 'r', encoding='utf-8', errors='ignore') as f:
            for ln in f:
                if MARK in ln:
                    return True
    except Exception:
        return False
    return False

def main():
    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    t0 = time.time()
    while time.time() - t0 < timeout:
        if ingame():
            print('INGAME t=%.0fs' % (time.time() - t0), flush=True)
            return 0
        time.sleep(6)
    print('TIMEOUT after %ds' % timeout, flush=True)
    return 1

sys.exit(main())
