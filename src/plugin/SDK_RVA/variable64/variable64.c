#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "effect_reg.h"
#include "inline_hook.h"
#include "variable64.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void (__fastcall *Var64GetParamFn)(void* a1, void* out, void* ctx, void* a4, void* a5);
typedef void* (__fastcall *Var64FactoryFn)(void);
typedef void* (__fastcall *Var64LookupFn)(void* scopedVar, void* ctx, void* a3);

#define RVA_VARSET_FACTORY 0x341F60u
#define RVA_VAR_LOOKUP     0x542280u
#define RVA_VARSET_ENTRYVT 0x277C418u
#define RVA_VARSET_VT      0x2775698u
#define RVA_GAME_SET_EXEC  0x364C60u
#define VAR64_MARK_OFF     505u
#define VAR64_HIGH_SUFFIX  "_hi"
#define VAR64_NAME_LIMIT   15u
#define VAR64_MARK_SET     0x53343656u
#define VAR64_MARK_ADD     0x53343641u
#define VAR64_MARK_LOG     0x5334364Cu
#define VAR64_NAME_OFF     200u
#define VAR64_SUBOBJ_OFF   88u
#define VAR64_PARAM_OFF    408u
#define VAR64_INST_SIZE    544u
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
static int g_var64OpCount = 0;

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

