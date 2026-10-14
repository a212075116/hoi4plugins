import argparse
import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET


parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
files = [p for p in (root / "src").rglob("*") if p.suffix in {".c", ".cpp", ".h", ".inc"}
         and "minihook" not in p.as_posix().lower()]
by_name = {}
for p in (root / "src").rglob("*"):
    if p.is_file():
        by_name.setdefault(p.name, []).append(p.resolve())
edges, unresolved, inventory = {}, [], []
for p in files:
    p = p.resolve()
    text = p.read_text(encoding="utf-8-sig")
    targets = []
    for name in re.findall(r'^\s*#include\s+"([^"]+)"', text, re.M):
        local = (p.parent / name).resolve()
        choices = [local] if local.exists() else by_name.get(pathlib.Path(name).name, [])
        if len(choices) != 1:
            unresolved.append(dict(source=str(p), include=name, candidates=[str(q) for q in choices]))
        else:
            targets.append(choices[0])
    edges[p] = targets
    inventory.append(dict(path=str(p), relative=p.relative_to(root).as_posix(),
                          bytes=p.stat().st_size, lines=len(text.splitlines()),
                          sha256=hashlib.sha256(p.read_bytes()).hexdigest(), includes=[str(q) for q in targets]))
projects, compiled = [], []
for p in (root / "src").rglob("*.vcxproj"):
    if "minihook" in p.as_posix().lower():
        continue
    entries = [(p.parent / n.attrib["Include"].replace("\\", "/")).resolve()
               for n in ET.parse(p).iter() if n.tag.endswith("ClCompile") and "Include" in n.attrib]
    projects.append(dict(path=str(p), compile_units=[str(q) for q in entries]))
    compiled.extend(q for q in entries if "minihook" not in q.as_posix().lower())


def closure(p, seen=None):
    seen = set() if seen is None else seen
    if p in seen:
        return seen
    seen.add(p)
    for q in edges.get(p, []):
        closure(q, seen)
    return seen


owners = {p: [str(unit) for unit in compiled if p in closure(unit)] for p in edges}
private = {str(p): owners[p] for p in edges if p.suffix in {".c", ".inc"} and p not in compiled}
structural_errors = list(unresolved)
for p, units in private.items():
    if len(units) != 1:
        structural_errors.append(dict(path=p, kind="private_fragment_compile_ownership", owners=units))


def site(path, needle):
    p = root / path
    text = p.read_text(encoding="utf-8-sig")
    start = text.index(needle)
    return dict(path=str(p), line=text[:start].count("\n") + 1, anchor=needle,
                source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())


header = (root / "src/plugin/SDK_RVA/variable64/variable64.h").read_text(encoding="utf-8-sig")
findings = [
    dict(id="F1", status="needs_ownership_verification", site=site("src/plugin/SDK_RVA/effect/effect_reg.c", "void* Effect_BuildTooltip("),
         observed="Local packed/fin are produced by native PackKey/Format; no matching release in this function, while Trigger tooltip releases native temporary strings.",
         not_claimed="No real leak size/root cause asserted; native output ownership must be verified before adding free."),
    dict(id="F2", status="resolved_for_verified_install_contract", site=site("src/plugin/SDK_RVA/hook/file_redirect.c", "int FileRedirect_Install("),
         observed="Per-slot saved originals,owned-slot retry,protection recovery,CAS foreign guard andcomplete-install path gate; required/presentoptional failures are reported.",
         evidence="test/reports/20261014_iat_install/final_verification.json;4100faultcases,realreadonlysharedpage32threads andlive module-range snapshots;not continuousforeignmonitor/hotunload"),
    dict(id="F3", status="resolved_for_verified_group_bootstrap", site=site("src/plugin/plugin_main.c", "static void RegisterPluginGroups("),
         observed="Shared per-group poller requires exact counts andscalar/language readiness,skips completedgroups,preserves per-phasebounded waits andreports incomplete groups; arithmetic retry skips successful originals.",
         evidence="test/reports/20261014_bootstrap/final_verification.json;521actualstartup scenarios and4096actualhookretry combinations pluslive8group completion; external registrarscontrolled,not allallocator transfer faults"),

]
if '#include "effect_reg.h"' in header and not re.search(r"\b(?:Effect[A-Z]\w*|EFF_\w*|RVA_\w*)\b", header):
    findings.append(dict(id="F4", status="unnecessary_public_header_dependency",
                         site=site("src/plugin/SDK_RVA/variable64/variable64.h", '#include "effect_reg.h"'),
                         observed="Public declarations use no Effect types; both current consumers already explicitly include effect_reg.h."))
reviewed_source_hashes = {'F1': '099cd8071fb079bb1f490abdd61b94e14a39ac7bd0f22f1cec0a4892bd654df7', 'F2': 'f172c7a8e438c0092ed9025666d4fd635e428da100a3700052e8ab1af2b3ead4', 'F3': '459d3d3af49763be614493b99e5ad8d11b9cdacdf4c42f63f724298f4a3ffced'}
for finding in findings:
    expected = reviewed_source_hashes.get(finding["id"])
    if expected and finding["site"]["source_sha256"] != expected:
        finding["status"] = "requires_renewed_manual_review"
        finding["observed"] = "Previously recorded observation; source changed since the reviewed snapshot. Reinspect before treating it as a current finding."

retained = [
    dict(contract="Array64 private implementation chain", reason="Private C fragments are included under array64_api.c, not separate link units; snapshot/wire/journal validate different identities and commit states.",
         sites=[site("src/plugin/SDK_RVA/variable64/array64_api.c", '#include "array64_shape_journal.c"'), site("src/plugin/SDK_RVA/variable64/array64_recovery.c", "static unsigned long long ar_hash("), site("src/plugin/SDK_RVA/variable64/array64_api.c", "static int a64_store(")]),
    dict(contract="Game/CRT/process heap and remote address spaces", reason="Game entry/strings use game allocator; journal scratch uses malloc/free; debt uses process heap; remote catalog owns process/snapshot. Sharing allocation/free indiscriminately would change ownership.",
         sites=[site("src/plugin/SDK_RVA/trigger/trigger_reg.c", "static void Trigger_FreeString(unsigned char* value, unsigned char* img)\n{"), site("src/plugin/SDK_RVA/variable64/variable64_debt.inc", "static Var64DebtRecord* Var64_NewDebt("), site("src/debug_console/command_catalog.cpp", "CommandCatalog::Query")]),
    dict(contract="Successful native hooks/workers keep process lifetime", reason="No hot unload interface is present. Shutdown client posts cancellation and joins its worker before closing the pipe; gate failure aborts before Peer and keeps published scheduler trampoline.",
         sites=[site("src/debug_console/main.cpp", "void RequestStop()"), site("src/debug_console/main.cpp", "g_stop = true; commands.Stop(); logs.join();"), site("src/plugin/SDK_RVA/console/debug_console.c", "static int StartPeerThreads(")]),
]
record = dict(source_root=str(root), files=len(files), inventory=inventory, projects=projects,
              private_fragments=private, compile_owners={str(p): q for p, q in owners.items()},
              structural_errors=structural_errors, findings=findings, retained_contracts=retained,
              scope="All own-source structural inventory/quoted include and project ownership; selected actual module contracts. Not every function semantically certified and not a completion proof.",
              goal_complete=False, exit=int(bool(structural_errors)))
(output / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(dict(files=len(files), projects=len(projects), private_fragments=len(private),
                     structural_errors=structural_errors, findings=[dict(id=x["id"], status=x["status"]) for x in findings], exit=record["exit"]), ensure_ascii=True, indent=2))
raise SystemExit(record["exit"])
