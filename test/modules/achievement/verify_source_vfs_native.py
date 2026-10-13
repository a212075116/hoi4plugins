import hashlib
import io
import json
import pathlib
import sys
import zipfile

import frida

ROOT = pathlib.Path(__file__).resolve().parents[3]
REPORT = ROOT / "test/reports/20261013_achievement_source"
payload = io.BytesIO()
with zipfile.ZipFile(payload, "w", zipfile.ZIP_STORED) as z:
    z.writestr("common/achievements.txt", b"fixture_override = { id = 999999 }\n")
archive = list(payload.getvalue())
js = r'''
const game = Process.getModuleByName('hoi4.exe');
const fn = (name, result, args) => new NativeFunction(game.getExportByName(name), result, args);
const open = fn('?PHYSFS_openRead@@YAPEAUPHYSFS_File@@PEBD@Z','pointer',['pointer']);
const length = fn('?PHYSFS_fileLength@@YA_JPEAUPHYSFS_File@@@Z','int64',['pointer']);
const read = fn('?PHYSFS_readBytes@@YA_JPEAUPHYSFS_File@@PEAX_K@Z','int64',['pointer','pointer','uint64']);
const close = fn('?PHYSFS_close@@YAHPEAUPHYSFS_File@@@Z','int',['pointer']);
const real = fn('?PHYSFS_getRealDir@@YAPEBDPEBD@Z','pointer',['pointer']);
const mount = fn('?PHYSFS_mountMemory@@YAHPEBX_KP6AXPEAX@ZPEBD4H@Z','int',['pointer','uint64','pointer','pointer','pointer','int']);
const unmount = fn('?PHYSFS_unmount@@YAHPEBD@Z','int',['pointer']);
const name = Memory.allocUtf8String('hoi4plugins_source_test_override.zip');
function get(path) {
 const p=Memory.allocUtf8String(path), f=open(p); if(f.isNull())throw Error('open failed '+path);
 try { const n=Number(length(f).toString());if(n<0||n>16777216)throw Error('size');
 const data=Memory.alloc(Math.max(1,n)), got=Number(read(f,data,n).toString());if(got!==n)throw Error('short read');
 const origin=real(p);return {bytes:n,origin:origin.isNull()?null:origin.readUtf8String(),data:Array.from(new Uint8Array(data.readByteArray(n)))};
 } finally {close(f);}
}
rpc.exports={run(bytes) {
 const alias='__hoi4plugins_vanilla_achievement_v1/common/achievements.txt';
 const before=get(alias), normal=get('common/achievements.txt');
 const manager=game.base.add(0x3330460).readPointer();
 const managerBefore=Array.from(new Uint8Array(manager.readByteArray(168)));
 const buffer=Memory.alloc(bytes.length);buffer.writeByteArray(bytes);
 let active=false, overwritten, unchanged, restored;
 try {
  if(!mount(buffer,bytes.length,ptr(0),name,ptr(0),0))throw Error('fixture mount failed');active=true;
  overwritten=get('common/achievements.txt');unchanged=get(alias);
 } finally {if(active&&!unmount(name))throw Error('fixture unmount failed');}
 restored=get('common/achievements.txt');
 const managerAfter=Array.from(new Uint8Array(manager.readByteArray(168)));
 return {before,normal,overwritten,unchanged,restored,definitions:manager.add(28).readS32(),managerBefore,managerAfter};
}};
'''
session = frida.attach(int(sys.argv[1]))
try:
    script = session.create_script(js)
    script.load()
    result = script.exports_sync.run(archive)
finally:
    session.detach()
original = (ROOT.parent / "common/achievements.txt").read_bytes()
checks = {
    "private_alias_original_bytes": bytes(result["before"]["data"]) == original,
    "private_alias_archive_origin": result["before"]["origin"] == "hoi4plugins_vanilla_achievement_v1.zip",
    "nonempty_public_override_took_effect": bytes(result["overwritten"]["data"]) == b"fixture_override = { id = 999999 }\n",
    "private_alias_ignored_override": result["before"] == result["unchanged"],
    "public_source_restored": result["normal"] == result["restored"],
    "manager_bytes_unchanged": result["managerBefore"] == result["managerAfter"],
    "definitions_293": result["definitions"] == 293,
}
for key in ["before", "normal", "overwritten", "unchanged", "restored"]:
    data = bytes(result[key].pop("data"))
    result[key]["sha256"] = hashlib.sha256(data).hexdigest()
for key in ["managerBefore", "managerAfter"]:
    result[key] = hashlib.sha256(bytes(result[key])).hexdigest()
record = {"pid": int(sys.argv[1]), "checks": checks, "result": result, "scope": "Temporary nonempty public VFS fixture removed in finally; no parser reload, conditions, or Steam calls"}
(REPORT / "native_vfs.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
sys.exit(0 if all(checks.values()) else 1)
