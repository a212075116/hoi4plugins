import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'test/tools'))
import capstone
from capstone.x86 import X86_OP_MEM, X86_REG_RIP
from symbol_scan_core import EXECUTE, WRITE, Image, ScanError

CATALOG = ROOT / 'src/plugin/adapter/symbol_catalog.h'
MAX_ANCHORS = 12
ANCHOR_POOL = 8
SUPERMAJORITY_VOTES = 5
SUPERMAJORITY_DISSENT = 1
SUPERMAJORITY_SHARE = 0.9
DELTA_WINDOW = 0x100000
MIN_STRING = 8
RAW_HITS = 8
CONTEXT = 2


def catalog():
    text = CATALOG.read_text(encoding='ascii')
    groups = {m[0]: m[1] for m in re.findall(r'^NATIVE_GROUP\((\w+),\s*"(\w+)"', text, re.M)}
    symbols = []
    for kind, args in re.findall(r'^NATIVE_(CODE|DATA|SLOT|TABLE)\((.*)\)\s*$', text, re.M):
        parts = [p.strip() for p in re.findall(r'"[^"]*"|[^,]+', args)]
        row = dict(kind=kind, id=parts[0], group=groups[parts[1]], key=parts[2].strip('"'))
        if kind == 'DATA':
            row['bytes'] = int(parts[3])
        if kind in ('SLOT', 'TABLE'):
            row.update(type=parts[3].strip('"'), offset=int(parts[4]), index=int(parts[5]))
        symbols.append(row)
    return list(groups.values()), symbols


def read_profile(path):
    fields = {}
    for line in path.read_text(encoding='ascii').splitlines():
        if line.strip():
            key, value = line.split('=', 1)
            fields[key.strip()] = value.strip()
    return fields


def unique_function(base, target, fn):
    pattern, length, fixed = base.masked_pattern(fn)
    if base.is_function_start(fn):
        found = target.search(pattern, limit=2)
    else:
        raw = target.search(pattern, limit=RAW_HITS, function_start=False)
        found = [a for a in raw if target.is_function_start(a) or target.function_of(a) is None][:2]
        if len(raw) == RAW_HITS:
            found = found + [None] if len(found) == 1 else found
    return (found[0] if len(found) == 1 else None), found, length, fixed


def masked_instruction(image, ins):
    raw = bytearray(ins.bytes)
    if any(op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP for op in ins.operands):
        raw[ins.disp_offset:ins.disp_offset + 4] = b'\0' * 4
    if ins.imm_size and (ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_JUMP)):
        raw[ins.imm_offset:ins.imm_offset + ins.imm_size] = b'\0' * ins.imm_size
    return bytes(raw)


def align(base, fn, index, target, twin):
    mine = base.function_instructions(fn)
    theirs = target.function_instructions(twin)
    if index < len(theirs) and masked_instruction(base, mine[index]) == masked_instruction(target, theirs[index]):
        return index, theirs
    first = max(0, index - CONTEXT)
    window = [masked_instruction(base, x) for x in mine[first:index + CONTEXT + 1]]
    shapes = [masked_instruction(target, x) for x in theirs]
    hits = [j for j in range(len(shapes) - len(window) + 1) if shapes[j:j + len(window)] == window]
    return (hits[0] + index - first if len(hits) == 1 else None), theirs


def twin_of(base, target, fn, hop):
    twin, found, length, fixed = unique_function(base, target, fn)
    if twin is not None or not hop:
        return twin, ('ANCHOR_AMBIGUOUS' if found else 'ANCHOR_NOT_FOUND')
    votes, tried = anchored(base, target, fn, 'CODE', False)
    if len(votes) == 1 and target.is_function_start(next(iter(votes))):
        return next(iter(votes)), 'HOP'
    return None, 'ANCHOR_HOP_FAILED'


