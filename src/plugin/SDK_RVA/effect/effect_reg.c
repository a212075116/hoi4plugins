#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "effect_reg.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void* (__fastcall *AddTokenFn)(void* outId, void* view, void* a3);
typedef void* (__fastcall *StabFactoryFn)(void);
typedef void* (__fastcall *RegEntryFn)(void* map, int id, void* entry);
typedef void* (__fastcall *GetParamFn)(void* a1, void* out, void* ctx, long long a4, unsigned char a5);
typedef void* (__fastcall *PackKeyFn)(void* out, const char* key, void* params, int count);
typedef void* (__fastcall *FormatFn)(void* out, void* ctx, void* packed);
typedef void  (__fastcall *ParamCtorFn)(void* p);
typedef void  (__fastcall *ParamDtorFn)(void* p);
typedef void  (__fastcall *StrAppendFn)(void* str, unsigned long long n);
typedef char  assert_ptr64[(sizeof(void*) == 8) ? 1 : -1];

static int g_registeredCount = 0;
static char g_pendingTip[192];
static const char* g_pendingLoc = NULL;
static int g_hasPendingTip = 0;

void Effect_FlushPendingTooltip(void)
{
    if (g_hasPendingTip) {
        Plugin_Log("[efftip] loc=%s text=[%s]", g_pendingLoc ? g_pendingLoc : "?",
                   g_pendingTip);
        g_hasPendingTip = 0;
    }
}

void Effect_FlushPendingTooltip(void);

static unsigned char* Img(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

int Effect_RegistryReady(void)
{
    unsigned char* img = Img();
    if (img == NULL) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_LEXER_INIT, 2)) return 0;
    if (img[RVA_LEXER_INIT] == 0) return 0;
    if (img[RVA_LEXER_SYNC] == 0) return 0;
    return 1;
}

static int AddToken(const char* name, int* outId)
{
    struct NameView { const char* data; unsigned long long len; } view;
    unsigned char* img = Img();
    AddTokenFn fn;
    int id = 0;
    unsigned long long n = 0;

    if (img == NULL || name == NULL || outId == NULL) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_ADD_TOKEN, 16)) return 0;
    while (name[n] != 0) ++n;
    if (n == 0) return 0;

    view.data = name;
    view.len  = n;
    fn = (AddTokenFn)(img + RVA_ADD_TOKEN);
    fn(&id, &view, NULL);
    *outId = id;
    return id != 0;
}

void* Effect_NewInstance(void* vt)
{
    unsigned char* img = Img();
    StabFactoryFn make;
    void* inst;

    if (img == NULL || vt == NULL) return NULL;
    if (!ConsoleCmd_IsReadable(img + RVA_STAB_FACTORY, 16)) return NULL;
    make = (StabFactoryFn)(img + RVA_STAB_FACTORY);
    inst = make();
    if (inst != NULL) *(void**)inst = vt;
    return inst;
}

float Effect_ParamFloat(void* self, void* ctx)
{
    unsigned char* img = Img();
    long long fixed = 0;

    if (img == NULL || self == NULL) return 0.0f;
    if (!ConsoleCmd_IsReadable(img + RVA_EFF_GETPARAM, 16)) return 0.0f;
    ((GetParamFn)(img + RVA_EFF_GETPARAM))((unsigned char*)self + 0x58, &fixed, ctx, 0, 0);
    return (float)((double)fixed / EFF_FIXED_SCALE);
}

void Effect_SetParamFixed(void* self, double value)
{
    unsigned char* p = (unsigned char*)self;
    if (self == NULL) return;
    if (!ConsoleCmd_IsReadable(p + 0x98, 8)) return;
    *(long long*)(p + 0x98) = (long long)(value * EFF_FIXED_SCALE);
}

