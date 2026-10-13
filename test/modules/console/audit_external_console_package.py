import hashlib,json,pathlib,struct,sys,zipfile,xml.etree.ElementTree as E
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
p=pathlib.Path(sys.argv[1]).resolve();rows=[]
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 names=set(z.namelist())
 def data(n):return z.read(n) if n in names else b''
 def check(n,ok):rows.append({'name':n,'ok':bool(ok)})
 source=data('src/plugin/SDK_RVA/console/debug_console.c');client=data('src/debug_console/main.cpp');protocol=data('src/debug_console/protocol.h')
 project=data('src/plugin/plugin.vcxproj');E.fromstring(project)
 check('plugin-project-xml',True)
 check('server-compiled',bool(source) and b'console\\debug_console.c' in project)
 shared_log = all(b'Log_AppendV' in data(n) for n in ['src/plugin/SDK_RVA/common/log.c','src/plugin/plugin_main.c','src/plugin/SDK_RVA/console/console_cmd.c'])
 check('shared-log-compiled',b'common\\log.c' in project and shared_log)
 check('completion-catalog-compiled',b'command_catalog.cpp' in data('src/debug_console/debug_console.vcxproj') and b'CommandCatalog::Query' in client and b'PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION' in data('src/debug_console/command_catalog.cpp'))
 check('native-permission-dispatch',b'0x24B4D40' in source and b'0xDD3A50' in source and b'GetCurrentThreadId() != g_thread' in source)
 check('local-acl-and-server-identity',all(x in source for x in [b'ConvertSidToStringSidW',b'PIPE_REJECT_REMOTE_CLIENTS',b'FILE_FLAG_FIRST_PIPE_INSTANCE',b'ProcessIdToSessionId']) and b'GetNamedPipeServerProcessId' in client)
 check('bounded-cancel-fifo',all(x in source for x in [b'cancelled before execution',b'p->serial = ++g_serial',b'g_queue[i].serial < p->serial']) and b'DC_INPUT_MAX 2048' in protocol and b'DC_QUEUE_MAX 32' in protocol)
 check('bounded-log-tail',all(x in client for x in [b'65536',b'256',b'partial',b'sentinel',b'line continues']))
 check('user-visual-todo',b'U04' in data('test/docs/用户尚未测试的待办事项.md'))
 manifest='test/reports/20261012_variable64_transaction/CURRENT_BUILD.json'
 m=json.loads(data(manifest)) if manifest in names else {}
 for label,key,hashkey in [('dll','dll_archive','sha256'),('helper','helper_archive','helper_sha256')]:
  binary=data(m.get(key,''));valid=False
  if len(binary)>256 and binary[:2]==b'MZ':
   offset=struct.unpack_from('<I',binary,60)[0];valid=binary[offset:offset+4]==b'PE\0\0' and struct.unpack_from('<H',binary,offset+4)[0]==0x8664 and hashlib.sha256(binary).hexdigest()==m.get(hashkey)
  check(label+'-amd64-current-sha',valid)
 check('camera-old-job-cancelled',b'g_smoothCancelled = 1' in data('src/plugin/SDK_RVA/camera/camera_height.c') and b'from == target' in data('src/plugin/SDK_RVA/camera/camera_height.c'))
r={'package':str(p),'rows':rows,'checks':len(rows),'passed':sum(x['ok'] for x in rows)};r['exit']=int(r['checks']!=r['passed']);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(r['exit'])