def anchored(base, target, rva, kind, hop=True):
    votes = collections.Counter()
    tried = []
    seen = set()
    kinds = ('call', 'jump') if kind == 'CODE' else ('rip',)
    for ref in base.rip_references(rva, kinds, MAX_ANCHORS * ANCHOR_POOL):
        if ref['function'] in seen or ref['function'] == rva:
            continue
        seen.add(ref['function'])
        tried.append(dict(anchor=ref['function'], instruction=ref['instruction']))
    size = lambda row: sum(e - s for s, e in base.function_bounds(row['anchor']))
    tried = sorted(tried, key=lambda row: (-size(row), row['anchor']))[:MAX_ANCHORS]
    for second in (False, True):
        if second and (votes or not hop):
            break
        for row in tried:
            if row.get('status') == 'VOTE' or (second and row.get('status') not in ('ANCHOR_AMBIGUOUS', 'ANCHOR_NOT_FOUND')):
                continue
            try:
                twin, how = twin_of(base, target, row['anchor'], second)
                if twin is None:
                    row['status'] = how
                    continue
                index = base.instruction_index(row['anchor'], row['instruction'])
                at, theirs = align(base, row['anchor'], index, target, twin) if index is not None else (None, [])
            except ScanError as error:
                row['status'] = 'ANCHOR_SCAN_ERROR:' + str(error)
                continue
            if at is None:
                row['status'] = 'ANCHOR_SHAPE_CHANGED'
                continue
            value = target.operand_target(theirs[at])
            if value is None:
                row['status'] = 'ANCHOR_OPERAND_MISSING'
                continue
            row.update(status='VOTE', twin=twin, value=value, via=how if second else 'PATTERN')
            votes[value] += 1
    return votes, tried


def string_at(image, rva):
    if not image.readonly_data(rva):
        return None
    s = image.mapped_section(rva)
    raw = s[1][rva - s[0]:rva - s[0] + 512]
    end = raw.find(b'\0')
    text = raw[:end]
    if end < MIN_STRING or any(c < 0x20 or c > 0x7e for c in text):
        return None
    return text


def string_locations(image, text):
    found = []
    for start, raw, flags, mapped, name in image.sections:
        if flags & (WRITE | EXECUTE):
            continue
        for m in re.finditer(re.escape(text + b'\0'), raw):
            if m.start() == 0 or raw[m.start() - 1] == 0:
                found.append(start + m.start())
    return found


def string_consensus(base, target, rva):
    votes = collections.Counter()
    tried = []
    seen = set()
    for ins in base.function_instructions(rva):
        if ins.mnemonic != 'lea':
            continue
        at = base.operand_target(ins)
        text = string_at(base, at) if at is not None else None
        if text is None or text in seen:
            continue
        seen.add(text)
        if len(seen) > MAX_ANCHORS:
            break
        row = dict(string=text.decode('ascii'))
        tried.append(row)
        if string_locations(base, text) != [at] or {r['function'] for r in base.rip_references(at, ('rip',), 2)} != {rva}:
            row['status'] = 'STRING_SHARED_IN_BASELINE'
            continue
        locations = string_locations(target, text)
        if len(locations) != 1:
            row['status'] = 'STRING_NOT_UNIQUE_IN_TARGET' if locations else 'STRING_NOT_FOUND'
            continue
        users = {r['function'] for r in target.rip_references(locations[0], ('rip',), 2)}
        if len(users) != 1:
            row['status'] = 'STRING_USERS_' + str(len(users))
            continue
        value = users.pop()
        row.update(status='VOTE', value=value)
        votes[value] += 1
    return votes, tried


def recover_code(base, target, rva):
    value, detail = structural_code(base, target, rva)
    strings, rows = string_consensus(base, target, rva)
    detail['strings'] = rows
    if value is not None:
        if strings:
            detail['string_agrees'] = set(strings) == {value}
        return value, detail
    if len(strings) == 1 and not detail.get('votes'):
        value = next(iter(strings))
        if target.is_function_start(value):
            detail.pop('status', None)
            return value, dict(detail, method='STRING_CONSENSUS', votes=strings[value])
    if len(strings) > 1:
        detail['status'] = 'STRING_SPLIT'
    return None, detail


