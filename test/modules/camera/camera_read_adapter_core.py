import ctypes
import hashlib
import math
import pathlib
import struct
from ctypes import wintypes

import pefile


CURRENT_SHA = '7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5'
BACKUP_SHA = '46ebb324d734a2966e81681afdae77bbc23ff6a8be864ccf833495211a8c7e39'
PROFILES = {
    CURRENT_SHA: dict(camera_pointer=0x750, height=0x69c, minimum=0x6d0, maximum=0x6d4, runtime_layout=True),
    BACKUP_SHA: dict(camera_pointer=0x750, runtime_layout=False),
}


class AdapterError(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(code + ': ' + detail)


class ImageBindings:
    def __init__(self, image):
        self.path = pathlib.Path(image).resolve()
        self.data = self.path.read_bytes()
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.profile = PROFILES.get(self.sha)
        try:
            self.pe = pefile.PE(data=self.data, fast_load=True)
        except pefile.PEFormatError as e:
            raise AdapterError('INVALID_PE',str(e)) from e
        if self.pe.FILE_HEADER.Machine != 0x8664 or self.pe.OPTIONAL_HEADER.Magic != 0x20b:
            raise AdapterError('UNSUPPORTED_IMAGE', 'Only PE x64 is accepted')
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        self.sections = [(s.VirtualAddress, s.get_data(), s.Characteristics, s.Misc_VirtualSize)
                         for s in self.pe.sections]
        self.tables = {name: self.find_primary(name) for name in ['CInGameIdler', 'CFrontEndIdler']}
        self.getter = None
        if self.profile:
            self.getter = self.find_getter(self.profile['camera_pointer'])

    def section(self, rva, count=1):
        return next((s for s in self.sections if s[0] <= rva and rva + count <= s[0] + len(s[1])), None)

    def bytes(self, rva, count):
        s = self.section(rva, count)
        if s is None:
            raise AdapterError('IMAGE_RANGE', hex(rva))
        return s[1][rva-s[0]:rva-s[0]+count]

    def executable(self, rva):
        s = self.section(rva)
        return bool(s and s[2] & 0x20000000)

    def find_primary(self, name):
        decorated = ('.?AV' + name + '@@\0').encode('ascii')
        descriptors, locators, tables = set(), set(), set()
        for start, raw, flags, virtual_size in self.sections:
            offset = raw.find(decorated)
            while offset >= 0:
                if offset >= 16:
                    descriptors.add(start + offset - 16)
                offset = raw.find(decorated, offset + 1)
        for start, raw, flags, virtual_size in self.sections:
            if flags & (0x80000000 | 0x20000000):
                continue
            for td in descriptors:
                offset = raw.find(struct.pack('<I', td))
                while offset >= 0:
                    pos = offset - 12
                    if pos >= 0 and pos % 4 == 0 and pos + 24 <= len(raw):
                        sig, sub, cd, type_rva, hierarchy, own = struct.unpack_from('<6I', raw, pos)
                        if sig == 1 and sub == 0 and cd == 0 and own == start + pos and self.section(hierarchy, 16):
                            locators.add(own)
                    offset = raw.find(struct.pack('<I', td), offset + 1)
            for locator in locators:
                pointer = struct.pack('<Q', self.base + locator)
                offset = raw.find(pointer)
                while offset >= 0:
                    if offset % 8 == 0 and offset + 40 <= len(raw):
                        functions = struct.unpack_from('<4Q', raw, offset + 8)
                        if all(self.executable(f-self.base) for f in functions):
                            tables.add(start + offset + 8)
                    offset = raw.find(pointer, offset + 1)
        if len(tables) != 1:
            raise AdapterError('TABLE_AMBIGUOUS' if tables else 'TABLE_MISSING', name + ': ' + str(sorted(tables)))
        return next(iter(tables))

    def find_getter(self, field):
        matches = []
        for slot in range(256):
            fn = struct.unpack('<Q', self.bytes(self.tables['CInGameIdler'] + slot*8, 8))[0] - self.base
            if not self.executable(fn):
                break
            code = self.bytes(fn, 8)
            if code[:3] == b'\x48\x8b\x81' and code[7] == 0xc3:
                disp = struct.unpack('<i', code[3:7])[0]
            elif code[:3] == b'\x48\x8b\x41' and code[4] == 0xc3:
                disp = struct.unpack('<b', code[3:4])[0]
            else:
                continue
            if disp == field:
                matches.append(dict(slot=slot, rva=fn, displacement=disp, code=code.hex()))
        distinct = {(m['rva'],m['displacement'],m['code']) for m in matches}
        if len(distinct) != 1:
            raise AdapterError('GETTER_AMBIGUOUS' if matches else 'GETTER_MISSING', str(matches))
        return dict(matches[0],alias_slots=[m['slot'] for m in matches])

    def describe(self):
        return dict(image=str(self.path), sha256=self.sha, primary_vftables=self.tables, getter=self.getter,
                    runtime_layout=bool(self.profile and self.profile['runtime_layout']),
                    writable_sections=[dict(rva=s[0], size=s[3]) for s in self.sections if s[2] & 0x80000000],
                    status='OFFLINE_BOUND' if self.profile else 'UNREVIEWED_PROFILE', writes=False)

    def require_runtime(self):
        if not self.profile or not self.profile['runtime_layout']:
            raise AdapterError('UNREVIEWED_PROFILE', 'No approved runtime camera field contract for this SHA')


class CameraReader:
    def __init__(self, bindings, memory):
        self.bindings, self.memory = bindings, memory

    def pointer(self, address):
        return struct.unpack('<Q', self.memory.read(address, 8))[0]

    def snapshot(self):
        b, m = self.bindings, self.memory
        b.require_runtime()
        m.verify_image(b)
        states = {m.base + rva: name for name, rva in b.tables.items()}
        objects = {}
        seen = {}
        for start, raw, flags, virtual_size in b.sections:
            if not flags & 0x80000000:
                continue
            data = m.read(m.base + start, virtual_size)
            for offset in range(0, len(data) - 7, 8):
                obj = struct.unpack_from('<Q', data, offset)[0]
                if obj < 0x10000 or obj > 0x7fffffffffff or obj % 8:
                    continue
                relative = obj - m.base
                section = b.section(relative)
                if section and not section[2] & 0x80000000:
                    continue
                if obj not in seen:
                    try:
                        seen[obj] = self.pointer(obj)
                    except AdapterError:
                        seen[obj] = None
                if seen[obj] in states:
                    objects.setdefault(obj, dict(state=states[seen[obj]], roots=[]))['roots'].append(m.base + start + offset)
        if len(objects) != 1:
            raise AdapterError('OBJECT_AMBIGUOUS' if objects else 'OBJECT_MISSING', str({hex(k):v for k,v in objects.items()}))
        obj, state = next(iter(objects.items()))
        if state['state'] != 'CInGameIdler':
            raise AdapterError('NOT_IN_MAP', 'CFrontEndIdler is active; camera fields were not read')
        vt = m.base + b.tables['CInGameIdler']
        if self.pointer(obj) != vt:
            raise AdapterError('STATE_CHANGED', 'Idler vptr changed after discovery')
        getter = b.getter
        if self.pointer(vt + getter['slot']*8) != m.base + getter['rva']:
            raise AdapterError('GETTER_CHANGED', 'Loaded virtual slot differs from approved image')
        if m.read(m.base + getter['rva'], 8).hex() != getter['code']:
            raise AdapterError('GETTER_CHANGED', 'Loaded leaf getter differs from approved image')
        cam = self.pointer(obj + getter['displacement'])
        if cam < 0x10000 or cam % 8:
            raise AdapterError('CAMERA_MISSING', hex(cam))
        p = b.profile
        first = m.read(cam + p['height'], p['maximum'] - p['height'] + 4)
        height = struct.unpack_from('<f', first)[0]
        low, high = struct.unpack_from('<ii', first, p['minimum'] - p['height'])
        if not math.isfinite(height) or not 0 <= low < high <= 1000000 or not low <= height <= high:
            raise AdapterError('INVALID_VALUES', repr((height, low, high)))
        if (self.pointer(obj) != vt or self.pointer(obj + getter['displacement']) != cam or
                any(self.pointer(root) != obj for root in state['roots'])):
            raise AdapterError('STATE_CHANGED', 'Root, type or camera changed during read')
        if (self.pointer(vt + getter['slot']*8) != m.base + getter['rva'] or
                m.read(m.base + getter['rva'],8).hex() != getter['code']):
            raise AdapterError('GETTER_CHANGED','Getter changed during read')
        second = m.read(cam + p['height'], len(first))
        if second != first:
            raise AdapterError('STATE_CHANGED', 'Camera values changed during read; retry on a stable frame')
        return dict(status='READY_READ_ONLY', sha256=b.sha, idler=hex(obj), camera=hex(cam),
                    roots=[hex(a-m.base) for a in state['roots']], getter_slot=getter['slot'],
                    height=height, minimum=low, maximum=high, writes=False,
                    snapshot_contract='External bounded reads with before/after checks; not an atomic game-thread snapshot')


class ProcessMemory:
    def __init__(self, pid, image):
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.api
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        k.ReadProcessMemory.restype = wintypes.BOOL
        k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self.handle = k.OpenProcess(0x410, False, pid)
        if not self.handle:
            raise AdapterError('OPEN_FAILED', str(ctypes.get_last_error()))
        try:
            self.base, self.path = self.module(pid, image)
        except Exception:
            self.close()
            raise

    def module(self, pid, image):
        class Entry(ctypes.Structure):
            _fields_ = [('size',wintypes.DWORD),('module',wintypes.DWORD),('pid',wintypes.DWORD),
                        ('global_count',wintypes.DWORD),('process_count',wintypes.DWORD),
                        ('base',ctypes.c_void_p),('bytes',wintypes.DWORD),('handle',wintypes.HANDLE),
                        ('name',wintypes.WCHAR*256),('path',wintypes.WCHAR*260)]
        k = self.api
        for name in ['Module32FirstW', 'Module32NextW']:
            getattr(k,name).argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
            getattr(k,name).restype = wintypes.BOOL
        snap = k.CreateToolhelp32Snapshot(0x18,pid)
        if snap == ctypes.c_void_p(-1).value:
            raise AdapterError('MODULE_FAILED', str(ctypes.get_last_error()))
        try:
            entry = Entry();entry.size = ctypes.sizeof(entry)
            ok = k.Module32FirstW(snap,ctypes.byref(entry))
            while ok:
                if pathlib.Path(entry.path).resolve() == pathlib.Path(image).resolve():
                    return entry.base,entry.path
                ok = k.Module32NextW(snap,ctypes.byref(entry))
            raise AdapterError('MODULE_MISMATCH', str(image))
        finally:
            k.CloseHandle(snap)

    def read(self, address, count):
        if count < 1 or count > 0x1000000 or address < 0x10000:
            raise AdapterError('READ_RANGE', hex(address))
        out = ctypes.create_string_buffer(count);used = ctypes.c_size_t()
        if not self.api.ReadProcessMemory(self.handle,address,out,count,ctypes.byref(used)) or used.value != count:
            raise AdapterError('READ_FAILED', hex(address)+': '+str(ctypes.get_last_error()))
        return out.raw

    def verify_image(self, bindings):
        size = bindings.pe.OPTIONAL_HEADER.SizeOfHeaders
        expected = bytearray(bindings.data[:size])
        offset = bindings.pe.OPTIONAL_HEADER.get_field_absolute_offset('ImageBase')
        loaded = self.read(self.base,size)
        observed_base = struct.unpack_from('<Q',loaded,offset)[0]
        if observed_base == self.base:
            struct.pack_into('<Q',expected,offset,self.base)
        if loaded != expected:
            raise AdapterError('LOADED_IMAGE_MISMATCH', 'PE headers differ from selected file')

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
