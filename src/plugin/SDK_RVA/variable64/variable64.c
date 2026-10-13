#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "effect_reg.h"
#include "inline_hook.h"
#include "variable64.h"
#include "variable64_name.h"
#include "variable64_name_field.h"
#include "variable64_math.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void (__fastcall *Var64GetParamFn)(void* a1, void* out, void* ctx, void* a4, void* a5);
typedef void* (__fastcall *Var64FactoryFn)(void);
typedef void* (__fastcall *Var64LookupFn)(void* scopedVar, void* ctx, void* a3);

#define RVA_VARSET_FACTORY 0x341F60u
#define RVA_VAR_LOOKUP     0x542280u
#define RVA_VARSET_ENTRYVT 0x277C418u
#define RVA_GAME_SET_EXEC  0x364C60u
#define VAR64_MARK_OFF     505u
#define VAR64_SSO_LIMIT    15u
#define RVA_VAR_CONTAINER 0x542500u
#define VAR64_MARK_SET     0x53343656u
#define VAR64_MARK_ADD     0x53343641u
#define VAR64_MARK_LOG     0x5334364Cu
#define VAR64_MARK_MOD     0x5334364Du
#define VAR64_MARK_RND     0x53343652u
#define VAR64_MARK_CLP     0x53343643u
#define VAR64_MARK_CLH     0x53343648u
#define VAR64_NAME_OFF     200u
#define VAR64_SUBOBJ_OFF   88u
#define RVA_GAMESTATE_GLOBAL   0x332F260u
#define RVA_APP_GLOBAL         0x332F698u
#define RVA_SAVEINFO_INIT      0x0BC0880u
#define RVA_LOAD_SAVEFILE      0x0DA04F0u
#define RVA_STRING_ASSIGN      0x0129CA0u
#define RVA_STRING_APPEND      0x0129C10u
#define VAR64_SAVEINFO_BYTES   256u
#define VAR64_SAVEINFO_NAME_AT 32u
#define VAR64_APP_LOADER_SLOT  880u
#define VAR64_GS_SLOT_PRIMARY  1312u
#define VAR64_GS_SLOT_FALLBACK 1316u
#define VAR64_SAVEFILE_SUFFIX  ".hoi4"
#define VAR64_SAVEFILE_MAX     160u

static const char* const kVar64SlotNames[VAR64_SLOT_COUNT] = {
    "a", "b", "c", "d", "e", "f", "g", "h", "i"
};

static long long g_var64Slots[VAR64_SLOT_COUNT];

long long Var64_GetSlot(int slot)
{
    if (slot < 0 || slot >= VAR64_SLOT_COUNT) return 0;
    return g_var64Slots[slot];
}

void Var64_SetSlot(int slot, long long value)
{
    if (slot < 0 || slot >= VAR64_SLOT_COUNT) return;
    g_var64Slots[slot] = value;
}

void Var64_AddSlot(int slot, long long delta)
{
    if (slot < 0 || slot >= VAR64_SLOT_COUNT) return;
    g_var64Slots[slot] += delta;
}

const char* Var64_SlotName(int slot)
{
    if (slot < 0 || slot >= VAR64_SLOT_COUNT) return "?";
    return kVar64SlotNames[slot];
}

static unsigned int Var64_Fnv1a(const char* s)
{
    unsigned int h = 0x811C9DC5u;
    while (*s) {
        h ^= (unsigned char)*s++;
        h *= 0x01000193u;
    }
    return h;
}

static int Var64_LookupInScope(void* scope, const char* name, long long* out)
{
    unsigned char* tbl;
    unsigned char* buckets;
    unsigned char* bucket;
    unsigned char* node;
    unsigned char* namep;
    unsigned long long cap;
    unsigned long long size;
    unsigned int h;
    int mask;
    int count;
    int i;

    if (scope == NULL || name == NULL) return 0;
    tbl = (unsigned char*)scope + 16;
    if (!ConsoleCmd_IsReadable(tbl + 24, 4)) return 0;
    buckets = *(unsigned char**)(tbl + 8);
    mask = *(int*)(tbl + 20);
    if (buckets == NULL) return 0;
    if (mask <= 0 || mask > 0x100000) return 0;
    if (!ConsoleCmd_IsReadable(buckets, 48)) return 0;

    h = Var64_Fnv1a(name);
    bucket = buckets + 48 * (h & (unsigned int)mask);
    if (!ConsoleCmd_IsReadable(bucket, 48)) return 0;
    for (i = 0; i < 255; ++i) {
        node = bucket + 48 * i;
        if (!ConsoleCmd_IsReadable(node, 48)) return 0;
        count = (int)*(unsigned char*)(node + 4);
        if (count <= i) return 0;
        if (*(int*)node != (int)h) continue;
        cap = *(unsigned long long*)(node + 32);
        size = *(unsigned long long*)(node + 24);
        if (size == 0 || size > 250) continue;
        namep = (cap <= 15) ? (node + 8) : *(unsigned char**)(node + 8);
        if (namep == NULL) continue;
        if (!ConsoleCmd_IsReadable(namep, (unsigned long long)size)) continue;
        if ((unsigned long long)strlen(name) != size) continue;
        if (memcmp(namep, name, (size_t)size) != 0) continue;
        if (out != NULL) *out = *(long long*)(node + 40);
        return 1;
    }
    return 0;
}

