# -*- coding: utf-8 -*-
# 验证 hook 机制：挂必然被调用的 API
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
RUN = int(sys.argv[2]) if len(sys.argv) > 2 else 10
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var out = { apis: [], mods: [], mainThread: null };
  // 1) 必被调用的 user32 API
  ['user32.dll', 'kernel32.dll'].forEach(function(mn){
      var m = Process.findModuleByName(mn);
      if (!m) { out.mods.push(mn + ': NOT LOADED'); return; }
      out.mods.push(mn + ' @ ' + m.base);
      ['PeekMessageW','DispatchMessageW','GetMessageW','TranslateMessage',
       'GetTickCount','GetTickCount64','Sleep','WaitForSingleObject'].forEach(function(fn){
          var p = m.findExportByName(fn);
          if (!p) return;
          var rec = { name: mn + '!' + fn, addr: p.toString(), calls: 0 };
          out.apis.push(rec);
          try {
              Interceptor.attach(p, { onEnter: function(){ rec.calls++; } });
          } catch (e) { rec.err = String(e); }
      });
  });
  // 2) 主窗口消息：找 hoi4 的窗口类
  var uw = Process.findModuleByName('user32.dll');
  var EnumWindows = uw ? uw.findExportByName('EnumWindows') : null;
  // 3) 统计模块
  out.moduleCount = Process.enumerateModules().length;
  var interesting = Process.enumerateModules().filter(function(m){
      return /tbb|pdx|steam|d3d|dxgi|ucrt|vcruntime|msvcp/i.test(m.name); });
  out.interesting = interesting.map(function(m){ return m.name + '@' + m.base; });
  setTimeout(function(){ send(out); }, RUN_MS);
  '''.replace('RUN_MS', str(RUN*1000))
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
print('observing %d s ...' % RUN)
time.sleep(RUN + 4)
p = msgs[0].get('payload') if msgs else None
if p:
    print('modules =', p['moduleCount'])
    print('')
    print('--- 必然被调用的 API 命中 ---')
    for a in p['apis']:
        print('  %-28s %-18s calls=%d%s' % (a['name'], a['addr'], a['calls'],
              ('  ERR=' + a['err']) if a.get('err') else ''))
    print('')
    print('--- 相关模块 ---')
    for x in p['interesting']:
        print('  ' + x)
else:
    print('no payload', msgs[:2])
sess.detach()