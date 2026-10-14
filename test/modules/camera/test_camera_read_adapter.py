import copy
import json
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/modules/camera'))
from camera_read_adapter_core import AdapterError, CameraReader, ImageBindings, ProcessMemory


class Memory:
    base = 0x7ff600000000
    obj = 0x200000
    cam = 0x300000

    def __init__(self,b):
        self.b = b
        self.blocks = {}
        self.reads = []
        self.verified = False
        self.hook = None
        b.sections = [(s[0],s[1],s[2],32 if s[2]&0x80000000 else s[3]) for s in b.sections]
        self.root = self.base + next(s[0] for s in b.sections if s[2]&0x80000000)
        self.blocks[self.root] = struct.pack('<4Q',self.obj,self.obj,0,0x18000)
        self.blocks[self.obj] = struct.pack('<Q',self.base+b.tables['CInGameIdler'])
        self.blocks[self.obj+b.getter['displacement']] = struct.pack('<Q',self.cam)
        self.blocks[self.base+b.tables['CInGameIdler']+b.getter['slot']*8] = struct.pack('<Q',self.base+b.getter['rva'])
        self.blocks[self.base+b.getter['rva']] = bytes.fromhex(b.getter['code'])
        values = bytearray(60)
        struct.pack_into('<f',values,0,310)
        struct.pack_into('<ii',values,52,50,3000)
        self.blocks[self.cam+0x69c] = bytes(values)

    def verify_image(self,b):
        self.verified = True

    def read(self,address,count):
        self.reads.append((address,count))
        if self.hook:
            value = self.hook(address,count)
            if value is not None:
                return value
        for start,data in self.blocks.items():
            if start <= address and address+count <= start+len(data):
                return data[address-start:address-start+count]
        raise AdapterError('READ_FAILED',hex(address))


bindings = ImageBindings(sys.argv[1])
backup = ImageBindings(sys.argv[2])
output = pathlib.Path(sys.argv[3]);output.parent.mkdir(parents=True,exist_ok=True)
rows = []


def case(name,change,expected='READY_READ_ONLY'):
    b=copy.copy(bindings);b.profile=dict(bindings.profile);b.tables=dict(bindings.tables)
    m=Memory(b);change(b,m)
    try:
        result=CameraReader(b,m).snapshot();observed=result['status']
    except AdapterError as e:
        result={'status':e.code,'detail':e.detail};observed=e.code
    assert observed==expected,(name,result)
    if expected=='UNREVIEWED_PROFILE':assert not m.reads and not m.verified
    if expected=='NOT_IN_MAP':assert not any(a==m.obj+0x750 or a>=m.cam and a<m.cam+0x1000 for a,n in m.reads)
    rows.append(dict(name=name,expected=expected,observed=observed,result=result,read_calls=len(m.reads)))


case('same-object-two-global-roots-and-unreadable-nontarget',lambda b,m:None)
case('unknown-sha-contract-blocked-before-any-read',lambda b,m:setattr(b,'profile',None),'UNREVIEWED_PROFILE')
case('offline-only-backup-profile-blocked',lambda b,m:setattr(b,'profile',backup.profile),'UNREVIEWED_PROFILE')
case('frontend-no-camera-dereference',lambda b,m:m.blocks.update({m.obj:struct.pack('<Q',m.base+b.tables['CFrontEndIdler'])}),'NOT_IN_MAP')
case('missing-live-object',lambda b,m:m.blocks.update({m.root:bytes(32)}),'OBJECT_MISSING')


def duplicate(b,m):
    m.blocks[m.root]=struct.pack('<4Q',m.obj,0x400000,0,0)
    m.blocks[0x400000]=m.blocks[m.obj]


case('two-live-objects-refused',duplicate,'OBJECT_AMBIGUOUS')
case('null-camera',lambda b,m:m.blocks.update({m.obj+0x750:bytes(8)}),'CAMERA_MISSING')
case('unreadable-camera',lambda b,m:m.blocks.pop(m.cam+0x69c),'READ_FAILED')
case('changed-vslot',lambda b,m:m.blocks.update({m.base+b.tables['CInGameIdler']+b.getter['slot']*8:bytes(8)}),'GETTER_CHANGED')
case('patched-getter',lambda b,m:m.blocks.update({m.base+b.getter['rva']:b'\x90'*8}),'GETTER_CHANGED')
for number in [float('nan'),float('inf'),-1.,3001.]:
    def invalid(b,m,v=number):
        data=bytearray(m.blocks[m.cam+0x69c]);struct.pack_into('<f',data,0,v);m.blocks[m.cam+0x69c]=bytes(data)
    case('invalid-height-'+repr(number),invalid,'INVALID_VALUES')
