import argparse,json,pathlib,sys,xml.etree.ElementTree as ET,zipfile
ap=argparse.ArgumentParser();ap.add_argument('snapshot');args=ap.parse_args()
with zipfile.ZipFile(pathlib.Path(args.snapshot)) as z:
    project=ET.fromstring(z.read('src/plugin/plugin.vcxproj'))
    main=z.read('src/plugin/plugin_main.c').decode('utf-8-sig')
    compile_files=[e.attrib['Include'] for e in project.findall('.//{*}ClCompile') if 'Include' in e.attrib]
    integrated='SDK_RVA\\trigger\\trigger_reg.c' in compile_files and 'SDK_RVA\\trigger\\trigger_demo.c' in compile_files and 'TriggerDemo_Register();' in main
    print(json.dumps({'trigger_startup_integrated':integrated,'registry_sources':[p for p in compile_files if '\\trigger\\' in p]},ensure_ascii=False))
    raise SystemExit(0 if integrated else 1)
