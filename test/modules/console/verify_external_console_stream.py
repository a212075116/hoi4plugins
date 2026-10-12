import ctypes,json,struct,time
import verify_external_console as V
K=V.K;out=V.OUT/'stream.json';assert not out.exists();p=V.pid();rows=[]
def openpipe():
 h=K.CreateFileW(r'\\.\pipe\hoi4-plugin-debug-v1-'+str(p),0xc0000000,0,None,3,0,None);assert h!=V.INVALID;return h
def write(h,b):
 n=ctypes.c_ulong();return bool(K.WriteFile(h,b,len(b),ctypes.byref(n),None)) and n.value==len(b)
def read(h,n):
 pieces=[]
 while n:
  b=ctypes.create_string_buffer(n);got=ctypes.c_ulong()
  if not K.ReadFile(h,b,n,ctypes.byref(got),None) or not got.value:return None
  pieces.append(b.raw[:got.value]);n-=got.value
 return b''.join(pieces)
def response(h):
 b=read(h,28)
 if b is None:return {'closed':True}
 _,_,ident,n,status,ok,tid=struct.unpack('<7I',b);text=read(h,n)
 return {'id':ident,'status':status,'ok':ok,'thread':tid,'message':text.decode('utf-8',errors='replace') if text is not None else None}
def req(i,s):b=s.encode();return struct.pack('<4I',0x31434448,1,i,len(b))+b
def check(name,ok,details):rows.append({'name':name,'ok':bool(ok),'details':details});print(name,'PASS' if ok else 'FAIL',flush=True)
h=openpipe()
try:
 b=req(1,'help setcamheight')
 for piece in [b[:5],b[5:16],b[16:20],b[20:]]:assert write(h,piece);time.sleep(.03)
 r=response(h);check('fragmented-header-and-body',r.get('ok')==1 and r.get('id')==1,r)
 assert write(h,req(2,'help setcamheight'));r=response(h);check('same-connection-next-id',r.get('ok')==1 and r.get('id')==2,r)
 assert write(h,req(2,'setcamheight 1234'));r=response(h);check('duplicate-id-disconnected',r.get('closed'),r)
finally:K.CloseHandle(h)
h=openpipe()
try:
 assert write(h,struct.pack('<4I',0x31434448,1,1,10)+b'hel');started=time.monotonic();r=response(h)
 check('partial-body-deadline',r.get('closed') and 4.5<=time.monotonic()-started<8,{'result':r,'seconds':time.monotonic()-started})
finally:K.CloseHandle(h)
r={'rows':rows,'checks':len(rows),'passed':sum(x['ok'] for x in rows)};r['exit']=int(r['checks']!=r['passed']);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='rows'}));raise SystemExit(r['exit'])