def structural_code(base, target, rva):
    twin, found, length, fixed = unique_function(base, target, rva)
    if twin is not None:
        return twin, dict(method='MASKED_PATTERN', signature_bytes=length, fixed_bytes=fixed)
    votes, tried = anchored(base, target, rva, 'CODE')
    detail = dict(method='CALLER_CONSENSUS', pattern_candidates=found, signature_bytes=length, anchors=tried)
    value, extra = consensus(votes)
    if value is not None:
        if target.is_function_start(value):
            return value, dict(detail, **extra)
        if target.executable(value) and target.function_of(value) is None:
            return value, dict(detail, leaf_without_unwind=True, **extra)
        detail['status'] = 'CONSENSUS_NOT_FUNCTION_START'
    elif votes:
        detail['status'] = 'CONSENSUS_SPLIT'
        detail['votes'] = {hex(k): v for k, v in votes.items()}
    return None, detail


def consensus(votes):
    if len(votes) == 1:
        value = next(iter(votes))
        return value, dict(votes=votes[value])
    if not votes:
        return None, {}
    (value, top), = votes.most_common(1)
    total = sum(votes.values())
    if top >= SUPERMAJORITY_VOTES and total - top <= SUPERMAJORITY_DISSENT and top >= SUPERMAJORITY_SHARE * total:
        return value, dict(votes=top, dissent={hex(k): v for k, v in votes.items() if k != value})
    return None, {}


def recover_data(base, target, rva, size):
    votes, tried = anchored(base, target, rva, 'DATA')
    detail = dict(method='REFERENCE_CONSENSUS', anchors=tried)
    value, extra = consensus(votes)
    if value is None:
        if votes:
            detail['votes'] = {hex(k): v for k, v in votes.items()}
        return None, detail
    old, new = base.mapped_section(rva), target.mapped_section(value)
    if not new or (old[2] & (WRITE | EXECUTE)) != (new[2] & (WRITE | EXECUTE)) or value + size > new[0] + new[3]:
        return None, dict(detail, status='CONSENSUS_SECTION_KIND_CHANGED')
    return value, dict(detail, **extra)


def check_rtti(image, row):
    tables = image.find_table(row['type'], row['offset'])
    if len(tables) != 1:
        return dict(status='RTTI_TABLE_MISSING' if not tables else 'RTTI_TABLE_AMBIGUOUS', tables=tables[:4])
    table = tables[0]
    need = row['index'] + 1 if row['kind'] == 'SLOT' else row['index']
    if image.tables()[table]['slots'] < need:
        return dict(status='RTTI_TABLE_TOO_SHORT', table=table)
    result = dict(status='RTTI_RESOLVED', table=table, slots=image.tables()[table]['slots'])
    if row['kind'] == 'SLOT':
        result['slot'] = image.slot(table, row['index'])
    return result


def check_layout(base, target, row, entry):
    old = check_rtti(base, row)
    if old['status'] != 'RTTI_RESOLVED':
        return 'BASELINE_RTTI_UNRESOLVED'
    if row['kind'] == 'TABLE':
        if old['slots'] != entry['slots']:
            entry['baseline_slots'] = old['slots']
        return None
    entry['baseline_slot'] = old['slot']
    pattern, length, fixed = base.masked_pattern(old['slot'])
    try:
        if pattern.match(target.bytes(entry['slot'], length)):
            entry['slot_shape'] = 'SAME'
            return None
    except ScanError:
        pass
    twin, detail = structural_code(base, target, old['slot'])
    if twin is not None and twin != entry['slot']:
        entry['slot_twin'] = twin
        return 'SLOT_FUNCTION_MOVED'
    entry['slot_shape'] = 'CHANGED_TWIN_SAME' if twin is not None else 'UNVERIFIED'
    return None


def resolve(base, target, rows, same):
    out = {}
    entries = []
    failed = set()
    for row in rows:
        entry = dict(key=row['key'], kind=row['kind'], group=row['group'])
        if row['kind'] in ('SLOT', 'TABLE'):
            entry.update(check_rtti(target, row))
            if entry['status'] == 'RTTI_RESOLVED' and not same:
                layout = check_layout(base, target, row, entry)
                if layout:
                    entry['status'] = layout
            if entry['status'] != 'RTTI_RESOLVED':
                failed.add(row['group'])
            entries.append(entry)
            continue
        old = row['baseline']
        entry['baseline'] = old
        if same:
            out[row['key']] = row['text']
            entry['status'] = 'EXACT_IMAGE_REUSE'
            entries.append(entry)
            continue
        try:
            if row['kind'] == 'CODE':
                value, detail = recover_code(base, target, old)
            else:
                value, detail = recover_data(base, target, old, row['bytes'])
        except ScanError as error:
            value, detail = None, dict(status='SCAN_ERROR:' + str(error))
        entry.update(detail)
        if value is None:
            out[row['key']] = '0'
            entry.setdefault('status', 'UNRESOLVED')
            failed.add(row['group'])
        else:
            out[row['key']] = hex(value) + (':' + target.fingerprint(value) if row['kind'] == 'CODE' else '')
            entry.update(status='CANDIDATE', rva=value, delta=value - old)
        entries.append(entry)
    flag_review(entries)
    return out, entries, failed


