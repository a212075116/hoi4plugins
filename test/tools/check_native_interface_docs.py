import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
folder = root / 'ai_docs/07_逆向能力'
interface = (folder/'有没有官方接口.md').read_text(encoding='utf-8')
rtti = (folder/'虚表与RTTI.md').read_text(encoding='utf-8')
findings = []
if '**没有。** HOI4' in interface or '尚未建立' not in interface:
    findings.append('Unqualified absence assertion; public contract scope not recorded')
if '标准 MSVC x64 RTTI 用 8 字节绝对地址' in rtti or '常规 ABI' not in rtti:
    findings.append('Incorrect x64 RTTI field-width claim; normal image-relative ABI not recorded')
print(json.dumps(dict(checks=2, failed=len(findings), findings=findings), ensure_ascii=True))
raise SystemExit(bool(findings))
