import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

R = pathlib.Path(__file__).resolve().parents[2]
D = R / "test/reports/20261013_achievement_eligibility"
T = R / "test/reports/20261012_variable64_transaction"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")


def run(command, cwd=R):
    p = subprocess.run(command, cwd=cwd, capture_output=True)
    return dict(command=command, cwd=str(cwd), stdout=p.stdout.decode("utf8", errors="replace"), stderr=p.stderr.decode("utf8", errors="replace"), exit=p.returncode)


phases = {}
for phase, expected in [("BASELINE", 1), ("MODIFIED", 0), ("ROLLBACK", 1), ("FINAL", 0)]:
    stdout = (D / ("native_" + phase + ".txt")).read_text(encoding="utf-8-sig")
    assert "Unknown command" in stdout if expected else "installed=1 active=1" in stdout
    phases[phase] = dict(input="achievementcompat", stdout=stdout, stderr="", exit=expected)
assert sha(D / "restored.achievement-compat.dll") == sha(D / "hoi4_mod_plugin.BASELINE.dll")
assert sha(D / "restored.achievement-compat.zip") == sha(D / "SOURCE_BASELINE.zip")
assert sha(R.parent / "hoi4_mod_plugin.dll") == sha(D / "hoi4_mod_plugin.MODIFIED.dll")
assert read(D / "compat_fixture.json")["result"]["exit"] == 0
assert read(D / "readonly_100.json")["passed"]
acceptance = read(D / "real_unlock_acceptance.json")
assert acceptance["elapsed_hours"] == 744 and acceptance["positive"]["steam_unlock_confirmed_by_user"]
save_before = read(D / "user_save_hashes_before.json")
assert all(sha(pathlib.Path(name)) == digest for name, digest in save_before.items())
assert "active=1" in (D / "native_FINAL_reload_compat.txt").read_text(encoding="utf8")
assert "manager_flags_A0_A4=0,0,0,0,0" in (D / "native_FINAL_status.txt").read_text(encoding="utf8")
manifest = read(T / "CURRENT_BUILD.json")
manifest.update(dll_archive=(D / "hoi4_mod_plugin.MODIFIED.dll").relative_to(R).as_posix(), sha256=sha(D / "hoi4_mod_plugin.MODIFIED.dll"), reason="Single-player native achievement compatibility; real ID254 unlock confirmed by user, saved candidates restore; not all achievements/modes certified")
save(T / "CURRENT_BUILD.json", manifest)
cp = read(T / "checkpoint.json")
cp.update(LAST_CONFIRMED_RESULT="Compatibility deployed; CHI native annex plus744 simulation hours: ID254 pending->completed and user confirms Steam unlock; ironman0/debug1/A3zero; candidates10->9, completed254->255. Corrected non-Ironman save A1zero path, active1 and9/255/29 restored. Fixture31/31 and100 readonly pass. Native three-state exit1/0/1; exact source/DLL rollback; final modified reapplied.", NEXT_EXECUTABLE_ACTION="Extend achievement acceptance to non-debug startup, mod/definition overrides at startup, real runtime after paused-save restoration, platform reconnect and more positive/negative conditions. Intermittent exit deferred by user, not prerequisite. Do not clear/reset account achievements or claim all293 passed.", ACCEPTANCE_EVENT="Basic single-player native eligibility and real ID254 Steam unlock achieved; broader mode/platform regression pending", current_build=manifest, achievement_compatibility_enabled=True, achievement_real_unlock_verified=True, achievement_verified_id=254)
cp.setdefault("intermittent_exit", {})["deferred_by_user"] = True
save(T / "checkpoint.json", cp)
save(D / "checkpoint.json", cp)
record = dict(native_three_state=phases, production_fixture=read(D / "compat_fixture.json"), readonly_100=read(D / "readonly_100.json"), real_unlock=acceptance, save_integrity=read(D / "save_integrity.json"), corrected_reload_stdout=(D / "reload_corrected_stdout.txt").read_text(encoding="utf8"), final_reload_stdout=(D / "native_FINAL_reload.txt").read_text(encoding="utf8"), final_compat_stdout=(D / "native_FINAL_reload_compat.txt").read_text(encoding="utf8"), final_status_stdout=(D / "native_FINAL_status.txt").read_text(encoding="utf8"), source_rollback_hash=sha(D / "restored.achievement-compat.zip"), dll_rollback_hash=sha(D / "restored.achievement-compat.dll"), steam_account_not_rolled_back=True, original_save_hashes_unchanged=len(save_before), intermittent_exit_deferred=True, errors=["Driver mistook native annex status0/ok0 blank and pause affirmative status0/ok0 for failures; retained failed records, recognized only exact native forms, no date jump or game timeout kill", "V1 used persisted A1 qualification as readiness, reload yielded active0/empty lists; replaced with real Steam stats/interface readiness, fixture31/31 and actual A1zero restore active1 verified", "Reloaded game remains paused; ticks0 is not evidence of continued-runtime stress; pending broader runtime test"])
save(D / "transaction.json", record)
with zipfile.ZipFile(T / "MODIFIED_FILE.zip") as z:
    names = set(z.namelist())
