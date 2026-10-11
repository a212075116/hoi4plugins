'use strict';
const B = Process.getModuleByName('hoi4.exe').base;
const MAP_RVA = 0x3330000;
function readStr(p) { if (p.isNull()) return ''; try { return p.readCString(); } catch (e) { return ''; } }
function walk() {
  const res = [];
  const mapObj = B.add(MAP_RVA).readPointer();
  const head = mapObj.readPointer();
  const stack = [head.add(8).readPointer()];
  const seen = {};
  let guard = 0;
  while (stack.length > 0 && guard < 20000) {
    guard++;
    const node = stack.pop();
    if (node.isNull()) continue;
    if (seen[node.toString()]) continue;
    seen[node.toString()] = 1;
    if (node.add(25).readU8()) continue;
    const left = node.readPointer(); const right = node.add(16).readPointer();
    if (!left.isNull()) stack.push(left);
    if (!right.isNull()) stack.push(right);
    const entry = node.add(40).readPointer();
    if (entry.isNull()) continue;
    const desc = readStr(entry.add(8).readPointer());
    if (desc.indexOf('Clamps a variable between') === 0 || desc.indexOf('Clamps a temp variable') === 0) {
      const eVt = entry.readPointer();
      const slot0 = eVt.readPointer();
      res.push({ desc: desc.substring(0, 40), entryVtAddr: eVt.toString(),
                 entryVtRva: eVt.sub(B).toString(), slot0: slot0.toString(),
                 slot0Rva: slot0.sub(B).toString() });
    }
  }
  return res;
}
rpc.exports = { go: function () { return JSON.stringify({ base: B.toString(), items: walk() }, null, 1); } };
send('[effmap2] ready');