static long long Var64_ReadParamRaw(void* self, void* scope)
{
    unsigned char* img = (unsigned char*)GetModuleHandleA(NULL);
    long long fixed = 0;

    if (img == NULL || self == NULL) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_EFF_GETPARAM, 16)) return 0;
    ((Var64GetParamFn)(img + RVA_EFF_GETPARAM))((unsigned char*)self + 0x58, &fixed, scope, 0, (void*)1);
    return fixed;
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
    count = (int)*(unsigned char*)(bucket + 4);
    if (count <= 0 || count > 64) return 0;

    for (i = 0; i < count; ++i) {
        node = bucket + 48 * i;
        if (!ConsoleCmd_IsReadable(node, 48)) return 0;
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

static int Var64_ResolveGameVariable(void* self, void* ctx, long long* outValue,
                                     unsigned char** outAddr, char* nameBuf,
                                     unsigned int nameBufSize)
{
    unsigned char* img = Var64_Image();
    unsigned char* p = (unsigned char*)self;
    unsigned char* src;
    unsigned long long size;
    unsigned long long cap;
    unsigned long long k;

    if (img == NULL || p == NULL || nameBuf == NULL || nameBufSize < 40) return 0;
    if (!ConsoleCmd_IsReadable(p + VAR64_NAME_OFF, 32)) return 0;

    size = *(unsigned long long*)(p + VAR64_NAME_OFF + 16);
    cap = *(unsigned long long*)(p + VAR64_NAME_OFF + 24);
    if (size == 0 || size > 32) return 0;
    src = (cap <= 15) ? (p + VAR64_NAME_OFF) : *(unsigned char**)(p + VAR64_NAME_OFF);
    if (src == NULL || !ConsoleCmd_IsReadable(src, size)) return 0;
    for (k = 0; k < size; ++k) nameBuf[k] = (char)src[k];
    nameBuf[size] = 0;

    if (outValue != NULL) {
        *outValue = 0;
        if (ConsoleCmd_IsReadable(img + RVA_EFF_GETPARAM, 16)) {
            ((Var64GetParamFn)(img + RVA_EFF_GETPARAM))((void*)(p + 296), outValue, ctx, 0, (void*)1);
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
#define VAR64_KNOWN_NAME_BYTES 32

static char g_var64KnownNames[VAR64_KNOWN_NAME_LIMIT][VAR64_KNOWN_NAME_BYTES];
static int g_var64KnownNameCount = 0;

static void Var64_RememberSixtyFourBitName(const char* name)
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
    Plugin_Log("[v64lang] registered 64-bit name [%s] (total=%d)", name, g_var64KnownNameCount);
}

static int Var64_IsSixtyFourBitName(const char* name)
{
    int i;

    if (name == NULL || name[0] == 0) return 0;
    for (i = 0; i < g_var64KnownNameCount; ++i) {
        if (strcmp(g_var64KnownNames[i], name) == 0) return 1;
    }
    return 0;
}

static int Var64_MakeHighPartName(const char* name, char* out, unsigned int outSize)
{
    size_t n;

    if (name == NULL || out == NULL) return 0;
    n = strlen(name);
    if (n == 0 || n + 4 > outSize) return 0;
    if (n + 3 > VAR64_NAME_LIMIT) return 0;
    memcpy(out, name, n);
    out[n] = '_';
    out[n + 1] = 'h';
    out[n + 2] = 'i';
    out[n + 3] = 0;
    return 1;
}

static unsigned char* Var64_ResolveAddressByName(void* self, void* ctx, const char* name)
{
    unsigned char* img = Var64_Image();
    unsigned char* p = (unsigned char*)self;
    unsigned char* nm;
    unsigned char* addr;
    size_t n;

    if (img == NULL || p == NULL || name == NULL) return NULL;
    n = strlen(name);
    if (n == 0 || n > VAR64_NAME_LIMIT) return NULL;
    nm = p + VAR64_NAME_OFF;
    if (!ConsoleCmd_IsReadable(nm, 32)) return NULL;
    memcpy(nm, name, n + 1);
    *(unsigned long long*)(nm + 16) = (unsigned long long)n;
    *(unsigned long long*)(nm + 24) = (unsigned long long)VAR64_NAME_LIMIT;
    if (!ConsoleCmd_IsReadable(img + RVA_VAR_LOOKUP, 16)) return NULL;
    addr = (unsigned char*)((Var64LookupFn)(img + RVA_VAR_LOOKUP))
               ((void*)(p + VAR64_SUBOBJ_OFF), ctx, NULL);
    if (addr == NULL || !ConsoleCmd_IsReadable(addr, 8)) return NULL;
    return addr;
}

static void Var64_StoreSplit64(void* self, void* ctx, const char* name,
                               unsigned char* lowAddr, long long rawValue)
{
    long long value = rawValue / 100000;
    unsigned long long uv = (unsigned long long)value;
    unsigned int lo = (unsigned int)(uv & 0xFFFFFFFFu);
    unsigned int hi = (unsigned int)((uv >> 32) & 0xFFFFFFFFu);
    char hiName[40];

    if (lowAddr != NULL) *(long long*)lowAddr = (long long)lo;

    if (!Var64_MakeHighPartName(name, hiName, sizeof(hiName))) {
        Plugin_Log("[var64] name too long for high part: [%s]", name);
        return;
    }
    {
        unsigned char* hiAddr = Var64_ResolveAddressByName(self, ctx, hiName);
        if (hiAddr != NULL) {
            *(long long*)hiAddr = (long long)hi;
        } else {
            Plugin_Log("[var64] cannot store high part [%s]", hiName);
        }
    }
    Plugin_Log("[var64] split %s: value=%lld lo=%u hi=%u", name, value, lo, hi);
}

static long long Var64_LoadSplit64(void* self, void* ctx, const char* name,
                                   unsigned char* lowAddr, unsigned int* outLo,
                                   unsigned int* outHi)
{
    unsigned int lo = 0;
    unsigned int hi = 0;
    char hiName[40];

    if (lowAddr != NULL) lo = (unsigned int)(*(long long*)lowAddr);
    if (Var64_MakeHighPartName(name, hiName, sizeof(hiName))) {
        unsigned char* hiAddr = Var64_ResolveAddressByName(self, ctx, hiName);
        if (hiAddr != NULL) hi = (unsigned int)(*(long long*)hiAddr);
    }
    if (outLo != NULL) *outLo = lo;
    if (outHi != NULL) *outHi = hi;
    return (long long)(((unsigned long long)hi << 32) | (unsigned long long)lo) * 100000;
}

static long long __fastcall Var64_DoSetVariable64(void* self, void* ctx)
{
    long long delta = 0;
    unsigned char* addr = NULL;
    char name[40];

    if (!Var64_ResolveGameVariable(self, ctx, &delta, &addr, name, sizeof(name))) {
        Plugin_Log("[var64] set_variable64 failed to resolve");
        return 0;
    }
    Var64_StoreSplit64(self, ctx, name, addr, delta);
    Var64_RememberSixtyFourBitName(name);
    Plugin_Log("[var64] set_variable64 %s = %lld", name, delta / 100000);
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
    Var64_RememberSixtyFourBitName(name);
    Plugin_Log("[var64] add_to_variable64 %s: %lld + %lld = %lld",
               name, before / 100000, delta / 100000, after / 100000);
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
    Plugin_Log("[var64] log_variable64 %s = %lld (lo=%u hi=%u)",
               name, current / 100000, lo, hi);
    return current;
}

static long long __fastcall Var64_GameSyntaxDetour(void* self, void* ctx)
{
    unsigned int mark = 0;

    if (self != NULL && ConsoleCmd_IsReadable((unsigned char*)self + VAR64_MARK_OFF, 7)) {
        mark = *(unsigned int*)((unsigned char*)self + VAR64_MARK_OFF);
    }
    if (mark == VAR64_MARK_SET) return Var64_DoSetVariable64(self, ctx);
    if (mark == VAR64_MARK_ADD) return Var64_DoAddToVariable64(self, ctx);
    if (mark == VAR64_MARK_LOG) return Var64_DoLogVariable64(self, ctx);
    if (g_var64OrigGameSetExec != NULL) return g_var64OrigGameSetExec(self, ctx);
    return 0;
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

static int Var64_MakeGameVarInstance(void* scope, const char* name, void** outInst, void** outAddr)
{
    unsigned char* img = Var64_Image();
    unsigned char* inst;
    unsigned char* nameDst;
    unsigned char* addr;
    size_t n;

    if (outInst != NULL) *outInst = NULL;
    if (outAddr != NULL) *outAddr = NULL;
    if (img == NULL || scope == NULL || name == NULL) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_VARSET_FACTORY, 16)) return 0;

    n = strlen(name);
    if (n == 0 || n > 15) {
        Plugin_Log("[var64] name length %u unsupported (need 1..15)", (unsigned)n);
        return 0;
    }

    inst = (unsigned char*)((Var64FactoryFn)(img + RVA_VARSET_FACTORY))();
    if (inst == NULL) return 0;

    nameDst = inst + VAR64_NAME_OFF;
    if (!ConsoleCmd_IsReadable(nameDst, 32)) {
        Plugin_Log("[var64] instance name field not writable");
        return 0;
    }
    memset(nameDst, 0, 32);
    memcpy(nameDst, name, n);
    *(unsigned long long*)(nameDst + 16) = (unsigned long long)n;
    *(unsigned long long*)(nameDst + 24) = 15ULL;
    Plugin_Log("[var64] wrote name [%s] to %p (len=%u)", name, nameDst, (unsigned)n);

    if (!ConsoleCmd_IsReadable(img + RVA_VAR_LOOKUP, 16)) return 0;
    addr = (unsigned char*)((Var64LookupFn)(img + RVA_VAR_LOOKUP))(inst + VAR64_SUBOBJ_OFF, scope, NULL);
    if (addr == NULL || !ConsoleCmd_IsReadable(addr, 8)) {
        Plugin_Log("[var64] lookup returned unusable addr");
        return 0;
    }

    if (outInst != NULL) *outInst = inst;
    if (outAddr != NULL) *outAddr = addr;
    return 1;
}

static void __fastcall ExecVar64Diag(void* self, void* scope)
{
    long long found = 0;
    int i;

    Effect_FlushPendingTooltip();
    Plugin_Log("[v64diag] self=%p scope=%p", self, scope);
    if (scope != NULL && ConsoleCmd_IsReadable(scope, 0x200)) {
        for (i = 0; i < 0x200; i += 8) {
            void* v = *(void**)((unsigned char*)scope + i);
            unsigned char* p = (unsigned char*)v;
            int looksPtr = 0;
            if (v != NULL && ConsoleCmd_IsReadable(p, 8)) {
                looksPtr = 1;
            }
            if (looksPtr || i < 0x40) {
                Plugin_Log("[v64diag] scope+0x%03X = %p", i, v);
            }
        }
    } else {
        Plugin_Log("[v64diag] scope not readable");
    }
    if (self != NULL && ConsoleCmd_IsReadable(self, 0x200)) {
        for (i = 0; i < 0x200; i += 8) {
            void* v = *(void**)((unsigned char*)self + i);
            if (v != NULL && ConsoleCmd_IsReadable((unsigned char*)v, 8)) {
                Plugin_Log("[v64diag] self+0x%03X = %p", i, v);
            }
        }
    }
    {
        void* cands[6];
        const char* tags[6] = { "scope", "s1C8", "s1E0", "s160", "s168", "s130" };
        int k;

        cands[0] = scope;
        cands[1] = (scope != NULL && ConsoleCmd_IsReadable((unsigned char*)scope + 0x1C8, 8))
                   ? *(void**)((unsigned char*)scope + 0x1C8) : NULL;
        cands[2] = (scope != NULL && ConsoleCmd_IsReadable((unsigned char*)scope + 0x1E0, 8))
                   ? *(void**)((unsigned char*)scope + 0x1E0) : NULL;
        cands[3] = (scope != NULL && ConsoleCmd_IsReadable((unsigned char*)scope + 0x160, 8))
                   ? *(void**)((unsigned char*)scope + 0x160) : NULL;
        cands[4] = (scope != NULL && ConsoleCmd_IsReadable((unsigned char*)scope + 0x168, 8))
                   ? *(void**)((unsigned char*)scope + 0x168) : NULL;
        cands[5] = (self != NULL && ConsoleCmd_IsReadable((unsigned char*)self + 0x130, 8))
                   ? *(void**)((unsigned char*)self + 0x130) : NULL;

        for (k = 0; k < 6; ++k) {
            unsigned char* c = (unsigned char*)cands[k];
            int mask = 0;
            void* buckets = NULL;
            if (c == NULL) { Plugin_Log("[v64diag] %s = NULL", tags[k]); continue; }
            if (ConsoleCmd_IsReadable(c + 24, 8)) {
                buckets = *(void**)(c + 24);
                mask = *(int*)(c + 36);
            }
            Plugin_Log("[v64diag] %s = %p  buckets=%p mask=%d",
                       tags[k], c, buckets, mask);
            if (Var64_LookupInScope(c, "dshprobe", &found)) {
                Plugin_Log("[v64diag] *** FOUND via %s: dshprobe = %lld (%.5f)",
                           tags[k], found, (double)found / EFF_FIXED_SCALE);
            }
        }
    }
    {
        void* inst = NULL;
        void* addr = NULL;
        if (Var64_MakeGameVarInstance(scope, "dshprobe", &inst, &addr)) {
            unsigned char* node = (unsigned char*)addr - 40;
            unsigned char* namep;
            unsigned long long cap;
            unsigned long long size;
            long long v = *(long long*)addr;

            Plugin_Log("[v64diag] *** GAME-API OK: inst=%p addr=%p value=%lld (%.5f)",
                       inst, addr, v, (double)v / EFF_FIXED_SCALE);
            if (ConsoleCmd_IsReadable(node, 48)) {
                cap = *(unsigned long long*)(node + 32);
                size = *(unsigned long long*)(node + 24);
                namep = (cap <= 15) ? (node + 8) : *(unsigned char**)(node + 8);
                Plugin_Log("[v64diag] node=%p hash=0x%X bucketIdx=%d size=%u cap=%u",
                           node, *(unsigned int*)node, *(unsigned char*)(node + 4),
                           (unsigned)size, (unsigned)cap);
                if (namep != NULL && size > 0 && size < 64 &&
                    ConsoleCmd_IsReadable(namep, (unsigned long long)size)) {
                    char tmp[80];
                    unsigned long long i2;
                    unsigned long long cn = (size < 79) ? size : 79;
                    for (i2 = 0; i2 < cn; ++i2) tmp[i2] = (char)namep[i2];
                    tmp[cn] = 0;
                    Plugin_Log("[v64diag] node name = [%s]", tmp);
                } else {
                    Plugin_Log("[v64diag] node name unreadable");
                }
            } else {
                Plugin_Log("[v64diag] node not readable at %p", node);
            }
        } else {
            Plugin_Log("[v64diag] GAME-API failed for dshprobe");
        }
    }
}

static void Var64_LogOp(int slot, const char* op, long long raw)
{
    ++g_var64OpCount;
    Plugin_Log("[var64] #%d %s slot=%s raw=%lld value=%.5f slotnow=%.5f",
               g_var64OpCount, op, Var64_SlotName(slot), raw,
               (double)raw / EFF_FIXED_SCALE,
               (double)g_var64Slots[slot] / EFF_FIXED_SCALE);
}

static void __fastcall ExecVar64SetA(void* self, void* scope)
{
    long long raw;
    Effect_FlushPendingTooltip();
    raw = Var64_ReadParamRaw(self, scope);
    {
        unsigned char* p = (unsigned char*)self;
        int i;
        Plugin_Log("[v64par] self=%p raw=%lld", self, raw);
        if (ConsoleCmd_IsReadable(p + 0x40, 0x1E0)) {
            for (i = 0x40; i < 0x220; i += 8) {
                if (i == 0x58 || i == 0x60) continue;
                Plugin_Log("[v64par] self+0x%03X = %p", i, *(void**)(p + i));
            }
        }
        {
            unsigned char* nm = p + VAR64_NAME_OFF;
            unsigned char* pm = p + VAR64_PARAM_OFF;
            unsigned long long c1 = 0, s1 = 0, c2 = 0, s2 = 0;
            if (ConsoleCmd_IsReadable(nm, 32)) {
                s1 = *(unsigned long long*)(nm + 16);
                c1 = *(unsigned long long*)(nm + 24);
            }
            if (ConsoleCmd_IsReadable(pm, 32)) {
                s2 = *(unsigned long long*)(pm + 16);
                c2 = *(unsigned long long*)(pm + 24);
            }
            Plugin_Log("[v64par] nameField(+200) size=%u cap=%u ; paramField(+408) size=%u cap=%u",
                       (unsigned)s1, (unsigned)c1, (unsigned)s2, (unsigned)c2);
            if (s1 > 0 && s1 < 32 && ConsoleCmd_IsReadable(nm, (unsigned long long)s1)) {
                char t1[40];
                unsigned long long k;
                for (k = 0; k < s1; ++k) t1[k] = (char)nm[k];
                t1[s1] = 0;
                Plugin_Log("[v64par] nameField text = [%s]", t1);
            }
            if (s2 > 0 && s2 < 32 && ConsoleCmd_IsReadable(pm, (unsigned long long)s2)) {
                char t2[40];
                unsigned long long k;
                for (k = 0; k < s2; ++k) t2[k] = (char)pm[k];
                t2[s2] = 0;
                Plugin_Log("[v64par] paramField text = [%s]", t2);
            }
        }
    }
    Var64_SetSlot(0, raw);
    Var64_LogOp(0, "set", raw);
    if (scope != NULL) {
        void* inst2 = NULL;
        void* addr2 = NULL;
        if (Var64_MakeGameVarInstance(scope, "v64gv", &inst2, &addr2)) {
            *(long long*)addr2 = raw;
            Plugin_Log("[var64] wrote game var v64gv = %lld at %p", *(long long*)addr2, addr2);
        }
    }
}

static void __fastcall ExecVar64AddA(void* self, void* scope)
{
    long long raw;
    Effect_FlushPendingTooltip();
    raw = Var64_ReadParamRaw(self, scope);
    Var64_AddSlot(0, raw);
    Var64_LogOp(0, "add", raw);
}

static void __fastcall ExecVar64ShowA(void* self, void* scope)
{
    Effect_FlushPendingTooltip();
    Var64_LogOp(0, "show", 0);
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

#define RVA_VARTEXT_HANDLER     0x12CF2B0u
#define VAR64_LANG_NAME_MAX     160u

typedef void* (__fastcall *Var64VarTextHandlerFn)(void* ctx, const char* text,
                                                  const char* textEnd, void* out, int depth);

static Var64VarTextHandlerFn g_var64OrigVarTextHandler = NULL;
static int Var64_LangResolveSlotValue(void* ctx, const char* name, long long* outValue);
static void Var64_LangAppendDecimalText(void* out, long long value);

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
    long long loValue = 0;
    long long hiValue = 0;
    unsigned long long combined;
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
    memcpy(hiName + n, VAR64_HIGH_SUFFIX, 4);

    if (!Var64_IsSixtyFourBitName(name)) {
        if (!Var64_LangResolveSlotValue(ctx, hiName, &hiValue) || hiValue == 0) {
            return g_var64OrigVarTextHandler(ctx, text, textEnd, out, depth);
        }
        Var64_RememberSixtyFourBitName(name);
        if (!Var64_LangResolveSlotValue(ctx, name, &loValue)) {
            return g_var64OrigVarTextHandler(ctx, text, textEnd, out, depth);
        }
    } else {
        if (!Var64_LangResolveSlotValue(ctx, name, &loValue)) {
            return g_var64OrigVarTextHandler(ctx, text, textEnd, out, depth);
        }
        if (!Var64_LangResolveSlotValue(ctx, hiName, &hiValue)) hiValue = 0;
    }

    combined = ((unsigned long long)(unsigned int)hiValue << 32)
             | (unsigned long long)(unsigned int)loValue;
    Var64_LangAppendDecimalText(out, (long long)combined);
    Plugin_Log("[v64lang] [%s] lo=%lld hi=%lld full=%lld",
               name, loValue, hiValue, (long long)combined);
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
    memcpy(nameField, name, n);
    *(unsigned long long*)(nameField + 16) = (unsigned long long)n;
    *(unsigned long long*)(nameField + 24) = 15ULL;

    ((Var64CtxResolveFn)(*(void**)((char*)vtable + 0x20)))(ctx, &resolved, nameField);
    *outValue = (long long)(intptr_t)resolved;
    return 1;
}

static void Var64_LangAppendDecimalText(void* out, long long value)
{
    CmdString* field = (CmdString*)out;
    unsigned char* img;
    char digits[24];
    char text[32];
    int d = 0;
    int k = 0;
    int neg = (value < 0);
    unsigned long long uv = (unsigned long long)(neg ? -value : value);

    if (field == NULL || !ConsoleCmd_IsReadable(field, 32)) return;
    img = Var64_Image();
    if (img == NULL) return;
    if (!ConsoleCmd_IsReadable(img + RVA_STRING_APPEND, 16)) return;

    if (uv == 0) digits[d++] = '0';
    while (uv > 0 && d < 22) {
        digits[d++] = (char)('0' + (int)(uv % 10ULL));
        uv /= 10ULL;
    }
    if (neg) text[k++] = '-';
    while (d > 0) text[k++] = digits[--d];
    text[k] = 0;

    ((Var64StringAppendFn)(img + RVA_STRING_APPEND))((void**)field, text, (size_t)k);
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
    orig = InlineHook_Install(img + RVA_VARTEXT_HANDLER, (void*)Var64_VarTextBridgeDetour);
    if (orig == NULL) {
        Plugin_Log("[v64lang] var text hook install failed");
        return;
    }
    g_var64OrigVarTextHandler = (Var64VarTextHandlerFn)orig;
    Plugin_Log("[v64lang] var text hook installed, orig=%p", orig);
}

EFF_DEF(gamesetvar64, "set_variable64",
        "Sets a 64-bit script variable. Same syntax as set_variable.",
        "EFFECT_SET_VARIABLE64", &ExecVar64GameSyntax)

EFF_DEF(gameaddvar64, "add_to_variable64",
        "Adds to a 64-bit script variable. Same syntax as set_variable.",
        "EFFECT_ADD_TO_VARIABLE64", &ExecVar64GameSyntax)

EFF_DEF(gamelogvar64, "log_variable64",
        "Logs a 64-bit script variable in full precision. Same syntax as set_variable.",
        "EFFECT_LOG_VARIABLE64", &ExecVar64GameSyntax)

static EffectDef* g_var64EffectDefs[] = {
    &gamesetvar64_def,
    &gameaddvar64_def,
    &gamelogvar64_def
};

#define VAR64_EFFECT_COUNT (int)(sizeof(g_var64EffectDefs) / sizeof(g_var64EffectDefs[0]))

int Var64_RegisterEffects(void)
{
    unsigned char* img;
    int n;

    gamesetvar64_fill();
    gameaddvar64_fill();
    gamelogvar64_fill();

    gamesetvar64_def.factory = Var64_SetVariable64Factory;
    gameaddvar64_def.factory = Var64_AddToVariable64Factory;
    gamelogvar64_def.factory = Var64_LogVariable64Factory;

    n = Effect_RegistryRegisterAll(g_var64EffectDefs, VAR64_EFFECT_COUNT);

    img = Var64_Image();
    if (img != NULL) {
        if (gamesetvar64_def.state == EFF_STATE_OK) {
            gamesetvar64_def.entryVt[0] = *(void**)(img + RVA_VARSET_ENTRYVT);
        }
        if (gameaddvar64_def.state == EFF_STATE_OK) {
            gameaddvar64_def.entryVt[0] = *(void**)(img + RVA_VARSET_ENTRYVT);
        }
        if (gamelogvar64_def.state == EFF_STATE_OK) {
            gamelogvar64_def.entryVt[0] = *(void**)(img + RVA_VARSET_ENTRYVT);
        }
        Plugin_Log("[var64] game-syntax entryVt: set=%p add=%p log=%p",
                   gamesetvar64_def.entryVt[0], gameaddvar64_def.entryVt[0],
                   gamelogvar64_def.entryVt[0]);
    }

    Var64_InstallGameSyntaxHook();

    Plugin_Log("[eff] var64 effects registered: %d/%d", n, VAR64_EFFECT_COUNT);
    return n;
}
