import io, sys

REPL = [
    ("[引导器] %s 发现插件 %s", "[carrier] %s found plugin %s"),
    ("[情况二] 插件加载成功: %s", "[case2] plugin loaded: %s"),
    ("         base=%p   模块名=%s", "         base=%p   name=%s"),
    ("[引导器] 加载失败: %s  GetLastError=%lu", "[carrier] load failed: %s  err=%lu"),
    ("[引导器] 无法取得主模块路径, GetLastError=%lu", "[carrier] no main module path, err=%lu"),
    ("[引导器] 主模块路径异常: %s", "[carrier] bad main module path: %s"),
    ("[引导器] 游戏根目录 = %s", "[carrier] game root = %s"),
    ('TryLoadPlugin(dir, "游戏根目录")', 'TryLoadPlugin(dir, "gameroot")'),
    ("[引导器] 加载完成: 成功 %d 个插件", "[carrier] done: %d plugin(s) loaded"),
    ("[情况一] 游戏根目录的 ", "[case1] game-root "),
    (".dll 已被游戏加载", ".dll loaded by game"),
    ("         主模块=%p  (%s)", "         main=%p (%s)"),
    ("         引导器自身路径 = %s", "         carrier path = %s"),
    ("[引导器] 另一个载体持有锁，仍继续", "[carrier] another carrier holds lock"),
    ("[cmdreg] 跳过: name 或 handler 为空", "[cmdreg] skip: name or handler is null"),
    ("[cmdreg] 跳过 %s: argCount=%d 超出 [0,%d]", "[cmdreg] skip %s: argCount=%d out of [0,%d]"),
    ("[cmdreg] 跳过 %s: %s 长 %llu 超过 SSO 上限 %d", "[cmdreg] skip %s: %s len %llu > SSO max %d"),
    ("[cmdreg] 跳过 %s: argNames[%d] 长 %llu 超过 SSO 上限 %d", "[cmdreg] skip %s: argNames[%d] len %llu > SSO max %d"),
    ("[cmdreg] 一次最多注册 %d 条, 收到 %d", "[cmdreg] max %d per call, got %d"),
    ("[cmdreg] 取不到主模块基址", "[cmdreg] no main module base"),
    ("[cmdreg] 命令管理器槽 %p 不可读", "[cmdreg] manager slot %p unreadable"),
    ("[cmdreg] 管理器尚未建立, 调用初始化 %p", "[cmdreg] manager not built, init %p"),
    ("[cmdreg] 初始化后管理器仍为空, 放弃", "[cmdreg] manager still null, abort"),
    ("[cmdreg] 管理器 = %p  (注册前 count=%d capacity=%d)", "[cmdreg] manager = %p (count=%d capacity=%d)"),
    ("[cmdreg] 调用合并函数 %p, 提交 %d 条", "[cmdreg] merge %p with %d entry(ies)"),
    ("[cmdreg] 完成: 注册后 count=%d", "[cmdreg] done: count=%d"),
    ("[cmdreg] 没有任何一条通过自检, 放弃", "[cmdreg] nothing passed checks, abort"),
]

def strip_comments(src):
    out = []
    i = 0
    n = len(src)
    state = 'code'
    while i < n:
        c = src[i]
        if state == 'code':
            if c == '/' and i + 1 < n and src[i+1] == '/':
                state = 'line'; i += 2; continue
            if c == '/' and i + 1 < n and src[i+1] == '*':
                state = 'block'; i += 2; continue
            if c == '"':
                state = 'str'; out.append(c); i += 1; continue
            if c == "'":
                state = 'chr'; out.append(c); i += 1; continue
            out.append(c); i += 1; continue
        if state == 'line':
            if c == '\n':
                state = 'code'; out.append(c)
            i += 1; continue
        if state == 'block':
            if c == '*' and i + 1 < n and src[i+1] == '/':
                state = 'code'; i += 2; continue
            if c == '\n':
                out.append(c)
            i += 1; continue
        if state == 'str':
            out.append(c)
            if c == '\\':
                if i + 1 < n: out.append(src[i+1]); i += 2; continue
            if c == '"': state = 'code'
            i += 1; continue
        if state == 'chr':
            out.append(c)
            if c == '\\':
                if i + 1 < n: out.append(src[i+1]); i += 2; continue
            if c == "'": state = 'code'
            i += 1; continue
    return ''.join(out)

def squeeze(text):
    res = []
    blank = 0
    for ln in text.split('\n'):
        s = ln.rstrip()
        if s.strip() == '':
            blank += 1
            if blank > 1: continue
        else:
            blank = 0
        res.append(s)
    return '\n'.join(res).strip() + '\n'

src_path, dst_path = sys.argv[1], sys.argv[2]
s = io.open(src_path, encoding='utf-8').read()
s = strip_comments(s)
for a, b in REPL:
    s = s.replace(a, b)
s = squeeze(s)
bad = [(i+1, l) for i, l in enumerate(s.split('\n')) if any(ord(ch) > 127 for ch in l)]
io.open(dst_path, 'w', encoding='utf-8', newline='\r\n').write(s)
print('%s -> %s' % (src_path.split('/')[-1], dst_path.split('/')[-1]))
if bad:
    print('  !! %d line(s) still non-ASCII' % len(bad))
    for ln, txt in bad[:12]:
        print('     %d| %s' % (ln, txt.strip()[:100]))
else:
    print('  OK all ASCII')
