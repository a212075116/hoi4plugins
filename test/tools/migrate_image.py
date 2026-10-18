import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'test/tools'))
sys.path.insert(0, str(ROOT / 'test/modules/camera'))
from migrate_native_symbols import migrate_symbols, read_profile, resolve, summarize, write_fields
from symbol_scan_core import Image
from camera_read_adapter_core import AdapterError, ImageBindings
from check_native_fields import brief, field_report

REGISTRY_SPECS = ROOT / 'src/plugin/adapter/script_bindings.inc'
TOKEN_BYTES = 72
CAMERA_KEYS = ('camera_pointer', 'height', 'minimum', 'maximum')
CAMERA_FIELDS = dict(camera_pointer='camera.object_to_camera', height='camera.height', minimum='camera.minimum',
                     maximum='camera.maximum')


def registry_specs():
    text = REGISTRY_SPECS.read_text(encoding='ascii')
    return [dict(key=k, bytes=int(n), function=f == 'true', readonly=r == 'true')
            for k, n, f, r in re.findall(r'\{"([\w.]+)",NS_\w+,(\d+),(true|false),(true|false)\}', text)]


def migrate_registry(base, target, same, output):
    fields = read_profile(ROOT / 'bindings' / (base.sha + '.registry'))
    count = int(fields['static_token_count'])
    rows = []
    for spec in registry_specs():
        text = fields[spec['key']]
        rows.append(dict(key=spec['key'], kind='CODE' if spec['function'] else 'DATA', group='registry',
                         bytes=spec['bytes'], text=text, baseline=int(text.split(':')[0], 0)))
    start = int(fields['token.static'], 0)
    rows.append(dict(key='token.static_end', kind='DATA', group='registry', bytes=1,
                     text=hex(start + count * TOKEN_BYTES), baseline=start + count * TOKEN_BYTES))
    out, entries, failed = resolve(base, target, rows, same)
    end = int(out.pop('token.static_end'), 0)
    new_start = int(out['token.static'], 0)
    tokens = (end - new_start) // TOKEN_BYTES if end > new_start and (end - new_start) % TOKEN_BYTES == 0 else 0
    if same:
        tokens = count
    elif not tokens:
        failed.add('registry')
    ordered = {'schema': '1', 'image_sha256': target.sha, 'contract': 'registry_v1',
               'runtime_registration': fields['runtime_registration'] if same else '0',
               'static_token_count': str(tokens)}
    ordered.update({r['key']: out[r['key']] for r in rows if r['key'] != 'token.static_end'})
    profile = output / (target.sha + '.registry')
    profile.write_text(''.join(k + '=' + v + '\n' for k, v in ordered.items()), encoding='ascii', newline='\n')
    return dict(profile=str(profile.resolve()), approved=same, complete=not failed, static_token_count=tokens,
                baseline_static_token_count=count, summary=summarize(entries), symbols=entries,
                scope='Same engine as symbols. static_token_count is (end-start)/72 from a separately migrated '
                      'array-end reference. Templates, factory ABI and allocator are left to the runtime binder.')


def migrate_camera(base, target_path, sha, same, output, layout):
    fields = read_profile(ROOT / 'bindings' / (base.sha + '.profile'))
    result = dict(baseline={k: fields[k] for k in CAMERA_KEYS})
    found = {r['key']: r for r in layout['fields']}
    offsets, origin = {}, {}
    for key in CAMERA_KEYS:
        row = found.get(CAMERA_FIELDS[key], {})
        if not same and row.get('status') in ('SAME', 'MOVED'):
            offsets[key], origin[key] = hex(int(next(iter(row['votes'])), 16)), 'WITNESS_' + row['status']
        else:
            offsets[key], origin[key] = fields[key], 'CARRIED_FROM_BASELINE'
    result.update(offsets=offsets, origin=origin)
    try:
        target = ImageBindings(target_path)
        target.getter = target.find_getter(int(offsets['camera_pointer'], 0))
        result.update(tables=target.tables, getter=target.getter, located=True)
    except AdapterError as error:
        target = None
        result.update(located=False, failure=error.code, detail=error.detail[:200])
    values = {'schema': '1', 'image_sha256': sha, 'read_contract': fields['read_contract']}
    values.update({k: offsets[k] if result['located'] else '0x0' for k in CAMERA_KEYS})
    values['runtime_read'] = fields['runtime_read'] if same else '0'
    profile = output / (sha + '.profile')
    profile.write_text(''.join(k + '=' + v + '\n' for k, v in values.items()), encoding='ascii', newline='\n')
    result.update(profile=str(profile.resolve()), approved=same,
                  scope='Offsets come from unanimous field witnesses when available, otherwise carried from the baseline; '
                        'the camera pointer must also have an RTTI getter. Field layout still needs live review.')
    return result


