import bisect
import hashlib
import pathlib
import re
import struct

import capstone
import numpy
import pefile
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP

EXECUTE, WRITE = 0x20000000, 0x80000000
RIP_DISP = 4


class ScanError(Exception):
    pass


class Image:
    def __init__(self, path):
        self.path = pathlib.Path(path).resolve()
        self.data = self.path.read_bytes()
        self.sha = hashlib.sha256(self.data).hexdigest()
        self.pe = pefile.PE(data=self.data, fast_load=True)
        if self.pe.FILE_HEADER.Machine != 0x8664 or self.pe.OPTIONAL_HEADER.Magic != 0x20b:
            raise ScanError('only PE x64 images are supported')
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        self.sections = []
        for s in self.pe.sections:
            raw = s.get_data()
            mapped = max(s.Misc_VirtualSize, len(raw))
            self.sections.append((s.VirtualAddress, raw, s.Characteristics, mapped, s.Name.rstrip(b'\0').decode('ascii', 'replace')))
        self.decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        self.decoder.detail = True
        self._functions = None
        self._tables = None
        self._reloc = None
        self._displacements = None

    def section(self, rva, count=1):
        for s in self.sections:
            if s[0] <= rva and rva + count <= s[0] + len(s[1]):
                return s
        return None

    def mapped_section(self, rva):
        for s in self.sections:
            if s[0] <= rva < s[0] + s[3]:
                return s
        return None

    def bytes(self, rva, count):
        s = self.section(rva, count)
        if s is None:
            raise ScanError('range ' + hex(rva))
        return s[1][rva - s[0]:rva - s[0] + count]

    def executable(self, rva):
        s = self.mapped_section(rva)
        return bool(s and s[2] & EXECUTE)

    def writable(self, rva):
        s = self.mapped_section(rva)
        return bool(s and s[2] & WRITE)

    def readonly_data(self, rva):
        s = self.mapped_section(rva)
        return bool(s and not s[2] & (WRITE | EXECUTE))

    def fingerprint(self, rva):
        return self.bytes(rva, 16).hex()

    def functions(self):
        if self._functions is None:
            directory = self.pe.OPTIONAL_HEADER.DATA_DIRECTORY[3]
            raw = self.pe.get_data(directory.VirtualAddress, directory.Size)
            entries = numpy.frombuffer(raw[:len(raw) // 12 * 12], dtype='<u4').reshape(-1, 3)
            roots = {}
            for begin, end, unwind in entries.tolist():
                root = begin
                info = unwind
                for _ in range(32):
                    try:
                        head = self.bytes(info & ~1, 4)
                    except ScanError:
                        break
                    if not head[0] >> 3 & 4:
                        break
                    codes = head[2]
                    chained = (info & ~1) + 4 + ((codes + 1) & ~1) * 2
                    root, _, info = struct.unpack('<III', self.bytes(chained, 12))
                roots[begin] = (end, root)
            starts = sorted(roots)
            self._functions = (starts, [roots[s][0] for s in starts], [roots[s][1] for s in starts])
        return self._functions

    def function_of(self, rva):
        starts, ends, roots = self.functions()
        i = bisect.bisect_right(starts, rva) - 1
        if i < 0 or rva >= ends[i]:
            return None
        return roots[i]

    def function_bounds(self, root):
        starts, ends, roots = self.functions()
        i = bisect.bisect_left(starts, root)
        if i < len(starts) and starts[i] == root:
            return [(starts[i], ends[i])]
        return []

    def is_function_start(self, rva):
        starts, ends, roots = self.functions()
        i = bisect.bisect_left(starts, rva)
        return i < len(starts) and starts[i] == rva and roots[i] == rva

    def tables(self):
        if self._tables is not None:
            return self._tables
        locators = {}
        for start, raw, flags, mapped, name in self.sections:
            if flags & (WRITE | EXECUTE) or len(raw) < 24:
                continue
            words = numpy.frombuffer(raw[:len(raw) // 4 * 4], dtype='<u4')
            index = numpy.nonzero(words[:-5] == 1)[0]
            own = start + index.astype(numpy.uint64) * 4
            index = index[(words[index + 5] == own) & (words[index + 2] == 0)]
            for i in index.tolist():
                type_rva, offset = int(words[i + 3]), int(words[i + 1])
                try:
                    text = self.bytes(type_rva + 16, 256)
                except Exception:
                    continue
                end = text.find(b'\0')
                if end <= 4 or not text.startswith(b'.?A'):
                    continue
                locators[start + i * 4] = (text[:end].decode('ascii', 'replace'), offset)
        tables = {}
        for start, raw, flags, mapped, name in self.sections:
            if flags & (WRITE | EXECUTE) or len(raw) < 16:
                continue
            words = numpy.frombuffer(raw[:len(raw) // 8 * 8], dtype='<u8')
            candidates = numpy.nonzero((words >= self.base) & (words < self.base + self.size))[0]
            for i in candidates.tolist():
                col = int(words[i]) - self.base
                if col in locators and i + 1 < len(words) and self.executable(int(words[i + 1]) - self.base):
                    count = 0
                    while i + 1 + count < len(words):
                        fn = int(words[i + 1 + count]) - self.base
                        if not 0 <= fn < self.size or not self.executable(fn):
                            break
                        count += 1
                    tables[start + (i + 1) * 8] = dict(type=locators[col][0], offset=locators[col][1], slots=count)
        self._tables = tables
        return tables

    def find_table(self, decorated, offset):
        return [t for t, v in self.tables().items() if v['type'] == decorated and v['offset'] == offset]

    def slot(self, table, index):
        return struct.unpack('<Q', self.bytes(table + index * 8, 8))[0] - self.base

    def vtable_references(self, fn):
        refs = []
        for table, info in self.tables().items():
            for index in range(info['slots']):
                if self.slot(table, index) == fn:
                    refs.append((info['type'], info['offset'], index, table))
        return refs

    def relocations(self):
        if self._reloc is None:
            directory = self.pe.OPTIONAL_HEADER.DATA_DIRECTORY[5]
            data = self.pe.get_data(directory.VirtualAddress, directory.Size)
            at, marks = 0, set()
            while at + 8 <= len(data):
                page, size = struct.unpack_from('<II', data, at)
                if size < 8 or at + size > len(data):
                    break
                for n in range(at + 8, at + size, 2):
                    entry = struct.unpack_from('<H', data, n)[0]
                    width = 8 if entry >> 12 == 10 else 4 if entry >> 12 == 3 else 0
                    for k in range(width):
                        marks.add(page + (entry & 4095) + k)
                at += size
            self._reloc = marks
        return self._reloc

    def function_instructions(self, root):
        pieces = self.function_bounds(root)
        if not pieces:
            return []
        start, end = pieces[0]
        data = self.bytes(start, end - start)
        return list(self.decoder.disasm(data, self.base + start))

    def masked_pattern(self, rva, maximum=160):
        end = None
        for s, e in self.function_bounds(rva):
            end = e
        count = min(maximum, (end - rva) if end else maximum)
        raw = self.bytes(rva, count)
        mask = bytearray(count)
        length = 0
        reloc = self.relocations()
        for ins in self.decoder.disasm(raw, self.base + rva):
            at = ins.address - self.base - rva
            if at != length:
                break
            for op in ins.operands:
                if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
                    mask[at + ins.disp_offset:at + ins.disp_offset + RIP_DISP] = b'\1' * RIP_DISP
            if ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_BRANCH_RELATIVE):
                if ins.imm_size:
                    mask[at + ins.imm_offset:at + ins.imm_offset + ins.imm_size] = b'\1' * ins.imm_size
            length += ins.size
            if ins.mnemonic == 'int3':
                break
        for k in range(length):
            if rva + k in reloc:
                mask[k] = 1
        raw = raw[:length]
        fixed = length - sum(mask[:length])
        pattern = re.compile(b''.join(b'.' if mask[i] else re.escape(bytes([c])) for i, c in enumerate(raw)), re.S)
        return pattern, length, fixed

    def search(self, pattern, limit=3, function_start=True):
        found = []
        for start, raw, flags, mapped, name in self.sections:
            if not flags & EXECUTE:
                continue
            for m in pattern.finditer(raw):
                at = start + m.start()
                if function_start and not self.is_function_start(at):
                    continue
                found.append(at)
                if len(found) >= limit:
                    return found
        return found

    def displacement_index(self):
        if self._displacements is None:
            ends, positions = [], []
            for start, raw, flags, mapped, name in self.sections:
                if not flags & EXECUTE or len(raw) < 8:
                    continue
                for phase in range(4):
                    count = (len(raw) - phase) // 4
                    at = start + phase + 4 * numpy.arange(count, dtype=numpy.int64)
                    disp = numpy.frombuffer(raw, dtype='<i4', count=count, offset=phase)
                    ends.append((at + 4 + disp).astype(numpy.int32))
                    positions.append(at.astype(numpy.int32))
            ends, positions = numpy.concatenate(ends), numpy.concatenate(positions)
            order = numpy.argsort(ends, kind='stable')
            self._displacements = (ends[order], positions[order])
        return self._displacements

    def rip_references(self, target, kinds=None, limit=None):
        ends, positions = self.displacement_index()
        lo = numpy.searchsorted(ends, target - 4, 'left')
        hi = numpy.searchsorted(ends, target, 'right')
        refs = sorted((int(p), int(target - e)) for e, p in zip(ends[lo:hi].tolist(), positions[lo:hi].tolist()))
        if limit is not None and len(refs) > limit:
            step = len(refs) // limit
            refs = [refs[i] for i in sorted(range(len(refs)), key=lambda i: (i % step, i))]
        verified = []
        cache = {}
        functions = set()
        for at, tail in refs:
            fn = self.function_of(at)
            if fn is None:
                continue
            if limit is not None and fn not in functions and len(functions) >= limit:
                continue
            if fn not in cache:
                cache[fn] = self.function_instructions(fn)
            for ins in cache[fn]:
                a = ins.address - self.base
                if a <= at < a + ins.size:
                    mem = [op for op in ins.operands if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP]
                    kind = None
                    if mem and a + ins.disp_offset == at:
                        if a + ins.size + mem[0].mem.disp == target:
                            kind = 'rip'
                    elif ins.imm_size == 4 and a + ins.imm_offset == at and (ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_JUMP)):
                        kind = 'call' if ins.group(capstone.CS_GRP_CALL) else 'jump'
                    if kind and (kinds is None or kind in kinds):
                        verified.append(dict(function=fn, instruction=a, kind=kind))
                        functions.add(fn)
                    break
        return verified

    def instruction_index(self, fn, instruction):
        for i, ins in enumerate(self.function_instructions(fn)):
            if ins.address - self.base == instruction:
                return i
        return None

    def operand_target(self, ins):
        for op in ins.operands:
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
                return ins.address - self.base + ins.size + op.mem.disp
        if (ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_JUMP)) and ins.operands and ins.operands[0].type == X86_OP_IMM:
            return ins.operands[0].imm - self.base
        return None
