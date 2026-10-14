#pragma once

#define VAR64_SLOT_COUNT 9
#define VAR64_EFFECT_COUNT 7

int       Var64_RegisterEffects(void);
int       Var64_RegisterLoadGameCommand(void);
void      Var64_InstallLanguageBridge(void);
int       Var64_SyntaxHooksReady(void);
int       Var64_LanguageBridgeReady(void);
long long Var64_GetSlot(int slot);
void      Var64_SetSlot(int slot, long long value);
void      Var64_AddSlot(int slot, long long delta);
const char* Var64_SlotName(int slot);
int Var64_ReadStoredContainerRaw(void* container, const char* name, long long* out);
