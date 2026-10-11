const BASE = Module.getBaseAddress('hoi4.exe');
const cands = {
  'c140345000': 0x140345000, 'c140345C30': 0x140345C30, 'c140346A10': 0x140346A10,
  'c140347370': 0x140347370, 'c14034F750': 0x14034F750, 'c140350C40': 0x140350C40,
  'c140360250': 0x140360250,
  'k_add_14034C760': 0x14034C760, 'k_sub_140366BC0': 0x140366BC0,
  'k_mul_14035B9E0': 0x14035B9E0, 'k_div_140355C70': 0x140355C70
};
const hits = {};
Object.keys(cands).forEach(function (k) {
  const addr = BASE.add(cands[k]).sub(0x140000000);
  try {
    Interceptor.attach(addr, { onEnter: function () { hits[k] = (hits[k] || 0) + 1; } });
  } catch (e) { send('[probe] attach failed ' + k + ': ' + e); }
});
rpc.exports = {
  dump: function () { return JSON.stringify(hits); },
  reset: function () { Object.keys(hits).forEach(function (k) { delete hits[k]; }); return 'ok'; }
};
send('[probe] ready');
