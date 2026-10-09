"""Find and summarize HOI4 crash reports (exception.txt + minidump.dmp).

Paradox already writes one folder per crash under:
  Documents/Paradox Interactive/Hearts of Iron IV/crashes/<timestamp>/
Each contains exception.txt (stack with module+line), minidump.dmp, meta.yml and a logs/ snapshot.
Usage:
  python crash_report.py             # list last 10, show newest in full
  python crash_report.py -n 3        # show newest 3 in full
  python crash_report.py --mine      # only crashes whose stack mentions our plugin
  python crash_report.py --copy      # copy newest exception.txt next to the game exe
"""
import os, sys, shutil, argparse

ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
CRASH = os.path.join(os.path.expanduser('~'), 'Documents', 'Paradox Interactive',
                     'Hearts of Iron IV', 'crashes')
OUR_DLL = 'hoi4_mod_plugin.dll'


def crash_dirs():
    if not os.path.isdir(CRASH):
        return []
    out = []
    for name in os.listdir(CRASH):
        p = os.path.join(CRASH, name)
        if os.path.isdir(p):
            out.append((name, p))
    out.sort(key=lambda t: t[0], reverse=True)
    return out


def read_exception(p):
    f = os.path.join(p, 'exception.txt')
    try:
        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except Exception:
        return ''


def summarize(name, p, text, full=False):
    lines = text.splitlines()
    head = [l for l in lines[:6]]
    frames = [l for l in lines if OUR_DLL in l]
    has_dump = os.path.isfile(os.path.join(p, 'minidump.dmp'))
    has_meta = os.path.isfile(os.path.join(p, 'meta.yml'))
    print('=' * 78)
    print('CRASH %s' % name)
    print('  minidump=%s  meta=%s  logs=%s' % (
        'yes' if has_dump else 'no',
        'yes' if has_meta else 'no',
        'yes' if os.path.isdir(os.path.join(p, 'logs')) else 'no'))
    for l in head:
        if l.strip():
            print('  ' + l.strip())
    if frames:
        print('  --- our plugin frames ---')
        for l in frames:
            print('    ' + l.strip())
    if full:
        print('  --- full exception.txt ---')
        for l in lines:
            print('    ' + l)
    return bool(frames)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', type=int, default=1, help='how many newest to show in full')
    ap.add_argument('--mine', action='store_true', help='only crashes mentioning our plugin')
    ap.add_argument('--copy', action='store_true', help='copy newest exception.txt to game root')
    a = ap.parse_args()

    dirs = crash_dirs()
    if not dirs:
        print('no crash folders under ' + CRASH)
        return 1
    print('crash folder: ' + CRASH)
    print('total: %d' % len(dirs))
    print()

    shown = 0
    first = None
    for name, p in dirs:
        text = read_exception(p)
        if a.mine and OUR_DLL not in text:
            continue
        if first is None:
            first = (name, p, text)
        full = shown < a.n
        summarize(name, p, text, full=full)
        shown += 1
        if shown >= max(a.n, 3) and not a.mine:
            break

    if a.copy and first is not None:
        name, p, text = first
        dst = os.path.join(ROOT, 'crash_%s_exception.txt' % name)
        try:
            shutil.copyfile(os.path.join(p, 'exception.txt'), dst)
            print()
            print('copied -> ' + dst)
        except Exception as e:
            print('copy failed: %s' % e)
    return 0


if __name__ == '__main__':
    sys.exit(main())
