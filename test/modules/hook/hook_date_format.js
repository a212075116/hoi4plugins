'use strict';
const RVA_FMT = 0x533460;      // sub_140533460 日期->字符串
const RVA_GET = 0x12D0490;     // GetDateString lambda
function M() { return Process.getModuleByName('hoi4.exe'); }
let nFmt = 0, nGet = 0;
const recs = [];
rpc.exports = {
  ready: function () { return M().base.toString(); },
  install: function () {
    const m = M();
    Interceptor.attach(m.base.add(RVA_GET), {
      onEnter: function (args) {
        nGet++;
        if (recs.length < 8) {
          try {
            const raw = args[3].readS32();
            recs.push('[GetDateString] #' + nGet + ' raw=' + raw +
              '  caller=' + this.returnAddress.sub(m.base));
          } catch (e) { recs.push('[GetDateString] #' + nGet + ' (args3 unreadable)'); }
        }
      }
    });
    Interceptor.attach(m.base.add(RVA_FMT), {
      onEnter: function (args) {
        nFmt++;
        if (recs.length < 8) {
          try {
            const cg = args[0];
            const raw = cg.add(8).readS32();
            let bt = '';
            try {
              const frames = Thread.backtrace(this.context, Backtracer.ACCURATE);
              bt = frames.slice(0, 6).map(function (f) { return f.sub(m.base).toString(); }).join(' <- ');
            } catch (e) { bt = '(no bt)'; }
            recs.push('[FMT] #' + nFmt + ' raw=' + raw + '\n         bt: ' + bt);
          } catch (e) { recs.push('[FMT] #' + nFmt + ' err'); }
        }
      }
    });
    return 'hooked fmt@' + m.base.add(RVA_FMT) + ' get@' + m.base.add(RVA_GET);
  },
  n: function () { return 'fmt=' + nFmt + ' get=' + nGet; },
  dump: function () { return recs.length ? recs.join('\n') : '(无调用)'; }
};
