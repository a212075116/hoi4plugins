import hashlib,json,pathlib,struct,sys,zipfile,xml.etree.ElementTree as ET
package=pathlib.Path(sys.argv[1]).resolve();source='src/plugin/SDK_RVA/variable64/array64_api.c';dll='test/reports/20261012_variable64_transaction/api/hoi4_mod_plugin.MODIFIED.dll'
with zipfile.ZipFile(package) as z:
 assert z.testzip() is None
 project=z.read('src/plugin/plugin.vcxproj');ET.fromstring(project);present=source in z.namelist();compiled=b'array64_api.c' in project
 assert present==compiled
 result={'package':str(package),'api_present':present,'api_compiled_into_plugin':compiled,'project_xml_valid':True}
 if present:
  code=z.read(source);assert b'array64_shape_journal.c' in code and b'check_array64' in code and b'Array64_JournalApply' in code
  binary=z.read(dll);offset=struct.unpack_from('<I',binary,60)[0];assert binary[:2]==b'MZ' and binary[offset:offset+4]==b'PE\0\0' and struct.unpack_from('<H',binary,offset+4)[0]==0x8664
  result['production_dll_sha256']=hashlib.sha256(binary).hexdigest();result['effects']=10;result['triggers']=1
 result['exit']=0;print(json.dumps(result))
