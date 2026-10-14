import argparse
import collections
import hashlib
import json
import pathlib
import re
import struct

import pefile


def inspect(path):
    data = path.read_bytes()
    pe = pefile.PE(data=data)
    base = pe.OPTIONAL_HEADER.ImageBase
    sections = []
    for section in pe.sections:
        raw = section.get_data()
        sections.append((section.VirtualAddress, raw, section.Characteristics,
                         section.Name.rstrip(b'\0').decode('ascii', errors='replace')))

    def section_at(rva, size=1):
        return next((s for s in sections if s[0] <= rva and rva + size <= s[0] + len(s[1])), None)

    def executable(va):
        section = section_at(va - base)
        return bool(section and section[2] & 0x20000000)

    types = {}
    for rva, raw, flags, name in sections:
        for match in re.finditer(rb'\.\?A[VU][!-~]{1,512}?@@\x00', raw):
            td = rva + match.start() - 16
            if section_at(td, 16) is not None:
                types[td] = match[0][:-1].decode('ascii')
    locators = {}
    for rva, raw, flags, name in sections:
        if flags & 0x80000000 or flags & 0x20000000:
            continue
        for i in range(0, len(raw) - 23, 4):
            if raw[i:i+4] != b'\x01\0\0\0':
                continue
            signature, offset, cd_offset, td, chd, self_rva = struct.unpack_from('<6I', raw, i)
            if self_rva != rva + i or td not in types or not section_at(chd, 16):
                continue
            locators[base + self_rva] = dict(class_name=types[td], col_rva=self_rva,
                                           type_descriptor_rva=td, subobject_offset=offset, cd_offset=cd_offset)
    tables = []
    for rva, raw, flags, name in sections:
        if flags & 0x80000000 or flags & 0x20000000:
            continue
        for i in range(0, len(raw) - 39, 8):
            col = struct.unpack_from('<Q', raw, i)[0]
            if col not in locators:
                continue
            entries = list(struct.unpack_from('<4Q', raw, i + 8))
            if not all(executable(v) for v in entries):
                continue
            tables.append(dict(**locators[col], vftable_rva=rva+i+8, first_four_function_rvas=[v-base for v in entries]))
    exports = getattr(pe, 'DIRECTORY_ENTRY_EXPORT', None)
    names = [s.name.decode('ascii', errors='replace') if s.name else '#'+str(s.ordinal) for s in exports.symbols] if exports else []
    version = None
    if getattr(pe, 'VS_FIXEDFILEINFO', []):
        v = pe.VS_FIXEDFILEINFO[0]
        version = '.'.join(str(n) for n in [v.FileVersionMS >> 16, v.FileVersionMS & 65535,
                                           v.FileVersionLS >> 16, v.FileVersionLS & 65535])
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), file_version=version,
                machine=hex(pe.FILE_HEADER.Machine), image_base=hex(base), exports=names,
                export_categories=dict(collections.Counter('PHYSFS_*' if n.startswith(('PHYSFS_', '?PHYSFS_')) else 'other' for n in names)),
                named_factory_exports=[n for n in names if re.search('CreateInterface|GetInterface|Factory', n, re.I)],
                decorated_types=len(types), validated_col_candidates=len(locators), vftable_candidates=len(tables),
                classes=len({t['class_name'] for t in tables}), tables=tables,
                scope='Read-only on-disk PE x64 RTTI candidate scan: signature1/selfRVA/type name/readonly COL reference/four executable entries. Not object discovery, slot semantics, runtime validity or ABI proof.')


parser = argparse.ArgumentParser()
parser.add_argument('--image', type=pathlib.Path, action='append', required=True)
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
records = [inspect(p.resolve()) for p in args.image]
comparison = []
if len(records) == 2:
    def unique(record):
        groups = collections.defaultdict(list)
        for t in record['tables']:
            groups[t['class_name']].append(t)
        return {name: v[0] for name, v in groups.items() if len(v) == 1}
    a, b = map(unique, records)
    for name in sorted(a.keys() & b.keys()):
        comparison.append(dict(class_name=name, first_rva=a[name]['vftable_rva'], second_rva=b[name]['vftable_rva'],
                               moved=a[name]['vftable_rva'] != b[name]['vftable_rva'],
                               semantic_identity_proven=False))
result = dict(images=records, unique_name_pairs=comparison,
              warning='Names and candidate structures are anchors, not a supported factory or a guarantee of compatible virtual slots.')
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(dict(output=str(args.output.resolve()), images=[{k:v for k,v in x.items() if k not in ['tables','exports']} for x in records],
                     unique_name_pairs=len(comparison), moved_pairs=sum(x['moved'] for x in comparison),
                     selected=[[t for t in x['tables'] if t['class_name'] in ['.?AVCInGameIdler@@','.?AVCFrontEndIdler@@','.?AVCAddStabilityEffect@@']] for x in records]), indent=2))