static unsigned char* Var64_Image(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

static void* __fastcall Var64_PureGameFactory(void)
{
    unsigned char* img = Var64_Image();
    if (img == NULL) return NULL;
    if (!ConsoleCmd_IsReadable(img + RVA_VARSET_FACTORY, 16)) return NULL;
    return ((Var64FactoryFn)(img + RVA_VARSET_FACTORY))();
}

typedef long long (__fastcall *Var64GameSetExecFn)(void* self, void* ctx);

static Var64GameSetExecFn g_var64OrigGameSetExec = NULL;
static int g_var64GameSyntaxHookReady = 0;

static void* __fastcall Var64_MarkedFactory(unsigned int mark)
{
    void* inst = Var64_PureGameFactory();

    if (inst != NULL && ConsoleCmd_IsReadable((unsigned char*)inst + VAR64_MARK_OFF, 7)) {
        *(unsigned int*)((unsigned char*)inst + VAR64_MARK_OFF) = mark;
    }
    return inst;
}

static void* __fastcall Var64_SetVariable64Factory(void)
{
    return Var64_MarkedFactory(VAR64_MARK_SET);
}

static void* __fastcall Var64_AddToVariable64Factory(void)
{
    return Var64_MarkedFactory(VAR64_MARK_ADD);
}

static void* __fastcall Var64_LogVariable64Factory(void)
{
    return Var64_MarkedFactory(VAR64_MARK_LOG);
}

static void* __fastcall Var64_ModuloVariable64Factory(void)
{
    return Var64_MarkedFactory(VAR64_MARK_MOD);
}

static void* __fastcall Var64_RoundVariable64Factory(void)
{
    return Var64_MarkedFactory(VAR64_MARK_RND);
}

static void* __fastcall Var64_ClampVariable64Factory(void)
{
    return Var64_MarkedFactory(VAR64_MARK_CLP);
}

static void* __fastcall Var64_ClampHighVariable64Factory(void)
{
    return Var64_MarkedFactory(VAR64_MARK_CLH);
}

static int Var64_ResolveGameVariableEx(void* self, void* ctx, long long* outValue,
                                       unsigned char** outAddr, char* nameBuf,
                                       unsigned int nameBufSize, int keepFraction)
{
    unsigned char* img = Var64_Image();
    unsigned char* p = (unsigned char*)self;

    if (img == NULL || p == NULL || nameBuf == NULL || nameBufSize < 40) return 0;
    if (!ConsoleCmd_IsReadable(p + VAR64_SUBOBJ_OFF + 144, 24)) return 0;
    if (*(void**)(p + VAR64_SUBOBJ_OFF + 144) != NULL || *(void**)(p + VAR64_SUBOBJ_OFF + 160) != NULL) {
        Plugin_Log("[var64] indexed/compound target unsupported; no split write");
        return 0;
    }
    if (!ConsoleCmd_IsReadable(p + VAR64_NAME_OFF, 32)) return 0;

    if (!Var64_CopyTargetName(p + VAR64_NAME_OFF, nameBuf, nameBufSize, VAR64_NAME_BYTES_ONLY)) return 0;

    if (outValue != NULL) {
        *outValue = 0;
        if (ConsoleCmd_IsReadable(img + RVA_EFF_GETPARAM, 16)) {
            ((Var64GetParamFn)(img + RVA_EFF_GETPARAM))((void*)(p + 296), outValue, ctx, 0,
                                                           (void*)(long long)keepFraction);
        }
    }
    if (outAddr != NULL) {
        *outAddr = NULL;
        if (!ConsoleCmd_IsReadable(img + RVA_VAR_LOOKUP, 16)) return 0;
        *outAddr = (unsigned char*)((Var64LookupFn)(img + RVA_VAR_LOOKUP))
                       ((void*)(p + VAR64_SUBOBJ_OFF), ctx, NULL);
        if (*outAddr == NULL || !ConsoleCmd_IsReadable(*outAddr, 8)) return 0;
    }
    return 1;
}

#define VAR64_KNOWN_NAME_LIMIT 128
#define VAR64_KNOWN_NAME_BYTES (VAR64_MAIN_NAME_LIMIT + 1u)

static char g_var64KnownNames[VAR64_KNOWN_NAME_LIMIT][VAR64_KNOWN_NAME_BYTES];
static int g_var64KnownNameCount = 0;

static void Var64_RememberSixtyFourBitNameSrc(const char* name, int src)
{
    size_t n;
    int i;

    if (name == NULL) return;
    n = strlen(name);
    if (n == 0 || n >= VAR64_KNOWN_NAME_BYTES) return;
    for (i = 0; i < g_var64KnownNameCount; ++i) {
        if (strcmp(g_var64KnownNames[i], name) == 0) return;
    }
    if (g_var64KnownNameCount >= VAR64_KNOWN_NAME_LIMIT) return;
    memcpy(g_var64KnownNames[g_var64KnownNameCount], name, n + 1);
    ++g_var64KnownNameCount;
    Plugin_Log("[v64lang] registered [%s] src=%d (total=%d)", name, src, g_var64KnownNameCount);
}

static void Var64_ForgetSixtyFourBitName(const char* name)
{
    int i;

    if (name == NULL) return;
    for (i = 0; i < g_var64KnownNameCount; ++i) {
        if (strcmp(g_var64KnownNames[i], name) == 0) {
            --g_var64KnownNameCount;
            if (i < g_var64KnownNameCount) {
                memcpy(g_var64KnownNames[i], g_var64KnownNames[g_var64KnownNameCount],
                       VAR64_KNOWN_NAME_BYTES);
            }
            Plugin_Log("[v64lang] unregistered 64-bit name [%s]", name);
            return;
        }
    }
}

static char* g_var64HeapName = NULL;

static unsigned char* Var64_ResolveAddressByName(void* self, void* ctx, const char* name)
{
    unsigned char* img = Var64_Image();
    unsigned char* p = (unsigned char*)self;
    unsigned char* nm;
    unsigned char* addr;
    unsigned char saved[32];
    size_t n;

    if (img == NULL || p == NULL || name == NULL) return NULL;
    n = strlen(name);
    if (n == 0 || n > VAR64_NAME_LIMIT) return NULL;
    nm = p + VAR64_NAME_OFF;
    if (!ConsoleCmd_IsReadable(nm, 32)) return NULL;
    memcpy(saved, nm, sizeof(saved));
    if (n <= VAR64_SSO_LIMIT) {
        memcpy(nm, name, n + 1);
        *(unsigned long long*)(nm + 24) = (unsigned long long)VAR64_SSO_LIMIT;
    } else {
        if (g_var64HeapName == NULL) {
            g_var64HeapName = (char*)HeapAlloc(GetProcessHeap(), 0, 128);
            if (g_var64HeapName == NULL) return NULL;
        }
        memcpy(g_var64HeapName, name, n + 1);
        *(char**)(nm) = g_var64HeapName;
        *(unsigned long long*)(nm + 24) = (unsigned long long)127;
    }
    *(unsigned long long*)(nm + 16) = (unsigned long long)n;
    addr = NULL;
    if (ConsoleCmd_IsReadable(img + RVA_VAR_LOOKUP, 16)) {
        addr = (unsigned char*)((Var64LookupFn)(img + RVA_VAR_LOOKUP))
                   ((void*)(p + VAR64_SUBOBJ_OFF), ctx, NULL);
    }
    memcpy(nm, saved, sizeof(saved));
    if (addr == NULL || !ConsoleCmd_IsReadable(addr, 8)) return NULL;
    return addr;
}

#define RVA_VARCLAMP_ENTRYVT 0x277C680u
#define RVA_VARCLAMP_EXEC    0x0034F750u
#define RVA_VAR_CLEAR_EXEC   0x00350240u
#define RVA_VAR_ADD_EXEC     0x0034C760u
#define RVA_VAR_SUB_EXEC     0x00366BC0u
#define RVA_VAR_MUL_EXEC     0x0035B9E0u
#define RVA_VAR_DIV_EXEC     0x00355C70u

static int Var64_IsStored64(void* self, void* ctx, const char* name);
static void Var64_ResetDebtForSet(void* self, void* ctx, const char* name);
static int Var64_ReadParamValue(void* self, void* ctx, unsigned int valueOff, unsigned int flagOff, long long* out);
#include "variable64_text_format.h"

static int Var64_ResolveGameVariable(void* self, void* ctx, long long* outValue,
                                     unsigned char** outAddr, char* nameBuf,
                                     unsigned int nameBufSize)
{
    return Var64_ResolveGameVariableEx(self, ctx, outValue, outAddr, nameBuf, nameBufSize, 1);
}

static void Var64_StoreSplit64(void* self, void* ctx, const char* name,
                               unsigned char* lowAddr, long long rawValue)
{
    long long vInt = rawValue / VAR64_FRAC_SCALE;
    long long vFrac = rawValue % VAR64_FRAC_SCALE;
    unsigned long long u = (unsigned long long)vInt;
    int lo = (int)(unsigned int)(u & 0xFFFFFFFFu);
    int hi = (int)(unsigned int)((u >> 32) & 0xFFFFFFFFu);
    char hiName[48];
    char fracName[48];
    char shown[48];

    if (lowAddr != NULL) *(long long*)lowAddr = (long long)lo * VAR64_SLOT_SCALE;

    if (!Var64_MakeHighPartName(name, hiName, sizeof(hiName))) {
        Plugin_Log("[var64] name too long for high part: [%s]", name);
        return;
    }
    {
        unsigned char* hiAddr = Var64_ResolveAddressByName(self, ctx, hiName);
        if (hiAddr != NULL) {
            *(long long*)hiAddr = (long long)hi * VAR64_SLOT_SCALE;
        } else {
            Plugin_Log("[var64] cannot store high part [%s]", hiName);
        }
    }
    if (!Var64_MakeFracPartName(name, fracName, sizeof(fracName))) {
        Plugin_Log("[var64] name too long for frac part: [%s]", name);
        return;
    }
    {
        unsigned char* fracAddr = Var64_ResolveAddressByName(self, ctx, fracName);
        if (fracAddr != NULL) {
            *(long long*)fracAddr = (vFrac + VAR64_FRAC_BIAS) * VAR64_SLOT_SCALE;
        } else {
            Plugin_Log("[var64] cannot store frac part [%s]", fracName);
        }
    }
    Var64_FormatPartsToText(vInt, vFrac, shown, sizeof(shown));
    Plugin_Log("[var64] split %s: raw=%lld (%s) int=%lld frac=%lld lo=%d hi=%d",
               name, rawValue, shown, vInt, vFrac, lo, hi);
}

static long long Var64_LoadSplit64(void* self, void* ctx, const char* name,
                                   unsigned char* lowAddr, unsigned int* outLo,
                                   unsigned int* outHi)
{
    long long lo = 0;
    long long hi = 0;
    long long frac = 0;
    char hiName[48];
    char fracName[48];

    if (lowAddr != NULL) lo = *(long long*)lowAddr / VAR64_SLOT_SCALE;
    if (Var64_MakeHighPartName(name, hiName, sizeof(hiName))) {
        unsigned char* hiAddr = Var64_ResolveAddressByName(self, ctx, hiName);
        if (hiAddr != NULL) hi = *(long long*)hiAddr / VAR64_SLOT_SCALE;
    }
    if (Var64_MakeFracPartName(name, fracName, sizeof(fracName))) {
        unsigned char* fracAddr = Var64_ResolveAddressByName(self, ctx, fracName);
        if (fracAddr != NULL) frac = *(long long*)fracAddr / VAR64_SLOT_SCALE - VAR64_FRAC_BIAS;
    }
    if (outLo != NULL) *outLo = (unsigned int)(lo & 0xFFFFFFFFLL);
    if (outHi != NULL) *outHi = (unsigned int)(hi & 0xFFFFFFFFLL);
    return ((hi << 32) | (long long)(unsigned int)lo) * VAR64_FRAC_SCALE + frac;
}

static long long __fastcall Var64_DoSetVariable64(void* self, void* ctx)
{
    long long delta = 0;
    unsigned char* addr = NULL;
    char name[40];
    char shown[48];

    if (!Var64_ResolveGameVariable(self, ctx, &delta, &addr, name, sizeof(name))) {
        Plugin_Log("[var64] set_variable64 failed to resolve");
        return 0;
    }
    Var64_StoreSplit64(self, ctx, name, addr, delta);
    Var64_ResetDebtForSet(self, ctx, name);
    Var64_RememberSixtyFourBitNameSrc(name, 1);
    Var64_FormatPartsToText(delta / VAR64_FRAC_SCALE, delta % VAR64_FRAC_SCALE, shown, sizeof(shown));
    Plugin_Log("[var64] set_variable64 %s = %s", name, shown);
    return delta;
}

static long long __fastcall Var64_DoAddToVariable64(void* self, void* ctx)
{
    long long delta = 0;
    unsigned char* addr = NULL;
    char name[40];
    long long before;
    long long after;

    if (!Var64_ResolveGameVariable(self, ctx, &delta, &addr, name, sizeof(name))) {
        Plugin_Log("[var64] add_to_variable64 failed to resolve");
        return 0;
    }
    before = Var64_LoadSplit64(self, ctx, name, addr, NULL, NULL);
    after = before + delta;
    Var64_StoreSplit64(self, ctx, name, addr, after);
    Var64_RememberSixtyFourBitNameSrc(name, 2);
    {
        char b[48];
        char d[48];
        char a[48];
        Var64_FormatPartsToText(before / VAR64_FRAC_SCALE, before % VAR64_FRAC_SCALE, b, sizeof(b));
        Var64_FormatPartsToText(delta / VAR64_FRAC_SCALE, delta % VAR64_FRAC_SCALE, d, sizeof(d));
        Var64_FormatPartsToText(after / VAR64_FRAC_SCALE, after % VAR64_FRAC_SCALE, a, sizeof(a));
        Plugin_Log("[var64] add_to_variable64 %s: %s + %s = %s", name, b, d, a);
    }
    return after;
}

static long long __fastcall Var64_DoLogVariable64(void* self, void* ctx)
{
    unsigned char* addr = NULL;
    char name[40];
    unsigned int lo = 0;
    unsigned int hi = 0;
    long long current;

    if (!Var64_ResolveGameVariable(self, ctx, NULL, &addr, name, sizeof(name))) {
        Plugin_Log("[var64] log_variable64 failed to resolve");
        return 0;
    }
    current = Var64_LoadSplit64(self, ctx, name, addr, &lo, &hi);
    {
        char shown[48];
        Var64_FormatPartsToText(current / VAR64_FRAC_SCALE, current % VAR64_FRAC_SCALE,
                              shown, sizeof(shown));
        Plugin_Log("[var64] log_variable64 %s = %s (lo=%u hi=%u)", name, shown, lo, hi);
    }
    return current;
}

static void Var64_ClearHighPartAfterVanillaSet(void* self, void* ctx)
{
    unsigned char* p = (unsigned char*)self;
    unsigned char* src;
    unsigned long long size;
    unsigned long long cap;
    unsigned char* hiAddr;
    char name[40];
    char hiName[48];
    char fracName[48];
    unsigned long long k;

    if (p == NULL) return;
    if (!ConsoleCmd_IsReadable(p + VAR64_NAME_OFF, 32)) return;
    size = *(unsigned long long*)(p + VAR64_NAME_OFF + 16);
    cap = *(unsigned long long*)(p + VAR64_NAME_OFF + 24);
    if (size == 0 || size > VAR64_MAIN_NAME_LIMIT) return;
    src = (cap <= 15) ? (p + VAR64_NAME_OFF) : *(unsigned char**)(p + VAR64_NAME_OFF);
    if (src == NULL || !ConsoleCmd_IsReadable(src, size)) return;
    for (k = 0; k < size; ++k) name[k] = (char)src[k];
    name[size] = 0;

    if (Var64_MakeHighPartName(name, hiName, sizeof(hiName))) {
        hiAddr = Var64_ResolveAddressByName(self, ctx, hiName);
        if (hiAddr != NULL) *(long long*)hiAddr = 0;
    }
    if (Var64_MakeFracPartName(name, fracName, sizeof(fracName))) {
        unsigned char* fracAddr = Var64_ResolveAddressByName(self, ctx, fracName);
        if (fracAddr != NULL) *(long long*)fracAddr = 0;
    }
    Var64_ForgetSixtyFourBitName(name);
    Plugin_Log("[var64] vanilla set reclaimed name [%s]", name);
}

static long long __fastcall Var64_DoModuloVariable64(void* self, void* ctx)
{
    long long modulusRaw = 0;
    unsigned char* addr = NULL;
    char name[40];
    char shownA[48];
    char shownB[48];
    long long currentRaw;
    long long vInt;
    long long mInt;

    if (!Var64_ResolveGameVariable(self, ctx, &modulusRaw, &addr, name, sizeof(name))) {
        Plugin_Log("[var64] modulo_variable64 failed to resolve");
        return 0;
    }
    currentRaw = Var64_LoadSplit64(self, ctx, name, addr, NULL, NULL);
    vInt = currentRaw / VAR64_FRAC_SCALE;
    mInt = modulusRaw / VAR64_FRAC_SCALE;
    Var64_FormatPartsToText(vInt, 0, shownA, sizeof(shownA));
    Var64_FormatPartsToText(mInt, 0, shownB, sizeof(shownB));
    if (mInt == 0) {
        Plugin_Log("[var64] modulo_variable64 %s: modulus is zero (%s), left unchanged", name, shownA);
        return currentRaw;
    }
    vInt = vInt % mInt;
    Var64_StoreSplit64(self, ctx, name, addr, vInt * VAR64_FRAC_SCALE);
    Var64_RememberSixtyFourBitNameSrc(name, 3);
    Plugin_Log("[var64] modulo_variable64 %s: %s mod %s = %lld", name, shownA, shownB, vInt);
    return vInt * VAR64_FRAC_SCALE;
}

static long long __fastcall Var64_DoRoundVariable64(void* self, void* ctx)
{
    unsigned char* addr = NULL;
    char name[40];
    long long currentRaw;
    long long vInt;
    long long vFrac;

    if (!Var64_ResolveGameVariable(self, ctx, NULL, &addr, name, sizeof(name))) {
        Plugin_Log("[var64] round_variable64 failed to resolve");
        return 0;
    }
    currentRaw = Var64_LoadSplit64(self, ctx, name, addr, NULL, NULL);
    vInt = currentRaw / VAR64_FRAC_SCALE;
    vFrac = currentRaw % VAR64_FRAC_SCALE;
    if (vFrac >= 50000) ++vInt;
    else if (vFrac <= -50000) --vInt;
    Var64_StoreSplit64(self, ctx, name, addr, vInt * VAR64_FRAC_SCALE);
    Var64_RememberSixtyFourBitNameSrc(name, 4);
    Plugin_Log("[var64] round_variable64 %s = %lld", name, vInt);
    return vInt * VAR64_FRAC_SCALE;
}

static long long Var64_ApplyClamp(void* self, void* ctx, int isUpper)
{
    long long boundRaw = 0;
    unsigned char* addr = NULL;
    char name[40];
    char shown[48];
    long long currentRaw;
    long long result;

    if (!Var64_ResolveGameVariable(self, ctx, &boundRaw, &addr, name, sizeof(name))) {
        Plugin_Log("[var64] clamp failed to resolve");
        return 0;
    }
    currentRaw = Var64_LoadSplit64(self, ctx, name, addr, NULL, NULL);
    result = currentRaw;
    if (isUpper) {
        if (result > boundRaw) result = boundRaw;
    } else {
        if (result < boundRaw) result = boundRaw;
    }
    Var64_StoreSplit64(self, ctx, name, addr, result);
    Var64_FormatPartsToText(result / VAR64_FRAC_SCALE, result % VAR64_FRAC_SCALE, shown, sizeof(shown));
    Plugin_Log("[var64] clamp%s %s = %s", isUpper ? "-max" : "-min", name, shown);
    return result;
}

static long long __fastcall Var64_DoClampVariable64(void* self, void* ctx)
{
    return Var64_ApplyClamp(self, ctx, 0);
}

static long long __fastcall Var64_DoClampHighVariable64(void* self, void* ctx)
{
    return Var64_ApplyClamp(self, ctx, 1);
}

static Var64GameSetExecFn g_var64OrigAddExec = NULL;
static Var64GameSetExecFn g_var64OrigSubExec = NULL;
static Var64GameSetExecFn g_var64OrigMulExec = NULL;
static Var64GameSetExecFn g_var64OrigDivExec = NULL;

static int Var64_HasFracComponent(void* self, void* ctx, const char* name)
{
    char fracName[48];
    unsigned char* addr;
    long long slot;

    if (!Var64_MakeFracPartName(name, fracName, sizeof(fracName))) return 0;
    addr = Var64_ResolveAddressByName(self, ctx, fracName);
    if (addr == NULL) return 0;
    if (!ConsoleCmd_IsReadable(addr, 8)) return 0;
    slot = *(long long*)addr;
    if (slot < 100000LL * VAR64_SLOT_SCALE) return 0;
    if (slot >= 200000LL * VAR64_SLOT_SCALE) return 0;
    return 1;
}

static void Var64_NormalizeFraction(long long* outInt, long long* outFrac)
{
    while (*outFrac >= VAR64_FRAC_SCALE) {
        *outFrac -= VAR64_FRAC_SCALE;
        ++(*outInt);
    }
    while (*outFrac < 0) {
        *outFrac += VAR64_FRAC_SCALE;
        --(*outInt);
    }
}

static int Var64_ReadNameOnly(void* self, char* nameBuf, unsigned int nameBufSize)
{
    unsigned char* p = (unsigned char*)self;

    if (p == NULL || nameBuf == NULL || nameBufSize < 40) return 0;
    if (!ConsoleCmd_IsReadable(p + VAR64_SUBOBJ_OFF + 144, 24)
        || *(void**)(p + VAR64_SUBOBJ_OFF + 144) != NULL || *(void**)(p + VAR64_SUBOBJ_OFF + 160) != NULL) return 0;
    if (!ConsoleCmd_IsReadable(p + VAR64_NAME_OFF, 32)) return 0;
    if (!Var64_CopyTargetName(p + VAR64_NAME_OFF, nameBuf, nameBufSize, VAR64_NAME_WITH_TERMINATOR)) return 0;
    return 1;
}

typedef void* (__fastcall *Var64ContainerFn)(void*, void*, int*, int*, void**, void**, void**, void**, void**, void**);

static void* Var64_ContainerAt(void* self, void* ctx, unsigned int offset)
{
    unsigned char* img = Var64_Image();
    int a = 0, b = 0;
    void* extra[6] = {0};
    if (img == NULL || self == NULL || ctx == NULL) return NULL;
    if (!ConsoleCmd_IsReadable(img + RVA_VAR_CONTAINER, 16)) return NULL;
    return ((Var64ContainerFn)(img + RVA_VAR_CONTAINER))((unsigned char*)self + offset, ctx,
            &a, &b, &extra[0], &extra[1], &extra[2], &extra[3], &extra[4], &extra[5]);
}

static void* Var64_Container(void* self, void* ctx)
{
    return Var64_ContainerAt(self, ctx, 88u);
}

static int Var64_ReadStoredIn(void* container, const char* name, long long* outRaw)
{
    long long lo, hi, frac;
    char highName[48], fracName[48];
    if (!Var64_MakeHighPartName(name, highName, sizeof(highName))
        || !Var64_MakeFracPartName(name, fracName, sizeof(fracName))) return 0;
    if (container == NULL
        || !Var64_LookupInScope(container, fracName, &frac)
        || frac <= 0 || frac >= 200000LL * VAR64_SLOT_SCALE
        || frac % VAR64_SLOT_SCALE != 0
        || !Var64_LookupInScope(container, highName, &hi)
        || !Var64_LookupInScope(container, name, &lo)) return 0;
    return Var64_DecodeStoredParts(lo, hi, frac, outRaw);
}
static int Var64_IsStored64(void* self, void* ctx, const char* name)
{
    return Var64_ReadStoredIn(Var64_Container(self, ctx), name, NULL);
}

int Var64_ReadStoredContainerRaw(void* container, const char* name, long long* out)
{
    if (out == NULL) return 0;
    return Var64_ReadStoredIn(container, name, out);
}

#include "variable64_debt.inc"

static int Var64_ReadOperandLiteralAt(void* self, unsigned int paramOff, long long* out)
{
    unsigned char* pd = (unsigned char*)self + paramOff;

    if (out == NULL) return 0;
    *out = 0;
    if (!ConsoleCmd_IsReadable(pd, 0x48)) return 0;
    if (*(unsigned char*)(pd + 9) == 0) return 0;
    *out = *(long long*)(pd + 0x40);
    return 1;
}

static int Var64_ReadOperandLiteral(void* self, long long* out)
{
    return Var64_ReadOperandLiteralAt(self, 296u, out);
}

static int Var64_ReadOperandNameAt(void* self, unsigned int paramOff,
                                   char* out, unsigned int outSize)
{
    unsigned char* pd = (unsigned char*)self + paramOff;
    unsigned long long size;
    unsigned long long cap;
    unsigned char* src;

    if (out == NULL || outSize < 8) return 0;
    out[0] = 0;
    if (!ConsoleCmd_IsReadable(pd, 176) || *(void**)(pd + 144) != NULL || *(void**)(pd + 160) != NULL) return 0;
    if (*(unsigned char*)(pd + 9) != 0) return 0;
    size = *(unsigned long long*)(pd + 0x80);
    cap = *(unsigned long long*)(pd + 0x88);
    if (size == 0 || size >= outSize) return 0;
    src = (cap <= 15) ? (pd + 0x70) : *(unsigned char**)(pd + 0x70);
    if (src == NULL || !ConsoleCmd_IsReadable(src, size + 1)) return 0;
    memcpy(out, src, (size_t)size);
    out[size] = 0;
    return 1;
}

static int Var64_ReadOperandName(void* self, char* out, unsigned int outSize)
{
    return Var64_ReadOperandNameAt(self, 296u, out, outSize);
}

static int Var64_ReadStoredOperandAt(void* self, void* ctx, unsigned int offset, long long* out)
{
    char name[40];
    if (!Var64_ReadOperandNameAt(self, offset, name, sizeof(name))) return 0;
    return Var64_ReadStoredIn(Var64_ContainerAt(self, ctx, offset), name, out);
}

static long long Var64_ReadTrueRaw(void* self, void* ctx, const char* name, unsigned char* addr)
{
    Var64DebtRecord* d;
    long long slot;

    if (addr == NULL) return 0;
    if (self != NULL && ctx != NULL && Var64_IsStored64(self, ctx, name)) {
        return Var64_LoadSplit64(self, ctx, name, addr, NULL, NULL);
    }
    slot = *(long long*)addr;
    d = Var64_FindDebt(self, ctx, name);
    if (d == NULL) return slot;
    return slot + d->debtInt * VAR64_FRAC_SCALE + d->debtFrac;
}

static void Var64_WriteTrueRaw(void* self, void* ctx, const char* name,
                              unsigned char* addr, long long trueRaw)
{
    long long vInt;
    long long vFrac;
    Var64DebtRecord* d;

    if (addr == NULL) return;
    if (trueRaw > VAR64_TRUE_CLAMP) trueRaw = VAR64_TRUE_CLAMP;
    if (trueRaw < -VAR64_TRUE_CLAMP) trueRaw = -VAR64_TRUE_CLAMP;

    if (Var64_IsStored64(self, ctx, name)) {
        if (self != NULL && ctx != NULL) {
            Var64_StoreSplit64(self, ctx, name, addr, trueRaw);
        } else {
            *(long long*)addr = trueRaw;
        }
        return;
    }

    vInt = trueRaw / VAR64_FRAC_SCALE;
    vFrac = trueRaw % VAR64_FRAC_SCALE;

    if (vInt >= VAR64_INT32_MIN && vInt <= VAR64_INT32_MAX) {
        d = Var64_FindDebt(self, ctx, name);
        if (d != NULL) {
            Var64_ClearDebt(d);
            Plugin_Log("[var64] debt %s fully repaid, back in 32-bit range", name);
        }
        if (self != NULL && ctx != NULL) {
            Var64_StoreSplit64(self, ctx, name, addr, trueRaw);
            Var64_RememberSixtyFourBitNameSrc(name, 6);
        } else {
            *(long long*)addr = trueRaw;
        }
        return;
    }

    {
        long long lockInt = (vInt > 0) ? VAR64_INT32_MAX : VAR64_INT32_MIN;
        long long lockFrac = (vInt > 0) ? 99999 : 0;
        long long lockedRaw = lockInt * VAR64_FRAC_SCALE + lockFrac;
        if (vInt < 0) lockedRaw += 1;

        d = Var64_FindDebt(self, ctx, name);
        if (d == NULL) d = Var64_NewDebt(self, ctx, name);
        if (d == NULL) return;
        d->debtInt = trueRaw / VAR64_FRAC_SCALE - (lockedRaw / VAR64_FRAC_SCALE);
        d->debtFrac = trueRaw % VAR64_FRAC_SCALE - (lockedRaw % VAR64_FRAC_SCALE);
        Var64_NormalizeFraction(&d->debtInt, &d->debtFrac);
        *(long long*)addr = lockedRaw;
        Plugin_Log("[var64] %s locked at %lld, owed %lld.%05lld", name,
                   lockedRaw / VAR64_FRAC_SCALE,
                   d->debtInt, d->debtFrac < 0 ? -d->debtFrac : d->debtFrac);
    }
}

static int Var64_TryDebtArithmetic(void* self, void* ctx, int op, const char* opName)
{
    unsigned char* img = Var64_Image();
    char name[40], operandName[40], shown[48];
    unsigned char* addr;
    long long operandRaw = 0, currentRaw, result;
    int namedOperand;
    int storedOperand;
    if (img == NULL || self == NULL || ctx == NULL) return 0;
    if (!Var64_ReadNameOnly(self, name, sizeof(name))) return 0;
    namedOperand = Var64_ReadOperandName(self, operandName, sizeof(operandName));
    storedOperand = namedOperand && Var64_ReadStoredOperandAt(self, ctx, 296u, &operandRaw);
    if (!Var64_IsStored64(self, ctx, name) && Var64_FindDebt(self, ctx, name) == NULL && !storedOperand) return 0;
    if (!storedOperand && !Var64_ReadOperandLiteral(self, &operandRaw)) {
        if (!Var64_ResolveGameVariableEx(self, ctx, &operandRaw, NULL, operandName, sizeof(operandName), 0)) return 1;
    }
    addr = ((Var64LookupFn)(img + RVA_VAR_LOOKUP))((unsigned char*)self + 88, ctx, NULL);
    if (addr == NULL) return 1;
    currentRaw = Var64_ReadTrueRaw(self, ctx, name, addr);
    if (!Var64_CalculateRaw(currentRaw, operandRaw, op, &result)) {
        Plugin_Log("[var64] %s %s: divide by zero, left unchanged", opName, name);
        return 1;
    }
    Var64_WriteTrueRaw(self, ctx, name, addr, result);
    Var64_FormatPartsToText(result / VAR64_FRAC_SCALE, result % VAR64_FRAC_SCALE, shown, sizeof(shown));
    Plugin_Log("[var64] %s %s = %s", opName, name, shown);
    return 1;
}

static int Var64_TryArithmetic(void* self, void* ctx, int op, const char* opName)
{
    long long operandRaw = 0;
    unsigned char* addr = NULL;
    char name[40];
    char shown[48];
    long long currentRaw;
    long long vInt;
    long long vFrac;
    long long oInt;
    long long oFrac;
    long long rInt;
    long long rFrac;

    if (self == NULL || ctx == NULL) return 0;
    if (!Var64_ReadNameOnly(self, name, sizeof(name))) return 0;
    if (!Var64_IsStored64(self, ctx, name)) return 0;
    if (!Var64_ResolveGameVariableEx(self, ctx, &operandRaw, &addr, name, sizeof(name), 0)) return 0;

    currentRaw = Var64_LoadSplit64(self, ctx, name, addr, NULL, NULL);
    vInt = currentRaw / VAR64_FRAC_SCALE;
    vFrac = currentRaw % VAR64_FRAC_SCALE;
    oInt = operandRaw / VAR64_FRAC_SCALE;
    oFrac = operandRaw % VAR64_FRAC_SCALE;
    rInt = 0;
    rFrac = 0;

    if (Var64_ReadStoredOperandAt(self, ctx, 296u, &operandRaw)) {
        oInt = operandRaw / VAR64_FRAC_SCALE;
        oFrac = operandRaw % VAR64_FRAC_SCALE;
    }
    if (op == VAR64_OP_ADD) {
        rInt = vInt + oInt;
        rFrac = vFrac + oFrac;
    } else if (op == VAR64_OP_SUB) {
        rInt = vInt - oInt;
        rFrac = vFrac - oFrac;
    } else if (op == VAR64_OP_MUL) {
        unsigned long long a = (unsigned long long)(currentRaw < 0 ? -currentRaw : currentRaw);
        unsigned long long b = (unsigned long long)(operandRaw < 0 ? -operandRaw : operandRaw);
        int neg = ((currentRaw < 0) != (operandRaw < 0)) ? 1 : 0;
        unsigned long long hi = 0;
        unsigned long long lo = _umul128(a, b, &hi);
        unsigned long long q;
        unsigned long long rem;
        if (hi != 0) {
            Plugin_Log("[var64] %s %s: multiply overflow, clamped", opName, name);
            return 0;
        }
        q = lo / (unsigned long long)VAR64_FRAC_SCALE;
        rem = q % (unsigned long long)VAR64_FRAC_SCALE;
        rInt = (long long)(q / (unsigned long long)VAR64_FRAC_SCALE);
        rFrac = (long long)rem;
        if (neg) {
            rInt = -rInt;
            rFrac = -rFrac;
        }
    } else {
        unsigned long long a = (unsigned long long)(currentRaw < 0 ? -currentRaw : currentRaw);
        unsigned long long b = (unsigned long long)(operandRaw < 0 ? -operandRaw : operandRaw);
        int neg = ((currentRaw < 0) != (operandRaw < 0)) ? 1 : 0;
        unsigned long long hi = 0;
        unsigned long long lo;
        unsigned long long q;
        unsigned long long rem;
        if (b == 0) {
            Plugin_Log("[var64] %s %s: divide by zero, left unchanged", opName, name);
            return 1;
        }
        lo = _umul128(a, (unsigned long long)VAR64_FRAC_SCALE, &hi);
        if (hi != 0) {
            Plugin_Log("[var64] %s %s: divide overflow, clamped", opName, name);
            return 0;
        }
        q = lo / b;
        rem = q % (unsigned long long)VAR64_FRAC_SCALE;
        rInt = (long long)(q / (unsigned long long)VAR64_FRAC_SCALE);
        rFrac = (long long)rem;
        if (neg) {
            rInt = -rInt;
            rFrac = -rFrac;
        }
    }

    Var64_NormalizeFraction(&rInt, &rFrac);
    Var64_StoreSplit64(self, ctx, name, addr, rInt * VAR64_FRAC_SCALE + rFrac);
    Var64_FormatPartsToText(rInt, rFrac, shown, sizeof(shown));
    Plugin_Log("[var64] %s %s -> %s", opName, name, shown);
    return 1;
}

static long long __fastcall Var64_AddDetour(void* self, void* ctx)
{
    unsigned int mark = 0;

    if (self != NULL && ConsoleCmd_IsReadable((unsigned char*)self + VAR64_MARK_OFF, 7)) {
        mark = *(unsigned int*)((unsigned char*)self + VAR64_MARK_OFF);
    }
    if (mark == VAR64_MARK_ADD) return Var64_DoAddToVariable64(self, ctx);
    if (Var64_TryDebtArithmetic(self, ctx, VAR64_OP_ADD, "add_to_variable")) return 0;
    if (Var64_TryArithmetic(self, ctx, VAR64_OP_ADD, "add_to_variable")) return 0;
    if (g_var64OrigAddExec != NULL) return g_var64OrigAddExec(self, ctx);
    return 0;
}

static long long __fastcall Var64_SubDetour(void* self, void* ctx)
{
    if (Var64_TryDebtArithmetic(self, ctx, VAR64_OP_SUB, "subtract_from_variable")) return 0;
    if (Var64_TryArithmetic(self, ctx, VAR64_OP_SUB, "subtract_from_variable")) return 0;
    if (g_var64OrigSubExec != NULL) return g_var64OrigSubExec(self, ctx);
    return 0;
}

static long long __fastcall Var64_MulDetour(void* self, void* ctx)
{
    if (Var64_TryDebtArithmetic(self, ctx, VAR64_OP_MUL, "multiply_variable")) return 0;
    if (Var64_TryArithmetic(self, ctx, VAR64_OP_MUL, "multiply_variable")) return 0;
    if (g_var64OrigMulExec != NULL) return g_var64OrigMulExec(self, ctx);
    return 0;
}

static long long __fastcall Var64_DivDetour(void* self, void* ctx)
{
    if (Var64_TryDebtArithmetic(self, ctx, VAR64_OP_DIV, "divide_variable")) return 0;
    if (Var64_TryArithmetic(self, ctx, VAR64_OP_DIV, "divide_variable")) return 0;
    if (g_var64OrigDivExec != NULL) return g_var64OrigDivExec(self, ctx);
    return 0;
}

static Var64GameSetExecFn g_var64OrigClampExec = NULL;
static Var64GameSetExecFn g_var64OrigClearExec = NULL;

static long long __fastcall Var64_ClearDetour(void* self, void* ctx)
{
    char name[40];
    Var64DebtRecord* debt;
    if (Var64_ReadNameOnly(self, name, sizeof(name))) {
        debt = Var64_FindDebt(self, ctx, name);
        if (Var64_IsStored64(self, ctx, name) || debt != NULL) {
            Var64_ClearHighPartAfterVanillaSet(self, ctx);
            if (debt != NULL) Var64_ClearDebt(debt);
            Plugin_Log("[var64] clear_variable %s cleared split parts and debt", name);
        }
    }
    if (g_var64OrigClearExec != NULL) return g_var64OrigClearExec(self, ctx);
    return 0;
}

static int Var64_ReadParamValue(void* self, void* ctx, unsigned int valueOff,
                               unsigned int flagOff, long long* out)
{
    unsigned char* img = Var64_Image();
    unsigned char* p = (unsigned char*)self;

    if (out == NULL || img == NULL || p == NULL) return 0;
    *out = 0;
    if (!ConsoleCmd_IsReadable(p + flagOff, 1)) return 0;
    if (*(unsigned char*)(p + flagOff) == 0) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_EFF_GETPARAM, 16)) return 0;
    ((Var64GetParamFn)(img + RVA_EFF_GETPARAM))((void*)(p + valueOff), out, ctx, 0, (void*)0);
    return 1;
}

