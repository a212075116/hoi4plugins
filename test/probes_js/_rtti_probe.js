var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
function u64(p, off) { try { return p.add(off).readPointer(); } catch (e) { return null; } }
function readCStr(p) { try { return p.readUtf8String(); } catch (e) { try { return p.readCString(); } catch (e2) { return null; } } }
function u32v(v) { return v >>> 0; }

// 读一个虚表的 RTTI: vt-8 -> COL -> TypeDescriptor -> name
function rttiOf(vtAddr) {
  var o = { vt: vtAddr, ok: false };
  try {
    var vt = ptr(vtAddr);
    var col = u64(vt, -8);
    if (!col || col.isNull()) { o.err = 'COL 为空'; return o; }
    o.col = col.toString();
    o.sig = u32v(u32(col, 0));
    o.offset = u32v(u32(col, 4));
    o.cdOffset = u32v(u32(col, 8));
    var tdRva = u32v(u32(col, 0x0C));
    o.tdRva = tdRva;
    var td = base.add(tdRva);
    o.td = td.toString();
    var nm = readCStr(td.add(0x10));
    o.name = nm;
    var cdRva = u32v(u32(col, 0x10));
    o.cdRva = cdRva;
    if (cdRva) {
      var cd = base.add(cdRva);
      o.cd = cd.toString();
      o.cdSig = u32v(u32(cd, 0));
      o.numBase = u32v(u32(cd, 8));
      var bcaRva = u32v(u32(cd, 0x0C));
      o.bcaRva = bcaRva;
      if (bcaRva) {
        var bca = base.add(bcaRva);
        o.bases = [];
        for (var k = 0; k < Math.min(o.numBase || 0, 12); k++) {
          var bcRva = u32v(bca.readU32()); bca = bca.add(4);
          var bc = base.add(bcRva);
          var td2Rva = u32v(u32(bc, 0));
          var td2 = base.add(td2Rva);
          o.bases.push(readCStr(td2.add(0x10)));
        }
      }
    }
    o.ok = true;
  } catch (e) { o.err = String(e); }
  return o;
}
rpc.exports.one = function (rva) { return rttiOf(base.add(rva).toString()); };
rpc.exports.many = function (rvas) { var out = []; for (var i = 0; i < rvas.length; i++) out.push(rttiOf(base.add(rvas[i]).toString())); return out; };
rpc.exports.base = function () { return base.toString(); };
rpc.exports.st = function () { return { ok: true, base: base.toString() }; };
