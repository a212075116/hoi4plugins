#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "../console/console_cmd.h"

static long long __fastcall AchievementStatus(CmdResult* out, CmdArgs* args) {
    unsigned char* base = (unsigned char*)GetModuleHandleW(NULL);
    IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)base;
    IMAGE_NT_HEADERS64* nt;
    const unsigned char* manager;
    const unsigned char* state;
    char text[768];
    (void)args;
    ConsoleCmd_InitResult(out);
    if (!base || dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 4096) {
        ConsoleCmd_SetMessage(out, "[error] Achievement probe: invalid host image."); return (long long)out;
    }
    nt = (IMAGE_NT_HEADERS64*)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE || nt->FileHeader.TimeDateStamp != 0x6AA123BB || nt->OptionalHeader.SizeOfImage != 0x37EC000) {
        ConsoleCmd_SetMessage(out, "[error] Achievement probe: unsupported game version; no state read."); return (long long)out;
    }
    manager = *(const unsigned char**)(base + 0x3330460);
    state = *(const unsigned char**)(base + 0x332F260);
    if (!ConsoleCmd_IsReadable(manager, 168) || !ConsoleCmd_IsReadable(state, 193)) {
        ConsoleCmd_SetMessage(out, "[warning] Achievement probe: game context not ready; no state changed."); return (long long)out;
    }
    _snprintf_s(text, sizeof(text), _TRUNCATE,
        "[info] Achievement probe ONLY; compatibility hooks NOT enabled. "
        "ironman=%u definitions=%d pending=%d completed=%d excluded=%d "
        "manager_flags_A0_A4=%u,%u,%u,%u,%u "
        "debug_flag=%u debug_or_crash_log_flag=%u. "
        "No SetAchievement/StoreStats/ClearAchievement/ResetAllStats calls.",
        state[192] & 1, *(const int*)(manager + 28), *(const int*)(manager + 52),
        *(const int*)(manager + 76), *(const int*)(manager + 100),
        manager[160], manager[161], manager[162], manager[163], manager[164],
        base[0x34530D4], base[0x332EC69]);
    ConsoleCmd_SetMessage(out, text); out->ok = 1;
    return (long long)out;
}

int AchievementProbe_RegisterCommands(void) {
    CmdDef def = {"achievementstatus", "Read achievement state without unlocking or changing eligibility", "achstatus", 0, {0}, AchievementStatus};
    return ConsoleCmd_RegisterAll(&def, 1);
}