static long long __fastcall Var64_ClampDetour(void* self, void* ctx)
{
    unsigned char* img = Var64_Image();
    char name[40];
    unsigned char* addr;
    long long curRaw;
    long long minRaw = 0;
    long long maxRaw = 0;
    int haveMin;
    int haveMax;
    char shown[48];

    if (img == NULL || self == NULL || ctx == NULL) goto vanilla;
    if (!Var64_ReadNameOnly(self, name, sizeof(name))) goto vanilla;
    if (!Var64_IsStored64(self, ctx, name) && Var64_FindDebt(self, ctx, name) == NULL) goto vanilla;

    addr = ((Var64LookupFn)(img + RVA_VAR_LOOKUP))((void*)((unsigned char*)self + 88), ctx, NULL);
    if (addr == NULL) goto vanilla;

    haveMin = Var64_ReadParamValue(self, ctx, 296u, 304u, &minRaw);
    haveMax = Var64_ReadParamValue(self, ctx, 504u, 512u, &maxRaw);

    if (haveMin) Var64_ReadStoredOperandAt(self, ctx, 296u, &minRaw);
    if (haveMax) Var64_ReadStoredOperandAt(self, ctx, 504u, &maxRaw);

    curRaw = Var64_ReadTrueRaw(self, ctx, name, addr);
    if (haveMax && curRaw > maxRaw) curRaw = maxRaw;
    if (haveMin && curRaw < minRaw) curRaw = minRaw;
    Var64_WriteTrueRaw(self, ctx, name, addr, curRaw);
    Var64_FormatPartsToText(curRaw / VAR64_FRAC_SCALE, curRaw % VAR64_FRAC_SCALE,
                            shown, sizeof(shown));
    Plugin_Log("[var64] clamp_variable %s = %s (min=%d max=%d)", name, shown, haveMin, haveMax);
    return 0;

vanilla:
    if (g_var64OrigClampExec != NULL) return g_var64OrigClampExec(self, ctx);
    return 0;
}

