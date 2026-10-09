# -*- coding: utf-8 -*-
"""把紧凑的虚表索引 JSON 重新格式化为人类可读形式。

保留原文件结构不变, 只改排版:
  - 顶层字段一行一个
  - 每个虚表一个对象, 字段缩进两格
  - slots 数组内联成一行 (否则 49 万元素会把文件撑到 20MB+ 且更难看)
  - 同时给出 rva_hex / slots_hex, 便于和 IDA 里看到的十六进制对照

用法: python reformat_vt_index.py <输入.json> <输出.json>
"""
import io, json, sys


def fmt_entry(v, ind='    '):
    rva = v['rva']
    slots = v.get('slots') or []
    # 十六进制必须加引号: JSON 不接受 0x 前缀的数字字面量
    slots_hex = '[' + ', '.join('"0x%X"' % s for s in slots) + ']'
    slots_dec = '[' + ', '.join(str(s) for s in slots) + ']'
    lines = [
        ind + '{',
        ind + '  "rva": %d,' % rva,
        ind + '  "rva_hex": "0x%X",' % rva,
        ind + '  "sym": %s,' % json.dumps(v.get('sym'), ensure_ascii=False),
        ind + '  "cls": %s,' % json.dumps(v.get('cls'), ensure_ascii=False),
        ind + '  "nbase": %s,' % json.dumps(v.get('nbase')),
        ind + '  "n": %d,' % v.get('n', len(slots)),
        ind + '  "slots": %s,' % slots_dec,
        ind + '  "slots_hex": %s' % slots_hex,
        ind + '}',
    ]
    return '\n'.join(lines)


def main():
    inp, outp = sys.argv[1], sys.argv[2]
    d = json.load(io.open(inp, encoding='utf-8'))
    vt = d.get('vt') or []

    out = []
    out.append('{')
    out.append('  "imagebase": %d,' % d['imagebase'])
    out.append('  "imagebase_hex": "0x%X",' % d['imagebase'])
    out.append('  "game": %s,' % json.dumps(d.get('game'), ensure_ascii=False))
    out.append('  "note": %s,' % json.dumps(d.get('note'), ensure_ascii=False))
    out.append('  "count": %d,' % d['count'])
    out.append('  "rtti_ok": %d,' % d['rtti_ok'])
    out.append('  "slot_total": %d,' % sum(len(v.get('slots') or []) for v in vt))
    out.append('  "vt": [')
    for i, v in enumerate(vt):
        tail = ',' if i + 1 < len(vt) else ''
        out.append(fmt_entry(v) + tail)
    out.append('  ]')
    out.append('}')
    text = '\n'.join(out) + '\n'

    # 先自校验: 生成的文本必须能被 json 重新解析, 且条数与槽数与原文件一致。
    # 不通过就绝不写出去 (上一次就是因为没校验, 把不合法的 JSON 覆盖了原文件)。
    back = json.loads(text)
    assert back['count'] == d['count'], 'count 不一致'
    assert back['rtti_ok'] == d['rtti_ok'], 'rtti_ok 不一致'
    assert len(back['vt']) == len(vt), 'vt 条数不一致'
    for a, b in zip(vt, back['vt']):
        assert a['rva'] == b['rva'], 'rva 不一致'
        assert a['slots'] == b['slots'], 'slots 不一致'
        assert a['sym'] == b['sym'] and a.get('cls') == b.get('cls'), '名字不一致'

    io.open(outp, 'w', encoding='utf-8', newline='\n').write(text)
    print('写出 %s' % outp)
    print('  大小 %.2f MB, 行数 %d' % (len(text) / 1024 / 1024, text.count(chr(10))))
    print('  自校验通过: %d 个虚表 / %d 个槽 与原文件逐条一致'
          % (back['count'], sum(len(v['slots']) for v in back['vt'])))


if __name__ == '__main__':
    main()
