#pragma once

int  InlineHook_Init(void);
void* InlineHook_Install(void* target, void* detour);
int  InlineHook_InstallInto(void* target, void* detour, void** original);
int  InlineHook_Remove(void* target);