static long long __fastcall Var64_GameSyntaxDetour(void* self, void* ctx)
{
    unsigned int mark = 0;
    long long result;
    char previousName[40];
    int was64;
    int haveName;

    if (self != NULL && ConsoleCmd_IsReadable((unsigned char*)self + VAR64_MARK_OFF, 7)) {
        mark = *(unsigned int*)((unsigned char*)self + VAR64_MARK_OFF);
    }
    if (mark == VAR64_MARK_SET) return Var64_DoSetVariable64(self, ctx);
    if (mark == VAR64_MARK_ADD) return Var64_DoAddToVariable64(self, ctx);
    if (mark == VAR64_MARK_LOG) return Var64_DoLogVariable64(self, ctx);
    if (mark == VAR64_MARK_MOD) return Var64_DoModuloVariable64(self, ctx);
    if (mark == VAR64_MARK_RND) return Var64_DoRoundVariable64(self, ctx);
    if (mark == VAR64_MARK_CLP) return Var64_DoClampVariable64(self, ctx);
    if (mark == VAR64_MARK_CLH) return Var64_DoClampHighVariable64(self, ctx);
    if (g_var64OrigGameSetExec == NULL) return 0;
    haveName = Var64_ReadNameOnly(self, previousName, sizeof(previousName));
    was64 = haveName && Var64_IsStored64(self, ctx, previousName);
    result = g_var64OrigGameSetExec(self, ctx);
    if (was64) Var64_ClearHighPartAfterVanillaSet(self, ctx);
    if (haveName) Var64_ResetDebtForSet(self, ctx, previousName);
    return result;
}

