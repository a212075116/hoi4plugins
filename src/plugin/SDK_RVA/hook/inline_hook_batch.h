#pragma once
#include "MinHook.h"

static inline int InlineHook_EnableQueuedBatch(void* const* targets, int count)
{
    int i;
    for (i = 0; i < count; ++i) {
        if (MH_QueueEnableHook(targets[i]) != MH_OK) return 0;
    }
    return MH_ApplyQueued() == MH_OK;
}

static inline void InlineHook_CleanupCreatedBatch(void* const* targets, int count)
{
    int i;
    for (i = 0; i < count; ++i) {
        MH_QueueDisableHook(targets[i]);
        MH_DisableHook(targets[i]);
    }
    MH_ApplyQueued();
    for (i = 0; i < count; ++i) MH_RemoveHook(targets[i]);
}
