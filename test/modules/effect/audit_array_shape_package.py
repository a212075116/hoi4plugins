import hashlib,json,pathlib,subprocess,sys,tempfile,zipfile,xml.etree.ElementTree as ET
package=pathlib.Path(sys.argv[1]).resolve();source='src/plugin/SDK_RVA/variable64/array64_shape_transaction.c';base='src/plugin/SDK_RVA/variable64/native_array_readonly.c';driver='test/modules/effect/test_array64_shape_native.py'
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    project=z.read('src/plugin/plugin.vcxproj');ET.fromstring(project);present=source in z.namelist();compiled=b'array64_shape_transaction.c' in project
    assert not compiled
    result={'package':str(package),'shape_present':present,'shape_compiled_into_plugin':compiled,'project_xml_valid':True}
    if present:
        with tempfile.TemporaryDirectory(prefix='hoi4_array_group_') as temp:
            root=pathlib.Path(temp)
            for name in [source,base,driver,'src/plugin/SDK_RVA/variable64/array64_ownership_gate.c','test/modules/effect/test_array64_ownership_native.py','src/plugin/SDK_RVA/variable64/array64_durable_snapshot.c','src/plugin/SDK_RVA/variable64/array64_recovery.c','src/plugin/SDK_RVA/variable64/array64_existing_transaction.c','test/modules/effect/test_array64_transaction_native.py','src/plugin/SDK_RVA/variable64/array64_group_readonly.c','test/modules/effect/test_array64_group_native.py']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
            p=subprocess.run([sys.executable,str(root/driver),str(root/'native')],capture_output=True);assert p.returncode==0,p.stderr
            native=json.loads((root/'native/result.json').read_text(encoding='utf-8'))
            assert native['exit']==0 and 'checks=287 passed=287 failed=0' in native['stdout']
            result.update({'source_sha256':hashlib.sha256(z.read(source)).hexdigest(),'native_stdout':native['stdout'],'native_stderr':native['stderr'],'native_exit':native['exit']})
    result['exit']=0;print(json.dumps(result,ensure_ascii=True))
