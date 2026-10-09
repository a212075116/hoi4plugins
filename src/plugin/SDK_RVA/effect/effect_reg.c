#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "camera_height.h"
#include "effect_reg.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void* (__fastcall *AddTokenFn)(void* outId, void* view, void* a3);
typedef void* (__fastcall *StabFactoryFn)(void);
typedef void* (__fastcall *RegEntryFn)(void* map, int id, void* entry);
typedef void  (__fastcall *CamSetHeightFn)(void* cam, float h);
typedef char  assert_effectsize[(sizeof(void*) == 8) ? 1 : -1];

static void* g_execVt[EFF_VT_SLOTS];
static void* g_entryVt[2];
static unsigned char g_entry[16];
static int   g_tokenId = 0;
static int   g_installed = 0;
static int   g_execCalls = 0;
static int   g_registerAttempts = 0;

static unsigned char* Img(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

int Effect_LexerReady(void)
{
    unsigned char* img = Img();
    if (img == NULL) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_LEXER_INIT, 2)) return 0;
    if (img[RVA_LEXER_INIT] == 0) return 0;
    if (img[RVA_LEXER_SYNC] == 0) return 0;
    return 1;
}

int Effect_AddToken(const char* name, int* outId)
{
    struct NameView { const char* data; unsigned long long len; } view;
    unsigned char* img;
    AddTokenFn fn;
    int id = 0;
    unsigned long long n = 0;

    if (name == NULL || outId == NULL) return 0;
    img = Img();
    if (img == NULL) return 0;
    if (!Effect_LexerReady()) return 0;
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

typedef void* (__fastcall *GetParamFn)(void* a1, void* out, void* ctx, long long a4, unsigned char a5);
typedef void* (__fastcall *PackKeyFn)(void* out, const char* key, void* params, int count);
typedef void* (__fastcall *FormatFn)(void* out, void* ctx, void* packed);
typedef void  (__fastcall *ParamCtorFn)(void* p);
typedef void  (__fastcall *ParamDtorFn)(void* p);
typedef void* (__fastcall *OrigTooltipFn)(void* self, void* out, void* ctx);
typedef void  (__fastcall *StrAppendFn)(void* str, unsigned long long n);

static void Wstr(void* p, const char* s);

static const char* g_locKey = "EFFECT_SET_CAMERA_HEIGHT";
static int g_tipMode = 0;
static int g_tipCalls = 0;

static void* __fastcall MyGetTooltip(void* self, void* out, void* ctx)
{
    unsigned char* img = Img();
    unsigned char paramDesc[EFF_PARAMDESC_SIZE];
    unsigned char packed[32];
    unsigned char fin[32];
    long long v18 = 0;
    unsigned long long sz;
    unsigned long long cap;
    unsigned char* src;
    unsigned char* dst;
    unsigned long long i;

    if (img == NULL) return out;

    ++g_tipCalls;

    if (g_tipMode == 1) {
        return ((OrigTooltipFn)(img + RVA_STAB_TOOLTIP))(self, out, ctx);
    }

    if (!ConsoleCmd_IsReadable(img + RVA_EFF_PACKKEY, 16)) return out;

    memset(packed, 0, sizeof(packed));
    memset(fin, 0, sizeof(fin));
    (void)v18;
    (void)paramDesc;

    ((PackKeyFn)(img + RVA_EFF_PACKKEY))(packed, g_locKey, NULL, 0);

    if (g_tipCalls <= 8) {
        unsigned long long pkSz = *(unsigned long long*)(packed + 0x10);
        unsigned long long pkCap = *(unsigned long long*)(packed + 0x18);
        unsigned char* pk = (pkCap <= EFF_SSO_MAX) ? packed : *(unsigned char**)packed;
        if (pkSz < 200) Plugin_Log("[efftip] call#%d packed=[%s] sz=%llu cap=%llu",
                                   g_tipCalls, (char*)pk, pkSz, pkCap);
    }

    ((FormatFn)(img + RVA_EFF_FORMAT))(fin, ctx, packed);

    if (g_tipCalls <= 8) {
        unsigned long long fs = *(unsigned long long*)(fin + 0x10);
        unsigned long long fc = *(unsigned long long*)(fin + 0x18);
        unsigned char* fp = (fc <= EFF_SSO_MAX) ? fin : *(unsigned char**)fin;
        if (fs < 200) Plugin_Log("[efftip] call#%d formatted=[%s]", g_tipCalls, (char*)fp);
    }

    sz = *(unsigned long long*)(fin + 0x10);
    cap = *(unsigned long long*)(fin + 0x18);
    src = (cap <= EFF_SSO_MAX) ? fin : *(unsigned char**)fin;

    *(unsigned long long*)((unsigned char*)out + 0x10) = 0;
    *(unsigned long long*)((unsigned char*)out + 0x18) = 0;
    *(unsigned long long*)out = 0;
    *((unsigned char*)out + 0x18) = 15;
    *(unsigned char*)out = 0;

    if (sz > 0 && sz < 200 && ConsoleCmd_IsReadable(src, (size_t)sz)) {
        ((StrAppendFn)(img + RVA_EFF_STR_APPEND))(out, sz);
        cap = *(unsigned long long*)((unsigned char*)out + 0x18);
        dst = (cap <= EFF_SSO_MAX) ? (unsigned char*)out : *(unsigned char**)out;
        for (i = 0; i < sz; ++i) dst[i] = src[i];
        dst[sz] = 0;
        *(unsigned long long*)((unsigned char*)out + 0x10) = sz;
    }

    if (g_tipCalls <= 8) {
        unsigned long long osz = *(unsigned long long*)((unsigned char*)out + 0x10);
        unsigned long long ocap = *(unsigned long long*)((unsigned char*)out + 0x18);
        unsigned char* op = (ocap <= EFF_SSO_MAX) ? (unsigned char*)out : *(unsigned char**)out;
        char dtxt[256];
        int dn = 0;
        unsigned long long j;
        if (osz < 200 && ConsoleCmd_IsReadable(op, (size_t)osz + 1)) {
            for (j = 0; j < osz && dn < 240; ++j) {
                char ch = (char)op[j];
                dtxt[dn++] = (ch == 10 || ch == 13) ? ' ' : ch;
            }
            dtxt[dn] = 0;
            Plugin_Log("[efftip] call#%d key=%s len=%llu text=[%s]",
                       g_tipCalls, g_locKey, osz, dtxt);
        }
    }

    return out;
}

static void* __fastcall MyFactory(void)
{
    unsigned char* img = Img();
    StabFactoryFn make;
    void* inst;

    if (img == NULL) return NULL;
    if (!ConsoleCmd_IsReadable(img + RVA_STAB_FACTORY, 16)) return NULL;
    make = (StabFactoryFn)(img + RVA_STAB_FACTORY);
    inst = make();
    if (inst != NULL) *(void**)inst = g_execVt;
    return inst;
}

static void Wstr(void* p, const char* s)
{
    unsigned char* d = (unsigned char*)p;
    size_t n = 0;
    size_t i;
    while (s[n] != 0) ++n;
    if (n <= EFF_SSO_MAX) {
        for (i = 0; i <= EFF_SSO_MAX; ++i) d[i] = 0;
        for (i = 0; i < n; ++i) d[i] = (unsigned char)s[i];
        *(unsigned long long*)(d + 0x10) = n;
        *(unsigned long long*)(d + 0x18) = EFF_SSO_MAX;
    } else {
        for (i = 0; i < n; ++i) d[i] = (unsigned char)s[i];
        d[n] = 0;
        *(unsigned long long*)(d + 0x10) = n;
        *(unsigned long long*)(d + 0x18) = n;
    }
}

static float ParamAsFloat(void* self)
{
    unsigned char* p = (unsigned char*)self + EFF_OFF_PARAM;
    unsigned long long size;
    unsigned long long cap;
    const char* data;
    double v = 0.0;
    double frac = 0.0;
    double scale = 1.0;
    int neg = 0;
    int dot = 0;
    size_t i;

    if (!ConsoleCmd_IsReadable(p, 32)) return 0.0f;
    size = *(unsigned long long*)(p + EFF_OFF_PARAM_SIZE);
    cap  = *(unsigned long long*)(p + EFF_OFF_PARAM_CAP);
    if (size == 0 || size > 64) return 0.0f;
    data = (cap <= EFF_SSO_MAX) ? (const char*)p : *(const char**)p;
    if (!ConsoleCmd_IsReadable(data, (size_t)size)) return 0.0f;

    for (i = 0; i < (size_t)size; ++i) {
        char c = data[i];
        if (c == '-') { neg = 1; }
        else if (c == '+') { }
        else if (c == '.') { dot = 1; }
        else if (c >= '0' && c <= '9') {
            if (dot) { scale *= 10.0; frac += (double)(c - '0') / scale; }
            else { v = v * 10.0 + (double)(c - '0'); }
        } else {
            break;
        }
    }
    v += frac;
    if (neg) v = -v;
    return (float)v;
}

static void __fastcall ExecSetCamHeight(void* self, void* scope)
{
    unsigned char* img = Img();
    void* idler;
    void* cam;
    float before;
    float after;

    (void)self;
    (void)scope;
    ++g_execCalls;

    if (img == NULL) return;
    if (!ConsoleCmd_IsReadable(img + RVA_CAM_SLOT, sizeof(void*))) return;
    idler = *(void**)(img + RVA_CAM_SLOT);
    if (idler == NULL) {
        Plugin_Log("[eff] exec#%d idler NULL", g_execCalls);
        return;
    }
    if (!ConsoleCmd_IsReadable((unsigned char*)idler + 0x750, sizeof(void*))) return;
    cam = *(void**)((unsigned char*)idler + 0x750);
    if (cam == NULL) {
        Plugin_Log("[eff] exec#%d cam NULL", g_execCalls);
        return;
    }
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + 0x69C, 8)) return;

    {
        float want = ParamAsFloat(self);
        before = *(float*)((unsigned char*)cam + 0x69C);
        ((CamSetHeightFn)(img + RVA_CAM_SETH))(cam, want);
        after = *(float*)((unsigned char*)cam + 0x69C);
        Plugin_Log("[eff] exec#%d setcamheight param=%.3f  %.2f -> %.2f",
                   g_execCalls, want, before, after);
    }
}