static void Var64_InstallGameSyntaxHook(void)
{
    unsigned char* img = Var64_Image();
    void* orig;

    if (g_var64GameSyntaxHookReady) return;
    if (img == NULL) return;
    if (!ConsoleCmd_IsReadable(img + RVA_GAME_SET_EXEC, 16)) return;
    orig = InlineHook_Install(img + RVA_GAME_SET_EXEC, (void*)Var64_GameSyntaxDetour);
    if (orig == NULL) {
        Plugin_Log("[var64] gamesyntax hook install failed");
        return;
    }
    g_var64OrigGameSetExec = (Var64GameSetExecFn)orig;
    g_var64GameSyntaxHookReady = 1;
    Plugin_Log("[var64] gamesyntax hook installed, orig=%p", orig);
}

static void __fastcall ExecVar64GameSyntax(void* self, void* scope)
{
    Var64_GameSyntaxDetour(self, scope);
}

typedef void (__fastcall *Var64SaveInfoInitFn)(void* self);
typedef void (__fastcall *Var64LoadSaveFileFn)(void* loader, void* saveInfo, void* slot);
typedef void* (__fastcall *Var64LoaderGetterFn)(void* app);
typedef void** (__fastcall *Var64StringAssignFn)(void** dst, const void* src, size_t len);
typedef void** (__fastcall *Var64StringAppendFn)(void** dst, const void* src, size_t len);