def flag_review(rows):
    deltas = collections.defaultdict(list)
    for entry in rows:
        if entry['status'] == 'CANDIDATE':
            deltas[entry['group']].append(entry['delta'])
    for entry in rows:
        if entry.get('slot_shape') == 'UNVERIFIED':
            entry['review'] = ['SLOT_UNVERIFIED']
        if 'baseline_slots' in entry:
            entry['review'] = ['TABLE_SLOT_COUNT_CHANGED']
        if entry['status'] != 'CANDIDATE':
            continue
        review = []
        if entry.get('votes') == 1:
            review.append('SINGLE_ANCHOR')
        if entry.get('dissent'):
            review.append('ANCHOR_DISSENT')
        if entry.get('string_agrees') is False:
            review.append('STRING_DISAGREES')
        others = list(deltas[entry['group']])
        others.remove(entry['delta'])
        if len(others) >= 2 and all(abs(entry['delta'] - d) > DELTA_WINDOW for d in others):
            review.append('DELTA_OUTLIER')
        if review:
            entry['review'] = review


def summarize(rows):
    summary = collections.Counter(r['status'] for r in rows)
    summary['NEEDS_REVIEW'] = sum('review' in r for r in rows)
    return dict(summary)


def migrate_symbols(base, target, same, output):
    groups, symbols = catalog()
    fields = read_profile(ROOT / 'bindings' / (base.sha + '.symbols'))
    for row in symbols:
        if row['kind'] in ('CODE', 'DATA'):
            row.update(text=fields[row['key']], baseline=int(fields[row['key']].split(':')[0], 0))
    out, rows, failed = resolve(base, target, symbols, same)
    ordered = {'schema': '1', 'image_sha256': target.sha, 'contract': 'symbols_v1'}
    for name in groups:
        ordered['approve.' + name] = fields['approve.' + name] if same else '0'
    ordered.update({r['key']: out[r['key']] for r in symbols if r['kind'] in ('DATA', 'CODE')})
    output.mkdir(parents=True, exist_ok=True)
    profile = output / (target.sha + '.symbols')
    profile.write_text(''.join(k + '=' + v + '\n' for k, v in ordered.items()), encoding='ascii', newline='\n')
    return dict(
        baseline_sha256=base.sha, target_sha256=target.sha, profile=str(profile.resolve()),
        approved=same, complete_groups=[g for g in groups if g not in failed], incomplete_groups=sorted(failed),
        summary=summarize(rows), symbols=rows,
        scope='Read-only candidates. Masked pattern for CODE; caller/reference consensus over uniquely matched anchors '
              'for DATA and ambiguous CODE; exclusive strings as fallback and cross-check; RTTI tables checked '
              'statically with slot twins and slot counts compared to the baseline. Candidates are not ABI proof. '
              'A different image is always written with every approve.<group>=0.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-image', type=pathlib.Path, required=True)
    parser.add_argument('--image', type=pathlib.Path, required=True)
    parser.add_argument('--output-directory', type=pathlib.Path, required=True)
    parser.add_argument('--rescan', action='store_true', help='scan even when SHA matches the baseline')
    args = parser.parse_args()
    base, target = Image(args.baseline_image), Image(args.image)
    report = migrate_symbols(base, target, base.sha == target.sha and not args.rescan, args.output_directory)
    (args.output_directory / 'migration.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(profile=report['profile'], approved=report['approved'], summary=report['summary'],
                          incomplete_groups=report['incomplete_groups']), indent=2))


if __name__ == '__main__':
    main()
