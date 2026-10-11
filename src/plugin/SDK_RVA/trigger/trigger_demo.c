#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "trigger_reg.h"

extern void Plugin_Log(const char* fmt, ...);

static int __fastcall PredicateTrue(void* self, void* scope)
{
    (void)self; (void)scope; return 1;
}

static int __fastcall PredicateFalse(void* self, void* scope)
{
    (void)self; (void)scope; return 0;
}

static int __fastcall PredicateHasScope(void* self, void* scope)
{
    (void)self; return scope != NULL;
}

TRG_BOOL_DEF(demo_true, "plugin_trigger_true", "Plugin trigger returning true.", "PLUGIN_TRIGGER_TRUE", PredicateTrue)
TRG_BOOL_DEF(demo_false, "plugin_trigger_false", "Plugin trigger returning false.", "PLUGIN_TRIGGER_FALSE", PredicateFalse)
TRG_BOOL_DEF(demo_scope, "plugin_trigger_scope", "Plugin trigger checking a scope pointer.", "PLUGIN_TRIGGER_SCOPE", PredicateHasScope)

static TriggerDef g_bulkDefs[256];
static char g_bulkNames[256][32];

static void TriggerDemo_OptionalBulk(void)
{
    char enabled[8];
    int i, count = 0;
    if (GetEnvironmentVariableA("HOI4_TRIGGER_REG_STRESS", enabled, sizeof(enabled)) != 1 || enabled[0] != '1') return;
    for (i = 0; i < 256; ++i) {
        if (g_bulkDefs[i].state != TRG_STATE_OK) {
            memcpy(&g_bulkDefs[i], &demo_true_def, sizeof(TriggerDef));
            _snprintf_s(g_bulkNames[i], sizeof(g_bulkNames[i]), _TRUNCATE, "plugin_trigger_bulk_%03d", i);
            g_bulkDefs[i].name = g_bulkNames[i];
            g_bulkDefs[i].entry = NULL;
            g_bulkDefs[i].tokenId = 0;
            g_bulkDefs[i].state = TRG_STATE_PENDING;
        }
        if (Trigger_RegistryRegister(&g_bulkDefs[i])) ++count;
    }
    Plugin_Log("[trg] stress startup registered=%d/256 total=%d", count, Trigger_RegistryRegisteredCount());
}

int TriggerDemo_Register(void)
{
    TriggerDef* defs[] = { &demo_true_def, &demo_false_def, &demo_scope_def };
    TriggerDef collision;
    int result;
    demo_true_fill(); demo_false_fill(); demo_scope_fill();
    result = Trigger_RegistryRegisterAll(defs, 3);
    if (result == 3) {
        int before = Trigger_RegistryRegisteredCount();
        int repeat = Trigger_RegistryRegisterAll(defs, 3);
        int rejected;
        memcpy(&collision, &demo_true_def, sizeof(collision));
        collision.name = "always"; collision.state = TRG_STATE_PENDING; collision.entry = NULL;
        rejected = Trigger_RegistryRegister(&collision);
        Plugin_Log("[trg] selfcheck: repeat=%d count=%d/%d builtin_collision=%d",
                   repeat, Trigger_RegistryRegisteredCount(), before, rejected);
        memcpy(&collision, &demo_true_def, sizeof(collision));
        collision.state = TRG_STATE_PENDING; collision.entry = NULL;
        rejected = Trigger_RegistryRegister(&collision);
        Plugin_Log("[trg] duplicate definition rejected=%d count=%d", !rejected, Trigger_RegistryRegisteredCount());
        TriggerDemo_OptionalBulk();
    }
    return result;
}