static int Var64_WriteSaveFileName(CmdString* field, const char* fileName)
{
    unsigned char* img;
    size_t n;

    if (field == NULL || fileName == NULL) return 0;
    n = strlen(fileName);
    if (n == 0 || n > 120) return 0;
    if (n <= CMD_SSO_MAX) {
        memcpy(field->u.buf, fileName, n);
        field->u.buf[n] = 0;
        field->size = n;
        field->cap = 15;
        return 1;
    }
    img = Var64_Image();
    if (img == NULL) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_STRING_ASSIGN, 16)) return 0;
    ((Var64StringAssignFn)(img + RVA_STRING_ASSIGN))((void**)field, fileName, n);
    return 1;
}

static long long __fastcall Handler_LoadGameSaveFile(CmdResult* out, CmdArgs* args)
{
    unsigned char saveInfo[VAR64_SAVEINFO_BYTES];
    unsigned char* img;
    void* gs;
    void* app;
    void* vtable;
    void* loader;
    void* slot;
    char fileName[VAR64_SAVEFILE_MAX];
    char msg[160];
    size_t n;

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);

    if (!ConsoleCmd_GetArg(args, 0, fileName, sizeof(fileName))) {
        ConsoleCmd_SetMessage(out, "loadgame <savefile>  e.g. loadgame zz_reload_test");
        return (long long)out;
    }

    n = strlen(fileName);
    if (n < 5 || _stricmp(fileName + n - 5, VAR64_SAVEFILE_SUFFIX) != 0) {
        if (n + 6 > sizeof(fileName)) {
            ConsoleCmd_SetMessage(out, "savefile name too long");
            return (long long)out;
        }
        memcpy(fileName + n, VAR64_SAVEFILE_SUFFIX, 6);
    }

    img = Var64_Image();
    if (img == NULL) { ConsoleCmd_SetMessage(out, "no module base"); return (long long)out; }
    if (!ConsoleCmd_IsReadable(img + RVA_GAMESTATE_GLOBAL, 8)
        || !ConsoleCmd_IsReadable(img + RVA_APP_GLOBAL, 8)
        || !ConsoleCmd_IsReadable(img + RVA_SAVEINFO_INIT, 16)
        || !ConsoleCmd_IsReadable(img + RVA_LOAD_SAVEFILE, 16)) {
        ConsoleCmd_SetMessage(out, "game addresses unreadable");
        return (long long)out;
    }

    gs  = *(void**)(img + RVA_GAMESTATE_GLOBAL);
    app = *(void**)(img + RVA_APP_GLOBAL);
    if (gs == NULL || app == NULL || !ConsoleCmd_IsReadable(app, 16)) {
        ConsoleCmd_SetMessage(out, "gamestate or application not ready");
        return (long long)out;
    }

    memset(saveInfo, 0, sizeof(saveInfo));
    ((Var64SaveInfoInitFn)(img + RVA_SAVEINFO_INIT))(saveInfo);
    if (!Var64_WriteSaveFileName((CmdString*)(saveInfo + VAR64_SAVEINFO_NAME_AT), fileName)) {
        ConsoleCmd_SetMessage(out, "cannot set savefile name");
        return (long long)out;
    }

    vtable = *(void**)app;
    loader = ((Var64LoaderGetterFn)(*(void**)((char*)vtable + VAR64_APP_LOADER_SLOT)))(app);
    if (loader == NULL) {
        ConsoleCmd_SetMessage(out, "save loader not available");
        return (long long)out;
    }

    slot = (char*)gs + VAR64_GS_SLOT_FALLBACK;
    if (*(int*)((char*)gs + VAR64_GS_SLOT_PRIMARY) > 0) slot = (char*)gs + VAR64_GS_SLOT_PRIMARY;

    Plugin_Log("[saveload] loadgame [%s] gs=%p app=%p loader=%p slot=%p",
               fileName, gs, app, loader, slot);
    ((Var64LoadSaveFileFn)(img + RVA_LOAD_SAVEFILE))(loader, saveInfo, slot);
    Plugin_Log("[saveload] loadgame returned for [%s]", fileName);

    _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Loaded %s", fileName);
    ConsoleCmd_SetMessage(out, msg);
    out->ok = 1;
    return (long long)out;
}

