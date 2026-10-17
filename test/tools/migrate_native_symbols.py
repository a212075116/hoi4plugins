import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'test/tools'))
from symbol_scan_core import EXECUTE, WRITE, Image, ScanError

CATALOG = ROOT / 'src/plugin/adapter/symbol_catalog.h'
MAX_ANCHORS = 12
DELTA_WINDOW = 0x100000
MIN_STRING = 8


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


def same_shape(a, b):
    return a.mnemonic == b.mnemonic and a.size == b.size


def unique_function(base, target, fn):
    pattern, length, fixed = base.masked_pattern(fn)
    found = target.search(pattern, limit=2)
    return (found[0] if len(found) == 1 else None), found, length, fixed


def anchored(base, target, rva, kind):
    votes = collections.Counter()
    tried = []
    seen = set()
    for ref in base.rip_references(rva):
        if (kind == 'CODE') != (ref['kind'] != 'rip') or ref['function'] in seen or ref['function'] == rva:
            continue
        seen.add(ref['function'])
        if len(seen) > MAX_ANCHORS:
            break
        row = dict(anchor=ref['function'], instruction=ref['instruction'])
        tried.append(row)
        try:
            twin, found, length, fixed = unique_function(base, target, ref['function'])
        except ScanError as error:
            row['status'] = 'ANCHOR_SCAN_ERROR:' + str(error)
            continue
        if twin is None:
            row['status'] = 'ANCHOR_AMBIGUOUS' if found else 'ANCHOR_NOT_FOUND'
            continue
        index = base.instruction_index(ref['function'], ref['instruction'])
        mine = base.function_instructions(ref['function'])
        theirs = target.function_instructions(twin)
        if index is None or index >= len(theirs) or not same_shape(mine[index], theirs[index]):
            row['status'] = 'ANCHOR_SHAPE_CHANGED'
            continue
        value = target.operand_target(theirs[index])
        if value is None:
            row['status'] = 'ANCHOR_OPERAND_MISSING'
            continue
        row.update(status='VOTE', twin=twin, value=value)
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
        if string_locations(base, text) != [at] or {r['function'] for r in base.rip_references(at)} != {rva}:
            row['status'] = 'STRING_SHARED_IN_BASELINE'
            continue
        locations = string_locations(target, text)
        if len(locations) != 1:
            row['status'] = 'STRING_NOT_UNIQUE_IN_TARGET' if locations else 'STRING_NOT_FOUND'
            continue
        users = {r['function'] for r in target.rip_references(locations[0])}
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
    if len(votes) == 1:
        value = next(iter(votes))
        if target.is_function_start(value):
            return value, dict(detail, votes=votes[value])
        if target.executable(value) and target.function_of(value) is None:
            return value, dict(detail, votes=votes[value], leaf_without_unwind=True)
        detail['status'] = 'CONSENSUS_NOT_FUNCTION_START'
    elif votes:
        detail['status'] = 'CONSENSUS_SPLIT'
        detail['votes'] = {hex(k): v for k, v in votes.items()}
    return None, detail


def recover_data(base, target, rva, size):
    votes, tried = anchored(base, target, rva, 'DATA')
    detail = dict(method='REFERENCE_CONSENSUS', anchors=tried)
    if len(votes) != 1:
        if votes:
            detail['votes'] = {hex(k): v for k, v in votes.items()}
        return None, detail
    value = next(iter(votes))
    if not target.writable(value) or not target.writable(value + size - 1):
        return None, dict(detail, status='CONSENSUS_NOT_WRITABLE')
    return value, dict(detail, votes=votes[value])


def check_rtti(image, row):
    tables = image.find_table(row['type'], row['offset'])
    if len(tables) != 1:
        return dict(status='RTTI_TABLE_MISSING' if not tables else 'RTTI_TABLE_AMBIGUOUS', tables=tables[:4])
    table = tables[0]
    need = row['index'] + 1 if row['kind'] == 'SLOT' else row['index']
    if image.tables()[table]['slots'] < need:
        return dict(status='RTTI_TABLE_TOO_SHORT', table=table)
    result = dict(status='RTTI_RESOLVED', table=table)
    if row['kind'] == 'SLOT':
        result['slot'] = image.slot(table, row['index'])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-image', type=pathlib.Path, required=True)
    parser.add_argument('--image', type=pathlib.Path, required=True)
    parser.add_argument('--output-directory', type=pathlib.Path, required=True)
    parser.add_argument('--rescan', action='store_true', help='scan even when SHA matches the baseline')
    args = parser.parse_args()
    groups, symbols = catalog()
    base, target = Image(args.baseline_image), Image(args.image)
    fields = read_profile(ROOT / 'bindings' / (base.sha + '.symbols'))
    same = base.sha == target.sha and not args.rescan
    out = {'schema': '1', 'image_sha256': target.sha, 'contract': 'symbols_v1'}
    rows = []
    failed = set()
    for row in symbols:
        entry = dict(key=row['key'], kind=row['kind'], group=row['group'])
        if row['kind'] in ('SLOT', 'TABLE'):
            entry.update(check_rtti(target, row))
            if entry['status'] != 'RTTI_RESOLVED':
                failed.add(row['group'])
            rows.append(entry)
            continue
        old = int(fields[row['key']].split(':')[0], 0)
        entry['baseline'] = old
        if same:
            out[row['key']] = fields[row['key']]
            entry['status'] = 'EXACT_IMAGE_REUSE'
            rows.append(entry)
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
        rows.append(entry)
    deltas = collections.defaultdict(list)
    for entry in rows:
        if entry['status'] == 'CANDIDATE':
            deltas[entry['group']].append(entry['delta'])
    for entry in rows:
        if entry['status'] != 'CANDIDATE':
            continue
        review = []
        if entry.get('votes') == 1:
            review.append('SINGLE_ANCHOR')
        if entry.get('string_agrees') is False:
            review.append('STRING_DISAGREES')
        others = list(deltas[entry['group']])
        others.remove(entry['delta'])
        if len(others) >= 2 and all(abs(entry['delta'] - d) > DELTA_WINDOW for d in others):
            review.append('DELTA_OUTLIER')
        if review:
            entry['review'] = review
    approvals = {}
    for name in groups:
        approvals['approve.' + name] = fields['approve.' + name] if same else '0'
    ordered = {k: out[k] for k in ('schema', 'image_sha256', 'contract')}
    ordered.update(approvals)
    ordered.update({r['key']: out[r['key']] for r in symbols if r['kind'] in ('DATA', 'CODE')})
    args.output_directory.mkdir(parents=True, exist_ok=True)
    profile = args.output_directory / (target.sha + '.symbols')
    profile.write_text(''.join(k + '=' + v + '\n' for k, v in ordered.items()), encoding='ascii', newline='\n')
    summary = collections.Counter(r['status'] for r in rows)
    summary['NEEDS_REVIEW'] = sum('review' in r for r in rows)
    report = dict(
        baseline_sha256=base.sha, target_sha256=target.sha, profile=str(profile.resolve()),
        approved=same, complete_groups=[g for g in groups if g not in failed], incomplete_groups=sorted(failed),
        summary=dict(summary), symbols=rows,
        scope='Read-only candidates. Masked pattern for CODE; caller/reference consensus over uniquely matched anchors '
              'for DATA and ambiguous CODE; RTTI tables checked statically. Candidates are not ABI proof. '
              'A different image is always written with every approve.<group>=0.')
    (args.output_directory / 'migration.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(profile=report['profile'], approved=same, summary=report['summary'],
                          incomplete_groups=report['incomplete_groups']), indent=2))


if __name__ == '__main__':
    main()
