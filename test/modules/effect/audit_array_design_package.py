import pathlib,sys,json,zipfile,xml.etree.ElementTree as ET
path=pathlib.Path(sys.argv[1]).resolve()
with zipfile.ZipFile(path) as z:
 names=set(z.namelist());ET.fromstring(z.read('src/plugin/plugin.vcxproj'))
 model='test/reports/20261012_variable64_transaction/array_design/protocol_model.html'
 present=model in names
 if present:assert b'<script id="protocol">' in z.read(model) and b'globalThis.A64=' in z.read(model)
 project=z.read('src/plugin/plugin.vcxproj');compiled=b'protocol_model' in project or b'array64' in project.lower()
 assert not compiled
 print(json.dumps({'package':str(path),'model_present':present,'game_model_compiled':compiled,'project_xml_valid':True,'exit':0}))