static const CmdDef kVar64CommandDefs[] = {
    { "loadgame", "Loads a save file by name (scriptable save loading).",
      NULL, 1, { "savefile", NULL }, Handler_LoadGameSaveFile }
};

int Var64_RegisterLoadGameCommand(void)
{
    return ConsoleCmd_RegisterAll(kVar64CommandDefs,
        (int)(sizeof(kVar64CommandDefs) / sizeof(kVar64CommandDefs[0])));
}

#include "variable64_language.inc"

EFF_DEF(gamesetvar64, "set_variable64",
        "Sets a 64-bit script variable. Same syntax as set_variable.",
        "EFFECT_SET_VARIABLE64", &ExecVar64GameSyntax)

EFF_DEF(gameaddvar64, "add_to_variable64",
        "Adds to a 64-bit script variable. Same syntax as set_variable.",
        "EFFECT_ADD_TO_VARIABLE64", &ExecVar64GameSyntax)

EFF_DEF(gamelogvar64, "log_variable64",
        "Logs a 64-bit script variable in full precision. Same syntax as set_variable.",
        "EFFECT_LOG_VARIABLE64", &ExecVar64GameSyntax)

EFF_DEF(gamemodvar64, "modulo_variable64",
        "Sets a 64-bit script variable to the remainder of its division by the value.",
        "EFFECT_MODULO_VARIABLE64", &ExecVar64GameSyntax)

