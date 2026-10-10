#pragma once

#include "effect_reg.h"

#define VAR64_SLOT_COUNT 9

int       Var64_RegisterEffects(void);
long long Var64_GetSlot(int slot);
void      Var64_SetSlot(int slot, long long value);
void      Var64_AddSlot(int slot, long long delta);
const char* Var64_SlotName(int slot);
