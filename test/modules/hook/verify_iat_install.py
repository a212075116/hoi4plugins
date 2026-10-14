import argparse
import json
import pathlib

import frida


parser = argparse.ArgumentParser()
parser.add_argument("pid", type=int)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
session = frida.attach(args.pid)
script = session.create_script(r'''
rpc.exports.snapshot = function () {
    const game = Process.getModuleByName('hoi4.exe');
    const plugin = Process.getModuleByName('hoi4_mod_plugin.dll');
    const names = ['CreateFileW','CreateFileA','CreateDirectoryW','CreateDirectoryA'];
    const rows = game.enumerateImports().filter(e => names.includes(e.name)).map(e => {
        if (!e.slot) return {name:e.name, module:e.module, missingSlot:true};
        const target = e.slot.readPointer(), range = Process.findRangeByAddress(e.slot);
        return {name:e.name,module:e.module,slot:e.slot.toString(),target:target.toString(),
            protection:range ? range.protection : null,
            inPlugin:target.compare(plugin.base)>=0 && target.compare(plugin.base.add(plugin.size))<0};
    });
    return {pid:Process.id, pluginPath:plugin.path, pluginBase:plugin.base.toString(), rows};
};
''')
try:
    script.load()
    result = script.exports_sync.snapshot()
finally:
    script.unload()
    session.detach()
result["scope"] = "Read-only live imported slot snapshot; no hooks/native calls/spawn/kill; module-range ownership not exact symbol identification"
result["passed"] = all(any(r["name"] == n and r.get("inPlugin") for r in result["rows"])
                       for n in ["CreateFileW", "CreateDirectoryW"]) and all(r.get("inPlugin") for r in result["rows"])
args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["passed"] else 1)