EFF_DEF(gamerndvar64, "round_variable64",
        "Rounds a 64-bit script variable to the nearest integer.",
        "EFFECT_ROUND_VARIABLE64", &ExecVar64GameSyntax)

EFF_DEF(gameclpvar64, "clamp_variable64",
        "Raises a 64-bit script variable to value if it is below it.",
        "EFFECT_CLAMP_VARIABLE64", &ExecVar64GameSyntax)

EFF_DEF(gameclhvar64, "clamp_variable64_max",
        "Lowers a 64-bit script variable to value if it is above it.",
        "EFFECT_CLAMP_VARIABLE64_MAX", &ExecVar64GameSyntax)

typedef struct {
    EffectDef* definition;
    void (*fill)(void);
    Var64FactoryFn factory;
} Var64EffectBinding;

static const Var64EffectBinding g_var64EffectBindings[] = {
    { &gamesetvar64_def, gamesetvar64_fill, Var64_SetVariable64Factory },
    { &gameaddvar64_def, gameaddvar64_fill, Var64_AddToVariable64Factory },
    { &gamelogvar64_def, gamelogvar64_fill, Var64_LogVariable64Factory },
    { &gamemodvar64_def, gamemodvar64_fill, Var64_ModuloVariable64Factory },
    { &gamerndvar64_def, gamerndvar64_fill, Var64_RoundVariable64Factory },
    { &gameclpvar64_def, gameclpvar64_fill, Var64_ClampVariable64Factory },
    { &gameclhvar64_def, gameclhvar64_fill, Var64_ClampHighVariable64Factory }
};

#define VAR64_EFFECT_COUNT (int)(sizeof(g_var64EffectBindings) / sizeof(g_var64EffectBindings[0]))

static void Var64_InstallArithmeticHooks(void)
{
    unsigned char* img = Var64_Image();

    if (img == NULL) return;
    if (ConsoleCmd_IsReadable(img + RVA_VAR_ADD_EXEC, 16)) {
        g_var64OrigAddExec = (Var64GameSetExecFn)InlineHook_Install(img + RVA_VAR_ADD_EXEC,
                                                                   (void*)Var64_AddDetour);
    }
    if (ConsoleCmd_IsReadable(img + RVA_VAR_SUB_EXEC, 16)) {
        g_var64OrigSubExec = (Var64GameSetExecFn)InlineHook_Install(img + RVA_VAR_SUB_EXEC,
                                                                   (void*)Var64_SubDetour);
    }
    if (ConsoleCmd_IsReadable(img + RVA_VAR_MUL_EXEC, 16)) {
        g_var64OrigMulExec = (Var64GameSetExecFn)InlineHook_Install(img + RVA_VAR_MUL_EXEC,
                                                                   (void*)Var64_MulDetour);
    }
    if (ConsoleCmd_IsReadable(img + RVA_VAR_DIV_EXEC, 16)) {
        g_var64OrigDivExec = (Var64GameSetExecFn)InlineHook_Install(img + RVA_VAR_DIV_EXEC,
                                                                   (void*)Var64_DivDetour);
    }
    if (ConsoleCmd_IsReadable(img + RVA_VARCLAMP_EXEC, 16)) {
        g_var64OrigClampExec = (Var64GameSetExecFn)InlineHook_Install(img + RVA_VARCLAMP_EXEC,
                                                                     (void*)Var64_ClampDetour);
    }
    if (ConsoleCmd_IsReadable(img + RVA_VAR_CLEAR_EXEC, 16)) {
        g_var64OrigClearExec = (Var64GameSetExecFn)InlineHook_Install(img + RVA_VAR_CLEAR_EXEC, (void*)Var64_ClearDetour);
    }
    Plugin_Log("[var64] clear hook: %p", (void*)g_var64OrigClearExec);
    Plugin_Log("[var64] arith hook: add=%p sub=%p mul=%p div=%p clamp=%p (round/modulo disabled: wrong name field)",
               (void*)g_var64OrigAddExec, (void*)g_var64OrigSubExec,
               (void*)g_var64OrigMulExec, (void*)g_var64OrigDivExec,
               (void*)g_var64OrigClampExec);
}

int Var64_RegisterEffects(void)
{
    unsigned char* img;
    int n, i;
    EffectDef* definitions[VAR64_EFFECT_COUNT];

    for (i = 0; i < VAR64_EFFECT_COUNT; ++i) g_var64EffectBindings[i].fill();
    for (i = 0; i < VAR64_EFFECT_COUNT; ++i) {
        definitions[i] = g_var64EffectBindings[i].definition;
        definitions[i]->factory = g_var64EffectBindings[i].factory;
    }
    n = Effect_RegistryRegisterAll(definitions, VAR64_EFFECT_COUNT);

    img = Var64_Image();
    if (img != NULL) {
        for (i = 0; i < VAR64_EFFECT_COUNT; ++i) {
            if (definitions[i]->state == EFF_STATE_OK) {
                definitions[i]->entryVt[0] = *(void**)(img + RVA_VARSET_ENTRYVT);
            }
        }
        Plugin_Log("[var64] entryVt set=%p add=%p log=%p mod=%p rnd=%p clp=%p",
                   gamesetvar64_def.entryVt[0], gameaddvar64_def.entryVt[0],
                   gamelogvar64_def.entryVt[0], gamemodvar64_def.entryVt[0],
                   gamerndvar64_def.entryVt[0], gameclpvar64_def.entryVt[0]);
    }

    Var64_InstallGameSyntaxHook();
    Var64_InstallArithmeticHooks();

    Plugin_Log("[eff] var64 effects registered: %d/%d", n, VAR64_EFFECT_COUNT);
    return n;
}
