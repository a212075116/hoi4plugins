import argparse
import json
import pathlib
import re
import struct
import sys

import capstone
from capstone.x86 import X86_OP_MEM, X86_REG_RIP

RIP_DISP=4
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'test/modules/camera'))
from camera_read_adapter_core import ImageBindings


def templates(image):
    names=['CAddStabilityEffect','CAlwaysTrigger','CHasStabilityTrigger','CCheckVariable']
    sizes=[296,96,304,544];slots=[25,23,26,23];result=[]
    for kind,name in enumerate(names):
        vt=image.find_primary(name)
        entry=image.find_primary(('?$CEffectEntry@V' if not kind else '?$CTriggerEntry@V')+name+'@@',2)
        function=lambda table,slot:struct.unpack('<Q',image.bytes(table+slot*8,8))[0]-image.base
        factory=function(entry,1);code=image.bytes(factory,192);offset=int(code[0]==0x40)
        assert code[offset:offset+6]==bytes.fromhex('534883ec20b9') and code[offset+10]==0xe8
        size=struct.unpack_from('<I',code,offset+6)[0];assert size==sizes[kind]
        allocator=factory+offset+15+struct.unpack_from('<i',code,offset+11)[0]
        result.append(dict(kind=kind,name=name,vt=vt,entry=entry,factory=factory,
                           parse=function(entry,0) if not kind else function(vt,4),
                           evaluate=function(vt,13 if not kind else 22),allocator=allocator,slots=slots[kind],allocation=size))
    assert len({t['allocator'] for t in result})==1
    return result


def signature(image,rva):
    decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);decoder.detail=True
    instructions=list(decoder.disasm(image.bytes(rva,128),image.base+rva))
    mask=bytearray(128);length=0
    for ins in instructions:
        at=ins.address-image.base-rva
        if at!=length:break
        for operand in ins.operands:
            if operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP:
                mask[at+ins.disp_offset:at+ins.disp_offset+RIP_DISP]=b'\1'*RIP_DISP
        if ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_JUMP):
            mask[at+ins.imm_offset:at+ins.imm_offset+ins.imm_size]=b'\1'*ins.imm_size
        length+=ins.size
        if ins.mnemonic in ['ret','int3','jmp']:break
    reloc=image.pe.OPTIONAL_HEADER.DATA_DIRECTORY[5]
    data=image.pe.get_data(reloc.VirtualAddress,reloc.Size);at=0
    while at+8<=len(data):
        page,size=struct.unpack_from('<II',data,at)
        if size<8 or at+size>len(data):break
        for n in range(at+8,at+size,2):
            entry=struct.unpack_from('<H',data,n)[0];position=page+(entry&4095)-rva
            width=8 if entry>>12==10 else 4 if entry>>12==3 else 0
            if width and 0<=position and position+width<=length:mask[position:position+width]=b'\1'*width
        at+=size
    raw=image.bytes(rva,length)
    return re.compile(b''.join(b'.' if mask[i] else re.escape(bytes([c])) for i,c in enumerate(raw)),re.S),length


def matches(image,pattern):
    found=[]
    for start,raw,flags,size in image.sections:
        if not flags&0x20000000:continue
        for m in pattern.finditer(raw):
            found.append(start+m.start())
            if len(found)>=2:return found
    return found


parser=argparse.ArgumentParser()
parser.add_argument('--baseline-image',type=pathlib.Path,required=True)
parser.add_argument('--image',type=pathlib.Path,required=True)
parser.add_argument('--output-directory',type=pathlib.Path,required=True)
args=parser.parse_args();base=ImageBindings(args.baseline_image);target=ImageBindings(args.image)
source=ROOT/'bindings'/(base.sha+'.registry')
fields=dict(line.split('=',1) for line in source.read_text(encoding='ascii').splitlines() if line)
same=base.sha==target.sha;target_fields={k:v for k,v in fields.items()}
target_fields['image_sha256']=target.sha;target_fields['runtime_registration']='1' if same else '0'
target_fields['static_token_count']=fields['static_token_count'] if same else '0'
rows=[]
for key,value in fields.items():
    if key in ['schema','image_sha256','contract','runtime_registration','static_token_count']:continue
    rva=int(value.split(':')[0],0)
    if same:
        rows.append(dict(symbol=key,status='EXACT_IMAGE_REUSE',rva=rva));continue
    if ':' not in value:
        target_fields[key]='0';rows.append(dict(symbol=key,status='NEEDS_DATA_XREF_REVIEW'));continue
    pattern,length=signature(base,rva);candidates=matches(target,pattern)
    if len(candidates)==1:
        found=candidates[0];target_fields[key]=hex(found)+':'+target.bytes(found,16).hex()
        rows.append(dict(symbol=key,status='UNIQUE_MASKED_CANDIDATE',rva=found,signature_bytes=length,abi_approved=False))
    else:
        target_fields[key]='0';rows.append(dict(symbol=key,status='AMBIGUOUS' if candidates else 'NOT_FOUND',at_most_first_two=candidates,signature_bytes=length))
args.output_directory.mkdir(parents=True,exist_ok=True)
profile=args.output_directory/(target.sha+'.registry');profile.write_text(''.join(k+'='+v+'\n' for k,v in target_fields.items()),encoding='ascii')
report=dict(baseline_sha256=base.sha,target_sha256=target.sha,templates=templates(target),symbols=rows,
            runtime_approved=same,profile=str(profile.resolve()),
            scope='Read-only migration candidates. RIP/branch displacements and relocation bytes masked, ordinary field/size constants retained. Unique bytes are not ABI proof; data roots and token count need review. Different image output is always disabled.')
(args.output_directory/'migration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(profile=str(profile.resolve()),template_families=4,automatic_table_method_allocator_fields=21,unique_function_candidates=sum(r['status']=='UNIQUE_MASKED_CANDIDATE' for r in rows),unresolved=sum(r['status'] in ['NEEDS_DATA_XREF_REVIEW','AMBIGUOUS','NOT_FOUND'] for r in rows),runtime_approved=same),indent=2))