void* Effect_BuildTooltip(void* self, void* out, void* ctx, const char* locKey)
{
    unsigned char* img = Img();
    unsigned char paramDesc[EFF_PARAMDESC_SIZE];
    unsigned char packed[32];
    unsigned char fin[32];
    unsigned long long sz;
    unsigned long long cap;
    unsigned char* src;
    unsigned char* dst;
    unsigned long long i;

    if (img == NULL || out == NULL) return out;
    if (locKey == NULL) locKey = "";
    if (!ConsoleCmd_IsReadable(img + RVA_EFF_PACKKEY, 16)) return out;

    memset(paramDesc, 0, sizeof(paramDesc));
    memset(packed, 0, sizeof(packed));
    memset(fin, 0, sizeof(fin));

    {
        long long fixed = 0;
        ((GetParamFn)(img + RVA_EFF_GETPARAM))((unsigned char*)self + 0x58, &fixed, ctx, 0, 0);
        ((ParamCtorFn)(img + RVA_EFF_PARAM_CTOR))(paramDesc);
        *(int*)(paramDesc + 0x00) = 9;
        *(void**)(paramDesc + 0x08) = (void*)(img + RVA_EFF_PARAM_TAG);
        *(long long*)(paramDesc + 0x50) = fixed;
        ((PackKeyFn)(img + RVA_EFF_PACKKEY))(packed, locKey, paramDesc, 1);
        ((ParamDtorFn)(img + RVA_EFF_PARAM_DTOR))(paramDesc);
    }

    ((FormatFn)(img + RVA_EFF_FORMAT))(fin, ctx, packed);

    sz = *(unsigned long long*)(fin + 0x10);
    cap = *(unsigned long long*)(fin + 0x18);
    src = (cap <= EFF_SSO_MAX) ? fin : *(unsigned char**)fin;

    *(unsigned long long*)((unsigned char*)out + 0x10) = 0;
    *(unsigned long long*)((unsigned char*)out + 0x18) = 0;
    *(unsigned long long*)out = 0;
    *((unsigned char*)out + 0x18) = EFF_SSO_MAX;
    *(unsigned char*)out = 0;

    if (sz > 0 && sz < 400 && ConsoleCmd_IsReadable(src, (size_t)sz)) {
        ((StrAppendFn)(img + RVA_EFF_STR_APPEND))(out, sz);
        cap = *(unsigned long long*)((unsigned char*)out + 0x18);
        dst = (cap <= EFF_SSO_MAX) ? (unsigned char*)out : *(unsigned char**)out;
        for (i = 0; i < sz; ++i) dst[i] = src[i];
        dst[sz] = 0;
        *(unsigned long long*)((unsigned char*)out + 0x10) = sz;
    }

    {
        unsigned long long osz = *(unsigned long long*)((unsigned char*)out + 0x10);
        unsigned long long ocap = *(unsigned long long*)((unsigned char*)out + 0x18);
        unsigned char* op = (ocap <= EFF_SSO_MAX)
                            ? (unsigned char*)out : *(unsigned char**)out;
        if (g_hasPendingTip == 0 && osz > 0 && osz < 150 &&
            ConsoleCmd_IsReadable(op, (size_t)osz + 1)) {
            unsigned long long j;
            int n = 0;
            for (j = 0; j < osz && n < 180; ++j) {
                char ch = (char)op[j];
                g_pendingTip[n++] = (ch == 10 || ch == 13) ? ' ' : ch;
            }
            g_pendingTip[n] = 0;
            g_pendingLoc = locKey;
            g_hasPendingTip = 1;
        }
    }

    return out;
}

int Effect_RegistryRegister(EffectDef* def)
{
    unsigned char* img;
    RegEntryFn reg;
    void* map;
    int id = 0;
    int i;

    if (def == NULL) return 0;
    if (def->state == EFF_STATE_OK) return 1;
    if (def->name == NULL || def->desc == NULL || def->exec == NULL) {
        def->state = EFF_STATE_FAILED;
        return 0;
    }

    img = Img();
    if (img == NULL) return 0;
    if (!Effect_RegistryReady()) return 0;

    if (!AddToken(def->name, &id)) {
        Plugin_Log("[eff] AddToken failed: %s", def->name);
        def->state = EFF_STATE_FAILED;
        return 0;
    }

    for (i = 0; i < EFF_VT_SLOTS; ++i) {
        def->vt[i] = *(void**)(img + RVA_STAB_VT + (unsigned)i * 8);
    }
    def->vt[EFF_VT_EXEC / 8]    = (void*)def->exec;
    def->vt[EFF_VT_TOOLTIP / 8] = (void*)def->tooltip;

    def->entryVt[0] = *(void**)(img + RVA_STAB_ENTRY_VT);
    def->entryVt[1] = (void*)def->factory;

    *(void**)def->entry = def->entryVt;
    *(const char**)(def->entry + 8) = def->desc;

    map = *(void**)(img + RVA_EFFECT_MAP);
    if (map == NULL) {
        Plugin_Log("[eff] _EffectEntries is NULL");
        def->state = EFF_STATE_FAILED;
        return 0;
    }
    reg = (RegEntryFn)(img + RVA_REG_ENTRY);
    reg(map, id, def->entry);

    def->tokenId = id;
    def->state = EFF_STATE_OK;
    ++g_registeredCount;
    Plugin_Log("[eff] + %s  tokenId=%d  loc=%s  exec=%p",
               def->name, id, def->locKey, (void*)def->exec);
    return 1;
}

int Effect_RegistryRegisterAll(EffectDef** defs, int count)
{
    int i;
    int ok = 0;

    if (defs == NULL || count <= 0) return 0;
    if (!Effect_RegistryReady()) return 0;

    for (i = 0; i < count; ++i) {
        if (defs[i] == NULL) continue;
        if (Effect_RegistryRegister(defs[i])) ++ok;
    }
    Plugin_Log("[eff] registry: %d/%d registered", ok, count);
    return ok;
}

int Effect_RegistryRegisteredCount(void)
{
    return g_registeredCount;
}
