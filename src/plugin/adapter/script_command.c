#include <stdio.h>
#include "native_adapter.h"
#include "../SDK_RVA/console/console_cmd.h"

static long long __fastcall ScriptBindingsCommand(CmdResult* out, CmdArgs* args)
{
    NativeScriptTemplate templates[4];
    char message[256];
    int i;
    (void)args;
    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);
    for (i = 0; i < 4; ++i) {
        if (!NativeAdapter_ScriptTemplate(i, &templates[i])) {
            ConsoleCmd_SetMessage(out, NativeAdapter_RegistryDiagnostic());
            return (long long)out;
        }
    }
    _snprintf_s(message, sizeof(message), _TRUNCATE,
        "SCRIPT_BINDINGS_READY effect=0x%X bool=0x%X value=0x%X variable=0x%X allocator=0x%X static_tokens=%u",
        templates[0].vt, templates[1].vt, templates[2].vt, templates[3].vt,
        NativeAdapter_RegistryRva(NS_GAME_ALLOC), NativeAdapter_StaticTokenCount());
    ConsoleCmd_SetMessage(out, message); out->ok = 1;
    return (long long)out;
}

int NativeAdapter_RegisterScriptDiagnostic(void)
{
    const CmdDef def = {"plugin_script_bindings", "Report validated script registration bindings", NULL, 0, {0}, ScriptBindingsCommand};
    return ConsoleCmd_RegisterAll(&def, 1);
}
