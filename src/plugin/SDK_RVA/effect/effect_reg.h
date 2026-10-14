#pragma once

#define EFF_VT_SLOTS         25
#define EFF_VT_TOOLTIP       0x38
#define EFF_VT_EXEC          0x68
#define EFF_ENTRY_VT_FACTORY 0x08
#define EFF_PARAMDESC_SIZE   0x68
#define EFF_SSO_MAX          15
#define EFF_FIXED_SCALE      100000.0

#include "../../adapter/native_adapter.h"

#define EFF_STATE_PENDING    0
#define EFF_STATE_OK         1
#define EFF_STATE_FAILED     2

typedef void (__fastcall *EffectExecFn)(void* self, void* scope);
typedef unsigned int (__fastcall *EffectScopeFn)(void* self);

typedef struct EffectDef {
    const char*  name;
    const char*  desc;
    const char*  locKey;
    EffectExecFn exec;
    EffectScopeFn supportedScopes;
    void*      (*factory)(void);
    void*      (*tooltip)(void* self, void* out, void* ctx);
    int          tokenId;
    int          state;
    void*        vt[EFF_VT_SLOTS];
    void*        entryVt[4];
    unsigned char entry[16];
    void* entryParser;
} EffectDef;

int  Effect_RegistryReady(void);
int  Effect_RegistryRegister(EffectDef* def);
int  Effect_RegistryRegisterAll(EffectDef** defs, int count);
int  Effect_RegistryRegisteredCount(void);
unsigned int __fastcall Effect_ScopeAny(void* self);

void* Effect_NewInstance(void* vt);
void* Effect_BuildTooltip(void* self, void* out, void* ctx, const char* locKey);
float Effect_ParamFloat(void* self, void* ctx);
void  Effect_SetParamFixed(void* self, double value);
void  Effect_FlushPendingTooltip(void);

#define EFF_DEF(sym, NM, DS, LK, FN)                                        \
    static EffectDef sym##_def;                                             \
    static void* __fastcall sym##_factory(void)                             \
    {                                                                       \
        return Effect_NewInstance(sym##_def.vt);                            \
    }                                                                       \
    static void* __fastcall sym##_tooltip(void* s, void* o, void* c)        \
    {                                                                       \
        return Effect_BuildTooltip(s, o, c, sym##_def.locKey);              \
    }                                                                       \
    static void sym##_fill(void)                                            \
    {                                                                       \
        sym##_def.name   = NM;                                              \
        sym##_def.desc   = DS;                                              \
        sym##_def.locKey = LK;                                              \
        sym##_def.exec   = FN;                                              \
        sym##_def.factory = sym##_factory;                                  \
        sym##_def.tooltip = sym##_tooltip;                                  \
    }
