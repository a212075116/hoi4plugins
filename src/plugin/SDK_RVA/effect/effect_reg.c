#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "carrier.h"
#include "../common/native_memory.h"
#include "../common/native_name_view.h"
#include "../common/native_string.h"
#include "effect_reg.h"

#include "../common/plugin_log.h"

typedef void* (__fastcall *AddTokenFn)(void* outId, void* view, void* a3);
typedef void* (__fastcall *StabFactoryFn)(void);
typedef void* (__fastcall *RegEntryFn)(void* map, int id, void* entry);
typedef void* (__fastcall *GetParamFn)(void* a1, void* out, void* ctx, long long a4, unsigned char a5);
typedef void* (__fastcall *PackKeyFn)(void* out, const char* key, void* params, int count);
typedef void* (__fastcall *FormatFn)(void* out, void* ctx, void* packed);
typedef void  (__fastcall *ParamCtorFn)(void* p);
typedef void  (__fastcall *ParamDtorFn)(void* p);
typedef void* (__fastcall *StrAppendFn)(void* str, const char* data, size_t n);
typedef char  assert_ptr64[(sizeof(void*) == 8) ? 1 : -1];

static int g_registeredEffectCount = 0;
static char g_pendingTooltipText[192];
static const char* g_pendingTooltipLocKey = NULL;
static int g_hasPendingTooltip = 0;

unsigned int __fastcall Effect_ScopeAny(void* self)
{
    (void)self;
    return 0;
}

void Effect_FlushPendingTooltip(void)
{
    if (g_hasPendingTooltip) {
        Plugin_Log("[efftip] loc=%s text=[%s]", g_pendingTooltipLocKey ? g_pendingTooltipLocKey : "?",
                   g_pendingTooltipText);
        g_hasPendingTooltip = 0;
    }
}

void Effect_FlushPendingTooltip(void);