int Effect_Register(const char* name, const char* desc, EffectExecFn exec, int* outId)
{
    unsigned char* img;
    RegEntryFn reg;
    void* map;
    int id = 0;
    int i;

    if (name == NULL || desc == NULL || exec == NULL || outId == NULL) return 0;
    if (g_installed) { *outId = g_tokenId; return 1; }
    ++g_registerAttempts;

    img = Img();
    if (img == NULL) return 0;
    if (!Effect_LexerReady()) {
        Plugin_Log("[eff] lexer not ready, defer");
        return 0;
    }
    if (!Effect_AddToken(name, &id)) {
        Plugin_Log("[eff] AddToken failed: %s", name);
        return 0;
    }

    for (i = 0; i < EFF_VT_SLOTS; ++i) {
        g_execVt[i] = *(void**)(img + RVA_STAB_VT + (unsigned)i * 8);
    }
    g_execVt[EFF_VT_EXEC / 8] = (void*)exec;
    g_execVt[EFF_VT_TOOLTIP / 8] = (void*)MyGetTooltip;

    g_entryVt[0] = *(void**)(img + RVA_STAB_ENTRY_VT);
    g_entryVt[1] = (void*)MyFactory;

    *(void**)g_entry = g_entryVt;
    *(const char**)(g_entry + 8) = desc;

    map = *(void**)(img + RVA_EFFECT_MAP);
    if (map == NULL) {
        Plugin_Log("[eff] _EffectEntries is NULL");
        return 0;
    }
    reg = (RegEntryFn)(img + RVA_REG_ENTRY);
    reg(map, id, g_entry);

    g_tokenId = id;
    g_installed = 1;
    *outId = id;
    Plugin_Log("[eff] registered name=%s tokenId=%d exec=%p factory=%p map=%p",
               name, id, (void*)exec, (void*)MyFactory, map);
    return 1;
}

int Effect_IsCameraHeightRegistered(void)
{
    return g_installed;
}
int Effect_RegisterCameraHeight(void)
{
    int id = 0;
    int ok;
    ok = Effect_Register("set_camera_height",
                         "Sets the camera height",
                         &ExecSetCamHeight, &id);
    if (ok) Plugin_Log("[eff] camera height effect ready, tokenId=%d", id);
    return ok;
}

int Effect_GetLastError(void)
{
    return g_registerAttempts;
}

int Effect_GetTokenId(void)
{
    return g_tokenId;
}
