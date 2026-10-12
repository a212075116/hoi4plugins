import hashlib, json, pathlib, subprocess, sys, tempfile, zipfile, xml.etree.ElementTree as ET
package=pathlib.Path(sys.argv[1]).resolve()
source='src/plugin/SDK_RVA/variable64/native_array_readonly.c'
driver='test/modules/effect/test_array_readonly_native.py'
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    project=z.read('src/plugin/plugin.vcxproj');ET.fromstring(project)
    present=source in z.namelist()
    compiled=b'native_array_readonly.c' in project
    assert not compiled
    result={'package':str(package),'backend_present':present,'backend_compiled_into_plugin':compiled,'project_xml_valid':True}
    if present:
        with tempfile.TemporaryDirectory(prefix='hoi4_array_readonly_') as temp:
            root=pathlib.Path(temp);c=root/'backend.c';d=root/'verify.py'
            c.write_bytes(z.read(source));d.write_bytes(z.read(driver))
            p=subprocess.run([sys.executable,str(d),str(c),str(root/'native')],capture_output=True)
            assert p.returncode==0,p.stderr
            native=json.loads((root/'native/result.json').read_text(encoding='utf-8'))
            assert native['exit']==0 and 'checks=4123 passed=4123 failed=0' in native['stdout']
            result.update({'backend_sha256':hashlib.sha256(c.read_bytes()).hexdigest(),'native_stdout':native['stdout'],'native_stderr':native['stderr'],'native_exit':native['exit']})
    result['exit']=0
    print(json.dumps(result,ensure_ascii=True))
