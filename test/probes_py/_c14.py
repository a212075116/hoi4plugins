import sys, json
sys.path.insert(0, 'flirt')
from idalib_cli import send
r = send({'op':'decompile','ea':'0x140241DF0','lines':130})
t = r.get('text') if r.get('ok') else ''
lines = t.split(chr(10))
# 只打印含 a2 或 Usage 的行(看参数怎么解析), 附上下文
for i, ln in enumerate(lines):
    if ('a2' in ln) or ('Usage' in ln) or ('count' in ln.lower() and 'a2' in lines[max(0,i-2):i+2].__str__()):
        print('%4d| %s' % (i, ln))