def read_review(path):
    entries = {}
    for number, line in enumerate(path.read_text(encoding='ascii').splitlines(), 1):
        body, _, reason = line.partition('#')
        if not body.strip():
            continue
        key, _, value = body.partition('=')
        key, value, reason = key.strip(), value.strip(), reason.strip()
        if not key or not value or not reason or key.startswith(('approve.', 'runtime_')) or key in entries:
            raise SystemExit('review line %d needs key=value # reason, no approvals, no duplicates' % number)
        entries[key] = dict(value=value, reason=reason)
    return entries


def apply_review(review, symbols, registry, field_values, field_sources):
    applied = []
    registry_path = pathlib.Path(registry['profile'])
    registry_lines = dict(line.split('=', 1) for line in registry_path.read_text(encoding='ascii').splitlines() if line)
    for key, entry in review.items():
        if key.startswith('field.'):
            field_values[key[6:]] = int(entry['value'], 0)
            field_sources[key[6:]] = 'REVIEWED'
        elif key in symbols['ordered']:
            symbols['ordered'][key] = entry['value']
        elif key in registry_lines:
            registry_lines[key] = entry['value']
        else:
            raise SystemExit('review key not in any profile: ' + key)
        applied.append(dict(key=key, **entry))
    registry_path.write_text(''.join(k + '=' + v + '\n' for k, v in registry_lines.items()), encoding='ascii', newline='\n')
    return applied


def accept(fixture, image, profile):
    if not fixture:
        return None
    p = subprocess.run([str(fixture), str(image), profile, '--accept'], capture_output=True, text=True)
    return dict(exit=p.returncode, stdout=p.stdout.splitlines())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=pathlib.Path, required=True)
    parser.add_argument('--baseline-image', type=pathlib.Path, default=ROOT.parent / 'hoi4.exe')
    parser.add_argument('--output-directory', type=pathlib.Path, required=True)
    parser.add_argument('--rescan', action='store_true', help='scan even when SHA matches the baseline')
    parser.add_argument('--symbols-fixture', type=pathlib.Path, help='compiled native_symbols_fixture.exe for --accept')
    parser.add_argument('--review', type=pathlib.Path, help='reviewed key=value # reason lines applied to candidates')
    args = parser.parse_args()
    base, target = Image(args.baseline_image), Image(args.image)
    same = base.sha == target.sha and not args.rescan
    args.output_directory.mkdir(parents=True, exist_ok=True)
    symbols = migrate_symbols(base, target, same, args.output_directory)
    registry = migrate_registry(base, target, same, args.output_directory)
    fields = field_report(base, target, dict(target_sha256=target.sha, symbols=symbols, registry=registry))
    reviewed = []
    if not same:
        values = {r['key']: int(next(iter(r['votes'])), 16) for r in fields['fields'] if r['status'] in ('SAME', 'MOVED')}
        sources = {k: 'UNANIMOUS_WITNESS' for k in values}
        if args.review:
            reviewed = apply_review(read_review(args.review), symbols, registry, values, sources)
        write_fields(symbols, values, sources=sources)
    camera = migrate_camera(base, args.image, target.sha, same, args.output_directory, fields)
    report = dict(baseline_sha256=base.sha, target_sha256=target.sha, approved=same,
                  symbols=symbols, registry=registry, camera=camera, fields=fields, reviewed=reviewed,
                  symbols_accept=accept(args.symbols_fixture, args.image, symbols['profile']))
    (args.output_directory / 'migration.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(
        target_sha256=target.sha, approved=same,
        symbols=dict(summary=symbols['summary'], incomplete_groups=symbols['incomplete_groups']),
        registry=dict(summary=registry['summary'], complete=registry['complete'],
                      static_token_count=registry['static_token_count']),
        camera=dict(located=camera['located'], failure=camera.get('failure'), origin=camera['origin']),
        fields=brief(fields), reviewed=[r['key'] for r in reviewed],
        symbols_accept=report['symbols_accept'] and report['symbols_accept']['stdout'][-1]), indent=2))


if __name__ == '__main__':
    main()