names.update(p.relative_to(R).as_posix() for folder in ["src", "ai_docs", "test/docs", "test/modules/achievement"] for p in (R / folder).rglob("*") if p.is_file() and p.suffix in [".c", ".cpp", ".h", ".md", ".py", ".vcxproj"])
names.add("test/tools/finalize_achievement_compat.py")
names.update(p.relative_to(R).as_posix() for p in D.iterdir() if p.is_file() and p.name != "checkpoint.json" and p.suffix in [".json", ".txt", ".zip", ".dll", ".exe", ".c", ".hoi4"])
with zipfile.ZipFile(T / "MODIFIED_FILE.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for name in sorted(names):
        if (R / name).exists():
            z.write(R / name, name)
shutil.copyfile(T / "BASELINE.zip", T / "before/MODIFIED_FILE.zip")
shutil.copyfile(T / "MODIFIED_FILE.zip", T / "after/MODIFIED_FILE.zip")
diff = run(["git", "diff", "--no-index", "--binary", "--", "before/MODIFIED_FILE.zip", "after/MODIFIED_FILE.zip"], T)
assert diff["exit"] == 1
(T / "DIFF_FILE.patch").write_text(diff["stdout"], encoding="utf8", newline="\n")
shutil.copyfile(T / "BASELINE.zip", T / "reconstruct/MODIFIED_FILE.zip")
patch = run(["git", "apply", "-p2", str(T / "DIFF_FILE.patch")], T / "reconstruct")
assert patch["exit"] == 0 and sha(T / "reconstruct/MODIFIED_FILE.zip") == sha(T / "MODIFIED_FILE.zip")
shutil.copyfile(T / "MODIFIED_FILE.zip", T / "restored.zip")
rollback = run(["C:/Program Files/Git/bin/bash.exe", str(T / "ROLLBACK.sh"), str(T / "restored.zip")])
assert rollback["exit"] == 0 and sha(T / "restored.zip") == sha(T / "BASELINE.zip")
audits = {}
for key, command in [("docs", [sys.executable, str(R / "test/tools/audit_project_docs.py"), "--package", str(T / "MODIFIED_FILE.zip")]), ("console", [sys.executable, str(R / "test/modules/console/audit_external_console_package.py"), str(T / "MODIFIED_FILE.zip")])]:
    audits[key] = run(command)
    assert audits[key]["exit"] == 0, audits[key]
v = read(T / "VERIFICATION.txt")
v["achievement_compatibility_stage3"] = dict(record=record, patch_reconstruction=patch, full_package_rollback=rollback, audits=audits, build_stdout=(D / "build.txt").read_text(encoding="utf-8-sig"), changed_symbols=["Eligible", "Compatible", "Possible", "Iron", "Rebuild", "Restore", "Update"], current_dll_sha256=manifest["sha256"])
save(T / "VERIFICATION.txt", v)
roles = {}
for name in ["MODIFIED_FILE.zip", "DIFF_FILE.patch", "VERIFICATION.txt", "ROLLBACK.sh"]:
    p = T / name
    data = p.read_bytes()
    if name == "MODIFIED_FILE.zip":
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            assert z.read("src/plugin/SDK_RVA/achievement/achievement_compat.c") == (R / "src/plugin/SDK_RVA/achievement/achievement_compat.c").read_bytes()
    if name == "VERIFICATION.txt":
        json.loads(data)
    roles[name] = dict(path=str(p), bytes=len(data), sha256=sha(p))
    print(json.dumps(roles[name]))
save(T / "artifact_hashes.json", roles)
print("NATIVE_COMPATIBILITY_AND_REAL_ID254_UNLOCK_VERIFIED; BROADER_REGRESSION_PENDING; EXIT_DIAGNOSIS_DEFERRED")
