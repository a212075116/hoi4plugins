import hashlib
import json
import pathlib
import re
import subprocess
import sys


root = pathlib.Path(sys.argv[1]).resolve()
baseline = pathlib.Path(sys.argv[2]).resolve()
output = pathlib.Path(sys.argv[3]).resolve()
output.mkdir(parents=True, exist_ok=True)
declaration = re.compile(r"^extern void Plugin_Log\(const char\* fmt,\s*\.\.\.\);\n", re.M)
include = re.compile(r'^#include "(?:SDK_RVA/common|../common)/plugin_log.h"\n', re.M)
header = root / "src/plugin/SDK_RVA/common/plugin_log.h"
legacy = []
consumers = []
guards = {}
for path in sorted((baseline / "src/plugin").rglob("*.c")):
    if "minihook" in path.parts:
        continue
    relative = path.relative_to(baseline)
    before = path.read_text(encoding="utf-8")
    current = (root / relative).read_text(encoding="utf-8")
    matches = declaration.findall(before)
    legacy.extend(matches)
    if matches:
        consumers.append(str(relative))
        if header.exists():
            assert not declaration.search(current), str(relative)
            assert len(include.findall(current)) == 1, str(relative)
    guards[str(relative)] = declaration.sub("", before) == include.sub("", declaration.sub("", current))
assert all(guards.values()), [name for name, ok in guards.items() if not ok]
assert len(legacy) == 17
backend = root / "src/plugin/SDK_RVA/common/log.c"
assert backend.read_bytes() == (baseline / backend.relative_to(root)).read_bytes()
main = (root / "src/plugin/plugin_main.c").read_text(encoding="utf-8")
assert len(re.findall(r"^void Plugin_Log\(", main, re.M)) == 1
if header.exists():
    assert len(include.findall(main)) == 1
    assert header.read_text(encoding="ascii") == "#pragma once\n\nvoid Plugin_Log(const char* fmt, ...);\n"
    fixture = f'#include "{header.as_posix()}"\n' * 2
else:
    fixture = "".join(legacy)
fixture += "void (*contract)(const char*, ...) = Plugin_Log;\n"
(output / "contract.c").write_text(fixture, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W4 /WX /TC /c contract.c /Fo:contract.obj' + '"'
process = subprocess.run(command, cwd=output, capture_output=True)
record = dict(
    command=command, cwd=str(output), stdout=process.stdout.decode("utf-8", errors="replace"),
    stderr=process.stderr.decode("utf-8", errors="replace"), exit=process.returncode,
    consumers=consumers, legacy_declarations=0 if header.exists() else len(legacy),
    shared_header=header.exists(), runtime_guards=guards,
    backend_sha256=hashlib.sha256(backend.read_bytes()).hexdigest(),
    scope="Interface compilation and exact source guard; production log behavior tested separately",
)
(output / "result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print("PASS logger interface and unchanged runtime guard" if process.returncode == 0 else json.dumps(record))
sys.exit(process.returncode)
