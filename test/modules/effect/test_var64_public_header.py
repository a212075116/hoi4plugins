import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
header = root / "src/plugin/SDK_RVA/variable64/variable64.h"
shutil.copyfile(header, output / "variable64.h")
probe = '''#include "variable64.h"
typedef char slot_count_valid[(VAR64_SLOT_COUNT == 9) ? 1 : -1];
typedef char pointer_size_valid[(sizeof(void*) == 8) ? 1 : -1];
int (*raw_reader)(void*, const char*, long long*) = Var64_ReadStoredContainerRaw;
long long (*slot_reader)(int) = Var64_GetSlot;
void (*slot_writer)(int, long long) = Var64_SetSlot;
'''
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
results = {}
for language, flag, suffix in [("C", "/TC", ".c"), ("CPP", "/TP", ".cpp")]:
    name = "probe" + suffix
    (output / name).write_text(probe, encoding="ascii")
    cmd = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W4 /WX /c {flag} {name} /Fo:{language}.obj' + '"'
    p = subprocess.run(cmd, cwd=output, capture_output=True)
    results[language] = dict(command=cmd, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"),
                             stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
record = dict(results=results, source_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
              input_sha256=hashlib.sha256(probe.encode("ascii")).hexdigest(),
              scope="Actual copied public header only; no project include path; x64 slot constant/prototypes and standalone C/C++ compile; no link/runtime claim",
              exit=int(any(x["exit"] for x in results.values())))
(output / "result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
raise SystemExit(record["exit"])
