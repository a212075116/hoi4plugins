
'use strict';
const IMG = 0x140000000;
function img(ea) { return Process.getModuleByName('hoi4.exe').base.add(ea - IMG); }

const A_STAB_VT     = 0x14276EDF8;   // CAddStabilityEffect 虚表（25 槽）
const A_STAB_FACTORY= 0x14033C420;   // 它的工厂
const A_EFFECT_MAP  = 0x143330000;   // _EffectEntries
const A_REG_ENTRY   = 0x1405415A0;   // 注册
const A_CAM_SLOT    = 0x332F698;
const A_CAM_SETH    = 0x12643F0;

let g_calls = 0;
let g_log = [];

rpc.exports = {
  // 构造并注册；返回可读报告
  install: function (tokenId) {
    const L = [];
    const base = Process.getModuleByName('hoi4.exe').base;

    // ---- 1) 我的虚表：复制 CAddStabilityEffect 的 25 槽 ----
    const myVt = Memory.alloc(26 * 8);
    for (let i = 0; i < 25; i++) {
      myVt.add(i * 8).writePointer(img(A_STAB_VT).add(i * 8).readPointer());
    }
    L.push('myVt @ ' + myVt);

    // ---- 2) 我的执行函数（虚表 +0x68）----
    const setterFn = new NativeFunction(img(A_CAM_SETH), 'void', ['pointer', 'float']);
    const myExec = new NativeCallback(function (thisPtr, scope) {
      g_calls++;
      try {
        // 从实例 +0x2C 取参数（暂按 float 解读，仅用于观察）
        const raw2c = thisPtr.add(0x2C).readU32();
        const f2c = thisPtr.add(0x2C).readFloat();
        const raw58 = thisPtr.add(0x58).readU64().toString();
        const line = 'call#' + g_calls + ' this=' + thisPtr + ' scope=' + scope +
                     '  +0x2C(u32)=' + raw2c + ' (f32)=' + f2c.toFixed(3) +
                     '  +0x58(u64)=' + raw58;
        g_log.push(line);

        // 取摄像机并设置一个固定高度，验证「effect 执行确实能操控摄像机」
        const idler = img(A_CAM_SLOT).readPointer();
        if (!idler.isNull()) {
          const cam = idler.add(0x750).readPointer();
          if (!cam.isNull()) {
            setterFn(cam, 1500.0);
            g_log.push('   -> set camera height 1500 (now ' +
                       cam.add(0x69C).readFloat().toFixed(2) + ')');
          } else g_log.push('   -> cam NULL');
        } else g_log.push('   -> idler NULL');
      } catch (e) { g_log.push('   !! ' + e); }
    }, 'void', ['pointer', 'pointer']);
    myVt.add(0x68).writePointer(myExec);
    L.push('myExec @ ' + myExec + '  (写入 myVt+0x68)');

    // ---- 3) 工厂：造实例后把虚表换成我的 ----
    const makeInst = new NativeFunction(img(A_STAB_FACTORY), 'pointer', []);
    const myFactory = new NativeCallback(function () {
      const p = makeInst();
      if (!p.isNull()) p.writePointer(myVt);
      return p;
    }, 'pointer', []);
    L.push('myFactory @ ' + myFactory);

    // ---- 4) entry 虚表：只需 [0] 析构、[1] 工厂 ----
    const myEntryVt = Memory.alloc(3 * 8);
    // [0] 析构：借用 CEffectEntryBase 的析构（CAddStabilityEffect 的 entry 虚表 [0]）
    const srcEntryVt = img(0x14277CED8);
    myEntryVt.add(0).writePointer(srcEntryVt.add(0).readPointer());
    myEntryVt.add(1).writePointer(myFactory);
    L.push('myEntryVt @ ' + myEntryVt);

    // ---- 5) entry（16 字节）----
    const desc = Memory.allocUtf8String('Set camera height via injected effect');
    const entry = Memory.alloc(16);
    entry.writePointer(myEntryVt);
    entry.add(8).writePointer(desc);
    L.push('entry @ ' + entry + '  desc="' + desc.readUtf8String() + '"');

    // ---- 6) 注册进 _EffectEntries ----
    const mapPtr = img(A_EFFECT_MAP).readPointer();
    L.push('_EffectEntries map = ' + mapPtr);
    const reg = new NativeFunction(img(A_REG_ENTRY), 'pointer', ['pointer', 'int', 'pointer']);
    let rerr = null;
    try { reg(mapPtr, tokenId, entry); } catch (e) { rerr = String(e); }
    L.push('sub_1405415A0(map, ' + tokenId + ', entry)  err=' + (rerr || '(无)'));

    return L.join('\n');
  },

  log: function () { return g_log.length ? g_log.join('\n') : '(执行函数尚未被调用)'; },
  calls: function () { return g_calls; },

  // 手工直接调一次执行函数（验证函数本身可用）
  tryExec: function () {
    const makeInst = new NativeFunction(img(A_STAB_FACTORY), 'pointer', []);
    const p = makeInst();
    return '实例 @ ' + p + '  虚表 = ' + p.readPointer() + '  (原始应为 ' + img(A_STAB_VT) + ')';
  }
};
