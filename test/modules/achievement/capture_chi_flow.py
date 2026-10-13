import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Read-only capture for CHI annex-all achievement acceptance")
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--phase", choices=["before", "after-annex", "after-month"], required=True)
    parser.add_argument("--case", type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[3]
    game = root.parent
    command = [str(game / "hoi4_debug_console.exe"), "--pid", str(args.pid), "--command", "achievementstatus"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    match = re.search(r"ironman=(\d+) definitions=(\d+) pending=(\d+) completed=(\d+) excluded=(\d+)", result.stdout)
    fields = dict(zip(["ironman", "definitions", "pending", "completed", "excluded"], map(int, match.groups()))) if match else None
    compat_off = "compatibility hooks NOT enabled" in result.stdout
    record = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "command": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "command_exit": result.returncode,
        "fields": fields,
        "compatibility_explicitly_off": compat_off,
        "dll_sha256": hashlib.sha256((game / "hoi4_mod_plugin.dll").read_bytes()).hexdigest(),
        "original_definition_sha256": hashlib.sha256((game / "common/achievements.txt").read_bytes()).hexdigest(),
        "note": "Read-only observation, not proof of native happened or Steam unlock; no commands change game state",
    }
    args.case.mkdir(parents=True, exist_ok=True)
    destination = args.case / (args.phase + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    destination.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(destination.read_text(encoding="utf-8"))
    print(json.dumps(record, ensure_ascii=False, indent=2))
    print("record=" + str(destination.resolve()))
    return 1 if result.returncode != 0 or fields is None else 2 if compat_off else 0


if __name__ == "__main__":
    sys.exit(main())
