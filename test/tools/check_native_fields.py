import argparse
import collections
import json
import pathlib
import sys

import capstone
from capstone.x86 import X86_OP_MEM, X86_REG_RBP, X86_REG_RIP, X86_REG_RSP

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'test/tools'))
from migrate_native_symbols import catalog, read_profile
from native_fields import FIELDS
from symbol_scan_core import Image, ScanError

EXTRA_TYPES = ['.?AVCAddStabilityEffect@@', '.?AVCAlwaysTrigger@@', '.?AVCHasStabilityTrigger@@', '.?AVCCheckVariable@@',
               '.?AVCInGameIdler@@', '.?AVCFrontEndIdler@@']
CONTEXT = 2
LOW_SPECIFICITY = 0x40
NOISY = 40
MOSTLY = 0.9
DISSENT = 2


def instructions(image, fn, cache):
    if fn not in cache:
        try:
            cache[fn] = image.function_instructions(fn)
        except ScanError:
            cache[fn] = []
    return cache[fn]


def object_disps(ins):
    return [op.mem.disp for op in ins.operands
            if op.type == X86_OP_MEM and op.mem.base not in (0, X86_REG_RIP, X86_REG_RSP, X86_REG_RBP)]


def shape(ins):
    raw = bytearray(ins.bytes)
    for op in ins.operands:
        if op.type == X86_OP_MEM and ins.disp_size:
            size = 4 if op.mem.base == X86_REG_RIP else ins.disp_size
            raw[ins.disp_offset:ins.disp_offset + size] = b'\0' * size
    if ins.imm_size and (ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_JUMP)):
        raw[ins.imm_offset:ins.imm_offset + ins.imm_size] = b'\0' * ins.imm_size
    return bytes(raw)


def align(mine, index, theirs):
    if index < len(theirs) and shape(mine[index]) == shape(theirs[index]):
        return index
    first = max(0, index - CONTEXT)
    window = [shape(x) for x in mine[first:index + CONTEXT + 1]]
    shapes = [shape(x) for x in theirs]
    hits = [j for j in range(len(shapes) - len(window) + 1) if shapes[j:j + len(window)] == window]
    return hits[0] + index - first if len(hits) == 1 else None


def code_pairs(base, migration):
    from migrate_image import registry_specs
    pairs = {}
    groups, symbols = catalog()
    fields = read_profile(ROOT / 'bindings' / (base.sha + '.symbols'))
    registry = read_profile(ROOT / 'bindings' / (base.sha + '.registry'))
    rows = {r['key']: r for part in ('symbols', 'registry') for r in migration[part]['symbols']}
    keys = [(r['key'], r['group'], fields) for r in symbols if r['kind'] == 'CODE']
    keys += [(s['key'], 'registry', registry) for s in registry_specs() if s['function']]
    for key, group, source in keys:
        row = rows.get(key, {})
        twin = row.get('rva', row.get('baseline') if row.get('status') == 'EXACT_IMAGE_REUSE' else None)
        if twin:
            pairs[int(source[key].split(':')[0], 0)] = dict(twin=twin, source='code:' + key, group=group)
    return pairs


def table_pairs(base, target, pairs):
    groups, symbols = catalog()
    wanted = {(r['type'], r['offset']) for r in symbols if r['kind'] in ('SLOT', 'TABLE')}
    wanted |= {(t, 0) for t in EXTRA_TYPES}
    for kind, offset in sorted(wanted):
        mine, theirs = base.find_table(kind, offset), target.find_table(kind, offset)
        if len(mine) != 1 or len(theirs) != 1:
            continue
        count = min(base.tables()[mine[0]]['slots'], target.tables()[theirs[0]]['slots'])
        for slot in range(count):
            fn = base.slot(mine[0], slot)
            pairs.setdefault(fn, dict(twin=target.slot(theirs[0], slot), source='slot:%s+%d#%d' % (kind, offset, slot)))
    return pairs


def check(base, target, pairs):
    mine_cache, theirs_cache = {}, {}
    index = collections.defaultdict(list)
    for fn in pairs:
        for i, ins in enumerate(instructions(base, fn, mine_cache)):
            for disp in object_disps(ins):
                index[disp].append((fn, i))
    results = []
    for key, group, value, source in FIELDS:
        witnesses = index.get(value, [])
        votes = collections.Counter()
        aligned = 0
        sample = []
        for fn, i in witnesses:
            mine = instructions(base, fn, mine_cache)
            theirs = instructions(target, pairs[fn]['twin'], theirs_cache)
            at = align(mine, i, theirs)
            if at is None:
                continue
            new = object_disps(theirs[at])
            old = object_disps(mine[i])
            if len(new) != len(old):
                continue
            aligned += 1
            moved = new[old.index(value)]
            votes[moved] += 1
            if len(sample) < 4:
                sample.append(dict(source=pairs[fn]['source'], instruction=hex(mine[i].address - base.base),
                                   text=mine[i].mnemonic + ' ' + mine[i].op_str, target=moved))
        if not witnesses:
            status = 'NO_WITNESS'
        elif not votes:
            status = 'WITNESS_UNALIGNED'
        elif len(votes) == 1:
            status = 'SAME' if value in votes else 'MOVED'
        elif votes[value] >= MOSTLY * aligned and aligned - votes[value] <= DISSENT:
            status = 'MOSTLY_SAME'
        else:
            status = 'SPLIT'
        by_source = collections.defaultdict(collections.Counter)
        for fn, i in witnesses:
            by_source[pairs[fn]['source'].split('#')[0]]['witness'] += 1
        review = [] if status == 'SAME' else ['FIELD_' + status]
        if value < LOW_SPECIFICITY:
            review.append('LOW_SPECIFICITY')
        if len(witnesses) > NOISY:
            review.append('NOISY')
        results.append(dict(key=key, group=group, value=value, source=source, status=status,
                            witnesses=len(witnesses), aligned=aligned,
                            votes={hex(k): v for k, v in votes.most_common()}, review=review, sample=sample,
                            sources={k: v['witness'] for k, v in sorted(by_source.items())}))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-image', type=pathlib.Path, default=ROOT.parent / 'hoi4.exe')
    parser.add_argument('--image', type=pathlib.Path, required=True)
    parser.add_argument('--migration', type=pathlib.Path, required=True, help='migration.json from migrate_image.py')
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    base, target = Image(args.baseline_image), Image(args.image)
    migration = json.loads(args.migration.read_text(encoding='utf-8'))
    if migration['target_sha256'] != target.sha:
        raise SystemExit('migration report belongs to another image')
    report = field_report(base, target, migration)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(brief(report), indent=2))


def field_report(base, target, migration):
    pairs = table_pairs(base, target, code_pairs(base, migration))
    results = check(base, target, pairs)
    return dict(baseline_sha256=base.sha, target_sha256=target.sha, witness_functions=len(pairs),
                summary=dict(collections.Counter(r['status'] for r in results)), fields=results,
                scope='Static triage. A witness is an instruction in a migrated catalog function or same-type vtable slot '
                      'whose non-stack memory displacement equals the field offset; it is not tied to the owning object. '
                      'Only unanimous SAME needs no review. NO_WITNESS fields need manual evidence.')


def brief(report):
    out = dict(witness_functions=report['witness_functions'], summary=report['summary'])
    for status in ('MOVED', 'SPLIT', 'MOSTLY_SAME', 'WITNESS_UNALIGNED', 'NO_WITNESS'):
        keys = [r['key'] for r in report['fields'] if r['status'] == status]
        if keys:
            out[status.lower()] = keys
    return out


if __name__ == '__main__':
    main()