for low,high in [(50,50),(3000,50),(-1,3000),(50,1000001)]:
    def invalid(b,m,lo=low,hi=high):
        data=bytearray(m.blocks[m.cam+0x69c]);struct.pack_into('<ii',data,52,lo,hi);m.blocks[m.cam+0x69c]=bytes(data)
    case('invalid-range-'+repr((low,high)),invalid,'INVALID_VALUES')


def moving_values(b,m):
    calls=0
    def hook(a,n):
        nonlocal calls
        if a==m.cam+0x69c:
            calls+=1
            if calls==2:return bytes(n)
    m.hook=hook


case('changing-camera-values',moving_values,'STATE_CHANGED')
case('changing-root',lambda b,m:setattr(m,'hook',lambda a,n:struct.pack('<Q',0) if a==m.root and n==8 else None),'STATE_CHANGED')
case('loaded-image-mismatch',lambda b,m:setattr(m,'verify_image',lambda image:(_ for _ in ()).throw(AdapterError('LOADED_IMAGE_MISMATCH','fixture'))),'LOADED_IMAGE_MISMATCH')
assert bindings.getter['alias_slots']==[37,38]
assert backup.getter['alias_slots']==[37,38]
assert bindings.getter['rva']!=backup.getter['rva']
rows.append(dict(name='two-real-images-duplicate-slots-one-leaf-semantic-getter',observed='PASS',expected='PASS'))


class HeaderMemory:
    base=0x7ff600000000

    def read(self,address,count):
        assert address==self.base and count==len(self.headers)
        return self.headers


for mode,expected in [('preferred','PASS'),('relocated','PASS'),('wrong-base','LOADED_IMAGE_MISMATCH'),('timestamp','LOADED_IMAGE_MISMATCH')]:
    m=HeaderMemory();data=bytearray(bindings.data[:bindings.pe.OPTIONAL_HEADER.SizeOfHeaders])
    field=bindings.pe.OPTIONAL_HEADER.get_field_absolute_offset('ImageBase')
    if mode=='relocated':struct.pack_into('<Q',data,field,m.base)
    if mode=='wrong-base':struct.pack_into('<Q',data,field,m.base+0x10000)
    if mode=='timestamp':data[bindings.pe.FILE_HEADER.get_field_absolute_offset('TimeDateStamp')]^=1
    m.headers=bytes(data)
    try:ProcessMemory.verify_image(m,bindings);observed='PASS'
    except AdapterError as e:observed=e.code
    assert observed==expected
    rows.append(dict(name='header-'+mode,observed=observed,expected=expected))


def mutate(b,rva,value):
    sections=[]
    for start,raw,flags,size in b.sections:
        if start<=rva and rva+len(value)<=start+len(raw):
            data=bytearray(raw);data[rva-start:rva-start+len(value)]=value;raw=bytes(data)
        sections.append((start,raw,flags,size))
    b.sections=sections


for mode,expected in [('missing-type','TABLE_MISSING'),('duplicate-primary','TABLE_AMBIGUOUS'),('nonleaf-getter','GETTER_MISSING')]:
    b=copy.copy(bindings)
    if mode=='missing-type':
        b.sections=[(start,raw.replace(b'.?AVCInGameIdler@@\0',b'.?AVXInGameIdler@@\0'),flags,size) for start,raw,flags,size in b.sections]
    elif mode=='duplicate-primary':
        col=struct.unpack('<Q',b.bytes(b.tables['CInGameIdler']-8,8))[0]-b.base
        td=b.bytes(col+12,4);found=False
        for start,raw,flags,size in b.sections:
            if flags&(0x80000000|0x20000000):continue
            pos=raw.find(td)
            while pos>=12:
                i=pos-12
                if i+24<=len(raw):
                    sig,sub,cd,t,h,own=struct.unpack_from('<6I',raw,i)
                    if sig==1 and sub and cd==0 and own==start+i:
                        reference=raw.find(struct.pack('<Q',b.base+own))
                        if reference>=0 and reference+40<=len(raw) and all(b.executable(v-b.base) for v in struct.unpack_from('<4Q',raw,reference+8)):
                            mutate(b,start+i+4,bytes(4));found=True;break
                pos=raw.find(td,pos+1)
            if found:break
        assert found
    else:mutate(b,b.getter['rva']+7,b'\x90')
    try:
        if mode=='nonleaf-getter':b.find_getter(0x750)
        else:b.find_primary('CInGameIdler')
        observed='PASS'
    except AdapterError as e:observed=e.code
    assert observed==expected,(mode,observed)
    rows.append(dict(name='offline-'+mode,observed=observed,expected=expected))
result=dict(cases=len(rows),failed=0,rows=rows,scope='Actual adapter with bounded fake memory and two real offline PE inputs; no game writes, no claim of fake-memory outcomes being live transitions')
output.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(cases=len(rows),failed=0,exit=0)))
