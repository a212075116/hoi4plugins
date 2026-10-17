#define RVA_VARTEXT_HANDLER     NativeAdapter_Symbol(NSY_VARTEXT_HANDLER)
#define VAR64_LANG_NAME_MAX     160u

typedef void* (__fastcall *Var64VarTextHandlerFn)(void* ctx, const char* text,
                                                  const char* textEnd, void* out, int depth);

static Var64VarTextHandlerFn g_var64OrigVarTextHandler = NULL;
static int Var64_LangResolveSlotValue(void* ctx, const char* name, long long* outValue);
static void Var64_LangAppendText(void* out, const char* text, int len);

static void Var64_CopyVarPath(const char* text, const char* textEnd, char* dst, int dstSize)
{
    int n = 0;
    const char* p;

    if (dst == NULL || dstSize <= 1) return;
    dst[0] = 0;
    if (text == NULL || textEnd == NULL) return;
    for (p = text; p < textEnd && *p != 0 && *p != '|' && n < dstSize - 1; ++p) dst[n++] = *p;
    dst[n] = 0;
}

static void* __fastcall Var64_VarTextBridgeDetour(void* ctx, const char* text,
                                                   const char* textEnd, void* out, int depth)
{
    char name[VAR64_LANG_NAME_MAX];
    char hiName[VAR64_LANG_NAME_MAX + 8];
    char fracName[VAR64_LANG_NAME_MAX + 8];
    char formatted[VAR64_FMT_TEXT_MAX];
    Var64TextFormat fmt;
    const char* spec = NULL;
    const char* p;
    long long loSlot = 0;
    long long hiSlot = 0;
    long long fracSlot = 0;
    long long vInt;
    long long vFrac;
    size_t n;

    if (g_var64OrigVarTextHandler == NULL) return NULL;
    if (ctx == NULL || text == NULL || textEnd == NULL || textEnd <= text
        || out == NULL || depth > 0) {
        return g_var64OrigVarTextHandler(ctx, text, textEnd, out, depth);
    }

    Var64_CopyVarPath(text, textEnd, name, sizeof(name));
    n = strlen(name);
    if (n == 0 || n > VAR64_NAME_LIMIT) {
        return g_var64OrigVarTextHandler(ctx, text, textEnd, out, depth);
    }
    memcpy(hiName, name, n);
    memcpy(hiName + n, VAR64_HIGH_SUFFIX, sizeof(VAR64_HIGH_SUFFIX));
    memcpy(fracName, name, n);
    memcpy(fracName + n, VAR64_FRAC_SUFFIX, sizeof(VAR64_FRAC_SUFFIX));
    if (!Var64_LangResolveSlotValue(ctx, fracName, &fracSlot)
        || fracSlot <= 0 || fracSlot >= 200000LL) {
        return g_var64OrigVarTextHandler(ctx, text, textEnd, out, depth);
    }
    if (!Var64_LangResolveSlotValue(ctx, name, &loSlot)
        || !Var64_LangResolveSlotValue(ctx, hiName, &hiSlot)) {
        return g_var64OrigVarTextHandler(ctx, text, textEnd, out, depth);
    }

    for (p = text; p < textEnd; ++p) {
        if (*p == '|') { spec = p + 1; break; }
    }
    Var64_ParseTextFormat(spec, textEnd, &fmt);

    vInt = ((long long)(int)hiSlot << 32) | (long long)(unsigned int)(int)loSlot;
    vFrac = fracSlot - VAR64_FRAC_BIAS;
    Var64_BuildFormattedText(&fmt, vInt, vFrac, formatted, sizeof(formatted));
    Var64_LangAppendText(out, formatted, (int)strlen(formatted));
    Plugin_Log("[v64lang] [%s] int=%lld frac=%lld -> [%s]", name, vInt, vFrac, formatted);
    return out;
}

typedef void (__fastcall *Var64CtxResolveFn)(void* ctx, void** outValue, void* nameField);

static int Var64_LangResolveSlotValue(void* ctx, const char* name, long long* outValue)
{
    unsigned char nameField[32];
    void* resolved = NULL;
    void* vtable;
    size_t n;

    if (ctx == NULL || name == NULL || outValue == NULL) return 0;
    n = strlen(name);
    if (n == 0 || n > VAR64_NAME_LIMIT) return 0;
    vtable = *(void**)ctx;
    if (!ConsoleCmd_IsReadable(vtable, 0x40)) return 0;

    memset(nameField, 0, sizeof(nameField));
    if (n <= VAR64_SSO_LIMIT) {
        memcpy(nameField, name, n + 1);
        *(unsigned long long*)(nameField + 24) = (unsigned long long)VAR64_SSO_LIMIT;
    } else {
        *(const char**)nameField = name;
        *(unsigned long long*)(nameField + 24) = (unsigned long long)n;
    }
    *(unsigned long long*)(nameField + 16) = (unsigned long long)n;

    ((Var64CtxResolveFn)(*(void**)((char*)vtable + 0x20)))(ctx, &resolved, nameField);
    if ((long long)(intptr_t)resolved % VAR64_SLOT_SCALE != 0) return 0;
    *outValue = (long long)(intptr_t)resolved / VAR64_SLOT_SCALE;
    return 1;
}

static void Var64_LangAppendText(void* out, const char* text, int len)
{
    CmdString* field = (CmdString*)out;
    unsigned char* img;

    if (field == NULL || text == NULL || len <= 0) return;
    if (!ConsoleCmd_IsReadable(field, 32)) return;
    img = Var64_Image();
    if (img == NULL) return;
    if (!ConsoleCmd_IsReadable(img + RVA_STRING_APPEND, 16)) return;
    ((Var64StringAppendFn)(img + RVA_STRING_APPEND))((void**)field, text, (size_t)len);
}

void Var64_InstallLanguageBridge(void)
{
    unsigned char* img = Var64_Image();
    void* orig;

    if (g_var64OrigVarTextHandler != NULL) return;
    if (img == NULL) return;
    if (!ConsoleCmd_IsReadable(img + RVA_VARTEXT_HANDLER, 16)) {
        Plugin_Log("[v64lang] handler address unreadable");
        return;
    }
    orig = (void*)g_var64OrigVarTextHandler;
    if (!InlineHook_InstallInto(img + RVA_VARTEXT_HANDLER, (void*)Var64_VarTextBridgeDetour, (void**)&g_var64OrigVarTextHandler)) {
        g_var64OrigVarTextHandler = (Var64VarTextHandlerFn)orig;
        Plugin_Log("[v64lang] var text hook install failed");
        return;
    }
    Plugin_Log("[v64lang] var text hook installed, orig=%p", (void*)g_var64OrigVarTextHandler);
}

