import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SOURCE_ROOT = pathlib.Path(sys.argv[1]).resolve()
OUTPUT = pathlib.Path(sys.argv[2]).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
records = {}
if len(sys.argv) > 3:
    import re
    baseline = pathlib.Path(sys.argv[3]).resolve()
    names = ["src/plugin/plugin_main.c"] + [
        f"src/plugin/SDK_RVA/achievement/{name}.c"
        for name in ("achievement_compat", "achievement_probe", "achievement_ui")
    ]
    def runtime_tokens(path):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^#include[^\n]*\n", "", text, flags=re.M)
        text = re.sub(r"^(?:extern )?(?:int|void) Achievement\w+\(void\);\n", "", text, flags=re.M)
        return re.sub(r"\s+", "", text)
    guard = {name: runtime_tokens(SOURCE_ROOT / name) == runtime_tokens(baseline / name) for name in names}
    (OUTPUT / "runtime_token_guard.json").write_text(json.dumps(guard, indent=2), encoding="utf-8")
    if not all(guard.values()):
        raise AssertionError(guard)
for name in ("verify_compat_native_fixture.py", "verify_ui_fixture.py", "verify_original_source.py"):
    folder = OUTPUT / pathlib.Path(name).stem
    folder.mkdir(exist_ok=True)
    script = (ROOT / "test/modules/achievement" / name).read_text(encoding="utf-8")
    variable = "R" if name == "verify_ui_fixture.py" else "ROOT"
    script = script.replace(
        f"{variable} = pathlib.Path(__file__).resolve().parents[3]",
        f"{variable} = pathlib.Path({str(SOURCE_ROOT)!r})",
    )
    lines = script.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("D = ") or line.startswith("REPORT = "):
            key = line.split(" = ", 1)[0]
            lines[i] = f"{key} = pathlib.Path({str(folder)!r})"
    adapter = folder / "fixture_driver.py"
    adapter.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = [sys.executable, str(adapter), "MODIFIED"]
    run = subprocess.run(command, capture_output=True)
    records[name] = dict(
        command=command, stdout=run.stdout.decode("utf-8", errors="replace"),
        stderr=run.stderr.decode("utf-8", errors="replace"), exit=run.returncode,
    )
    print(f"{name}: exit={run.returncode}")
    if run.returncode:
        print(records[name]["stdout"])
        print(records[name]["stderr"])
(OUTPUT / "results.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
sys.exit(int(any(row["exit"] for row in records.values())))
