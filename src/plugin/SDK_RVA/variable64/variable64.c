#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "effect_reg.h"
#include "variable64.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void (__fastcall *Var64GetParamFn)(void* a1, void* out, void* ctx, void* a4, void* a5);

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
    ((Var64GetParamFn)(img + RVA_EFF_GETPARAM))((unsigned char*)self + 0x58, &fixed, scope, 0, 0);
    return fixed;
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
    Var64_SetSlot(0, raw);
    Var64_LogOp(0, "set", raw);
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

EFF_DEF(var64seta, "var64_set_a", "Sets 64-bit variable slot a",
        "EFFECT_VAR64_SET_A", &ExecVar64SetA)

EFF_DEF(var64adda, "var64_add_a", "Adds to 64-bit variable slot a",
        "EFFECT_VAR64_ADD_A", &ExecVar64AddA)

EFF_DEF(var64showa, "var64_show_a", "Logs 64-bit variable slot a",
        "EFFECT_VAR64_SHOW_A", &ExecVar64ShowA)

static EffectDef* g_var64EffectDefs[] = {
    &var64seta_def,
    &var64adda_def,
    &var64showa_def
};

#define VAR64_EFFECT_COUNT (int)(sizeof(g_var64EffectDefs) / sizeof(g_var64EffectDefs[0]))

int Var64_RegisterEffects(void)
{
    int n;
    var64seta_fill();
    var64adda_fill();
    var64showa_fill();
    n = Effect_RegistryRegisterAll(g_var64EffectDefs, VAR64_EFFECT_COUNT);
    Plugin_Log("[eff] var64 effects registered: %d/%d", n, VAR64_EFFECT_COUNT);
    return n;
}