static unsigned char* Effect_GetModuleBase(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

int Effect_RegistryReady(void)
{
    unsigned char* img = Effect_GetModuleBase();
    if (img == NULL || !NativeAdapter_RegistryReady()) return 0;
    if (!NativeMemory_IsReadable(img + NativeAdapter_RegistryRva(NS_LEXER_INIT), 2)) return 0;
    if (img[NativeAdapter_RegistryRva(NS_LEXER_INIT)] == 0) return 0;
    if (img[NativeAdapter_RegistryRva(NS_LEXER_SYNC)] == 0) return 0;
    return 1;
}

static int Effect_AddToken(const char* name, int* outId)
{
    NativeNameView view;
    unsigned char* img = Effect_GetModuleBase();
    AddTokenFn fn;
    int id = 0;
    unsigned long long n = 0;

    if (img == NULL || name == NULL || outId == NULL) return 0;
    if (!NativeMemory_IsReadable(img + NativeAdapter_RegistryRva(NS_ADD_TOKEN), 16)) return 0;
    while (name[n] != 0) ++n;
    if (n == 0) return 0;

    view.data = name;
    view.size  = n;
    fn = (AddTokenFn)(img + NativeAdapter_RegistryRva(NS_ADD_TOKEN));
    fn(&id, &view, NULL);
    *outId = id;
    return id != 0;
}

void* Effect_NewInstance(void* vt)
{
    unsigned char* img = Effect_GetModuleBase();
    StabFactoryFn make;
    NativeScriptTemplate t;
    void* inst;

    if (img == NULL || vt == NULL || !NativeAdapter_ScriptTemplate(0, &t)) return NULL;
    if (!NativeMemory_IsReadable(img + t.factory, 16)) return NULL;
    make = (StabFactoryFn)(img + t.factory);
    inst = make();
    if (inst != NULL) *(void**)inst = vt;
    return inst;
}

float Effect_ParamFloat(void* self, void* ctx)
{
    unsigned char* img = Effect_GetModuleBase();
    long long fixed = 0;

    if (img == NULL || self == NULL || !NativeAdapter_RegistryReady()) return 0.0f;
    if (!NativeMemory_IsReadable(img + NativeAdapter_RegistryRva(NS_PARAM_GET), 16)) return 0.0f;
    ((GetParamFn)(img + NativeAdapter_RegistryRva(NS_PARAM_GET)))((unsigned char*)self + 0x58, &fixed, ctx, 0, 0);
    return (float)((double)fixed / EFF_FIXED_SCALE);
}

void Effect_SetParamFixed(void* self, double value)
{
    unsigned char* p = (unsigned char*)self;
    if (self == NULL || !NativeAdapter_RegistryReady()) return;
    if (!NativeMemory_IsReadable(p + 0x98, 8)) return;
    *(long long*)(p + 0x98) = (long long)(value * EFF_FIXED_SCALE);
}

void* Effect_BuildTooltip(void* self, void* out, void* ctx, const char* locKey)
{
    unsigned char* img = Effect_GetModuleBase();
    unsigned char paramDesc[EFF_PARAMDESC_SIZE];
    unsigned char packed[32];
    unsigned char fin[32];
    unsigned long long sz;
    unsigned char* src;

    if (img == NULL || out == NULL || !NativeAdapter_RegistryReady()) return out;
    if (locKey == NULL) locKey = "";
    if (!NativeMemory_IsReadable(img + NativeAdapter_RegistryRva(NS_TEXT_PACK), 16)) return out;

    memset(paramDesc, 0, sizeof(paramDesc));
    memset(packed, 0, sizeof(packed));
    memset(fin, 0, sizeof(fin));

    {
        long long fixed = 0;
        ((GetParamFn)(img + NativeAdapter_RegistryRva(NS_PARAM_GET)))((unsigned char*)self + 0x58, &fixed, ctx, 0, 0);
        ((ParamCtorFn)(img + NativeAdapter_RegistryRva(NS_PARAM_CTOR)))(paramDesc);
        *(int*)(paramDesc + 0x00) = 9;
        *(void**)(paramDesc + 0x08) = (void*)(img + NativeAdapter_RegistryRva(NS_PARAM_TAG));
        *(long long*)(paramDesc + 0x50) = fixed;
        ((PackKeyFn)(img + NativeAdapter_RegistryRva(NS_TEXT_PACK)))(packed, locKey, paramDesc, 1);
        ((ParamDtorFn)(img + NativeAdapter_RegistryRva(NS_PARAM_DTOR)))(paramDesc);
    }

    ((FormatFn)(img + NativeAdapter_RegistryRva(NS_TEXT_FORMAT)))(fin, ctx, packed);

    sz = *(unsigned long long*)(fin + 0x10);
    src = (unsigned char*)NativeString_Data((const NativeString*)fin);

    *(unsigned long long*)((unsigned char*)out + 0x10) = 0;
    *(unsigned long long*)((unsigned char*)out + 0x18) = 0;
    *(unsigned long long*)out = 0;
    *((unsigned char*)out + 0x18) = EFF_SSO_MAX;
    *(unsigned char*)out = 0;

    if (sz > 0 && sz < 400 && NativeMemory_IsReadable(src, (size_t)sz)) {
        ((StrAppendFn)(img + NativeAdapter_RegistryRva(NS_TEXT_APPEND)))(out, (const char*)src, (size_t)sz);
    }

    {
        unsigned long long osz = *(unsigned long long*)((unsigned char*)out + 0x10);
        unsigned char* op = (unsigned char*)NativeString_Data((const NativeString*)out);
        if (g_hasPendingTooltip == 0 && osz > 0 && osz < 150 &&
            NativeMemory_IsReadable(op, (size_t)osz + 1)) {
            unsigned long long j;
            int n = 0;
            for (j = 0; j < osz && n < 180; ++j) {
                char ch = (char)op[j];
                g_pendingTooltipText[n++] = (ch == 10 || ch == 13) ? ' ' : ch;
            }
            g_pendingTooltipText[n] = 0;
            g_pendingTooltipLocKey = locKey;
            g_hasPendingTooltip = 1;
        }
    }

    return out;
}

int Effect_RegistryRegister(EffectDef* def)
{
    unsigned char* img;
    RegEntryFn reg;
    NativeScriptTemplate t;
    void* map;
    int id = 0;
    int i;

    if (def == NULL) return 0;
    if (def->state == EFF_STATE_OK) return 1;
    if (def->name == NULL || def->desc == NULL || def->exec == NULL) {
        def->state = EFF_STATE_FAILED;
        return 0;
    }

    img = Effect_GetModuleBase();
    if (img == NULL) return 0;
    if (!Effect_RegistryReady() || !NativeAdapter_ScriptTemplate(0, &t)) return 0;

    if (!Effect_AddToken(def->name, &id)) {
        Plugin_Log("[eff] Effect_AddToken failed: %s", def->name);
        def->state = EFF_STATE_FAILED;
        return 0;
    }

    for (i = 0; i < EFF_VT_SLOTS; ++i) {
        def->vt[i] = *(void**)(img + t.vt + (unsigned)i * 8);
    }
    def->vt[EFF_VT_EXEC / 8]    = (void*)def->exec;
    def->vt[EFF_VT_TOOLTIP / 8] = (void*)def->tooltip;
    if (def->supportedScopes != NULL) def->vt[19] = (void*)def->supportedScopes;

    def->entryVt[0] = def->entryParser!=NULL?def->entryParser:*(void**)(img + t.entryVt);
    def->entryVt[1] = (void*)def->factory;

    *(void**)def->entry = def->entryVt;
    *(const char**)(def->entry + 8) = def->desc;

    map = *(void**)(img + NativeAdapter_RegistryRva(NS_EFFECT_MAP));
    if (map == NULL) {
        Plugin_Log("[eff] _EffectEntries is NULL");
        def->state = EFF_STATE_FAILED;
        return 0;
    }
    reg = (RegEntryFn)(img + NativeAdapter_RegistryRva(NS_EFFECT_REGISTER));
    reg(map, id, def->entry);

    def->tokenId = id;
    def->state = EFF_STATE_OK;
    ++g_registeredEffectCount;
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
    return g_registeredEffectCount;
}
