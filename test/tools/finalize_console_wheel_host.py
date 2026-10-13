import hashlib, json, pathlib, shutil, subprocess, sys, zipfile

R = pathlib.Path(__file__).resolve().parents[2]
T = R / 'test/reports/20261012_variable64_transaction'
D = T / 'console_wheel_host'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def run(c, cwd=R):
    p = subprocess.run(c, cwd=cwd, capture_output=True)
    return dict(command=c, cwd=str(cwd), stdout=p.stdout.decode('utf-8', errors='replace'), stderr=p.stderr.decode('utf-8', errors='replace'), exit=p.returncode)
def save(p, v): p.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding='utf-8')
def pack(p, names):
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in sorted(names): z.write(R / n, n)
build = run(['C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe', 'hoi4plugins.sln', '/p:Configuration=Release', '/p:Platform=x64', '/v:minimal', '/nologo'])
save(D / 'build.json', build); assert build['exit'] == 0
selftest = run([str(R / 'build/Release/hoi4_debug_console.exe'), '--self-test'])
save(D / 'selftest.json', selftest); assert selftest['exit'] == 0
for phase, code in [('BASELINE', 1), ('MODIFIED', 0), ('ROLLBACK', 1)]: assert read(D / (phase + '.json'))['result']['exit'] == code
assert read(D / 'BASELINE.json')['result']['stdout'] == read(D / 'ROLLBACK.json')['result']['stdout']
assert sha(D / 'main.BASELINE.cpp') == sha(D / 'restored.console-wheel-host.cpp')
shutil.copyfile(R / 'src/debug_console/main.cpp', D / 'main.MODIFIED.cpp')
shutil.copyfile(R / 'build/Release/hoi4_debug_console.exe', D / 'hoi4_debug_console.MODIFIED.exe')
shutil.copyfile(D / 'hoi4_debug_console.MODIFIED.exe', D / 'restored.console-wheel-host.exe')
restore = run(['C:/Program Files/Git/bin/bash.exe', str(T / 'ROLLBACK.sh'), str(D / 'restored.console-wheel-host.exe')]); assert restore['exit'] == 0
assert sha(D / 'restored.console-wheel-host.exe') == sha(D / 'hoi4_debug_console.BASELINE.exe')
manifest = read(T / 'CURRENT_BUILD.json')
manifest.update(helper_archive=(D / 'hoi4_debug_console.MODIFIED.exe').relative_to(R).as_posix(), helper_sha256=sha(D / 'hoi4_debug_console.MODIFIED.exe'), reason='Mouse capture disabled to let terminal host own scrollback; real ConPTY input mode and VT mouse-report checks pass; user physical wheel confirmation pending, prior attempt ineffective')
assert sha(R.parent / 'hoi4_debug_console.exe') == manifest['helper_sha256']
save(T / 'CURRENT_BUILD.json', manifest)
with zipfile.ZipFile(T / 'MODIFIED_FILE.zip') as z: names = set(z.namelist())
names.update(p.relative_to(R).as_posix() for folder in ['src', 'ai_docs', 'test/docs', 'test/modules/console'] for p in (R / folder).rglob('*') if p.is_file() and 'build' not in p.parts and '__pycache__' not in p.parts)
names.add('test/tools/finalize_console_wheel_host.py')
names.update(p.relative_to(R).as_posix() for p in D.iterdir() if p.is_file() and p.suffix in ['.json', '.cpp', '.h', '.exe'])
pack(T / 'MODIFIED_FILE.zip', names)
shutil.copyfile(T / 'BASELINE.zip', T / 'before/MODIFIED_FILE.zip'); shutil.copyfile(T / 'MODIFIED_FILE.zip', T / 'after/MODIFIED_FILE.zip')
diff = run(['git', 'diff', '--no-index', '--binary', '--', 'before/MODIFIED_FILE.zip', 'after/MODIFIED_FILE.zip'], T); assert diff['exit'] == 1
(T / 'DIFF_FILE.patch').write_text(diff['stdout'], encoding='utf-8', newline='\n')
shutil.copyfile(T / 'BASELINE.zip', T / 'reconstruct/MODIFIED_FILE.zip')
apply = run(['git', 'apply', '-p2', str(T / 'DIFF_FILE.patch')], T / 'reconstruct'); assert apply['exit'] == 0
assert sha(T / 'reconstruct/MODIFIED_FILE.zip') == sha(T / 'MODIFIED_FILE.zip')
shutil.copyfile(T / 'MODIFIED_FILE.zip', T / 'restored.zip')
full = run(['C:/Program Files/Git/bin/bash.exe', str(T / 'ROLLBACK.sh'), str(T / 'restored.zip')]); assert full['exit'] == 0 and sha(T / 'restored.zip') == sha(T / 'BASELINE.zip')
audits = {}
for key, c in [('package', [sys.executable, str(R / 'test/modules/console/audit_external_console_package.py'), str(T / 'MODIFIED_FILE.zip')]), ('docs', [sys.executable, str(R / 'test/tools/audit_project_docs.py'), '--package', str(T / 'MODIFIED_FILE.zip')])]:
    audits[key] = run(c); assert audits[key]['exit'] == 0, audits[key]
with zipfile.ZipFile(T / 'MODIFIED_FILE.zip') as z:
    assert z.testzip() is None
    for n in names: assert z.read(n) == (R / n).read_bytes(), n
v = read(T / 'VERIFICATION.txt')
v['console_wheel_host_extension'] = dict(target=str(R / 'src/debug_console/main.cpp'), changed_branches=['interactive startup SetConsoleMode clears ENABLE_MOUSE_INPUT'], three_state={p: read(D / (p + '.json')) for p in ['BASELINE', 'MODIFIED', 'ROLLBACK']}, build=build, selftest=selftest, binary_restore=restore, restored_helper_sha256=sha(D / 'restored.console-wheel-host.exe'), restored_source_sha256=sha(D / 'restored.console-wheel-host.cpp'), patch_reconstruction=apply, full_restore=full, audits=audits, deployment=read(D / 'deployment.json'), physical_mouse_tested=False, previous_user_confirmation='Prior wheel attempt remains ineffective in real user interaction', stdio_handle_attempt_error=read(D / 'stdio_handle_attempt_error.json'), prior_45minute_soak_rerun=False, compile_attempt_error=read(D / 'compile_attempt_error.json'))
v['latest_modified_hashes'] = {n: sha(R / n) for n in names}; save(T / 'VERIFICATION.txt', v)
c = read(T / 'checkpoint.json'); c.update(ACTIVE_OBJECT=str(R / 'src/debug_console/main.cpp'), LAST_CONFIRMED_RESULT='Host wheel routing BASELINE 3/5 plus VT mouse enabled exit1, MODIFIED 5/5 plus VT mouse disabled exit0, ROLLBACK baseline behavior exit1. Prior user GUI failure recorded; physical confirmation still pending.', NEXT_EXECUTABLE_ACTION='User physical wheel feedback; preserve prior stress evidence, do not claim modeled viewport test is real GUI or repeat completed soak unnecessarily.', current_build=manifest); save(T / 'checkpoint.json', c)
roles = {}
for n in ['MODIFIED_FILE.zip', 'DIFF_FILE.patch', 'VERIFICATION.txt', 'ROLLBACK.sh']:
    p = T / n; b = p.read_bytes(); roles[n] = dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest()); print(json.dumps(roles[n], ensure_ascii=False))
save(T / 'artifact_hashes.json', roles)
print('HOST_WHEEL_TRANSACTION_VERIFIED')
