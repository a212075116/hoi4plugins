#pragma once

#define TRG_VT_SLOTS 23
#define TRG_VT_TOOLTIP 21
#define TRG_VT_EVAL 22
#define TRG_PARAM_BOOL_OFFSET 88
#define TRG_STATE_PENDING 0
#define TRG_STATE_OK 1
#define TRG_STATE_FAILED 2

typedef int (__fastcall *TriggerPredicateFn)(void* self, void* scope);
typedef unsigned char (__fastcall *TriggerEvalFn)(void* self, void* scope);
typedef void* (__fastcall *TriggerTooltipFn)(void* self, void* out, void* ctx,
                                           unsigned char inverted, int indent);

typedef struct TriggerDef {
    const char* name;
    const char* desc;
    const char* locKey;
    TriggerEvalFn eval;
    void* (__fastcall *factory)(void);
    TriggerTooltipFn tooltip;
    int tokenId;
    int state;
    void* vtStorage[TRG_VT_SLOTS + 1];
    void* entryVtStorage[3];
    void* entry;
} TriggerDef;

int Trigger_RegistryReady(void);
int Trigger_RegistryRegister(TriggerDef* def);
int Trigger_RegistryRegisterAll(TriggerDef** defs, int count);
int Trigger_RegistryRegisteredCount(void);
int Trigger_ValidName(const char* name);
int Trigger_ParamBool(void* self);
unsigned char Trigger_EvaluateBool(void* self, void* scope, TriggerPredicateFn predicate);
void* Trigger_NewInstance(void* vt);
void* Trigger_BuildTooltip(void* self, void* out, void* ctx,
                          unsigned char inverted, const char* locKey);

#define TRG_BOOL_DEF(sym, NM, DS, LK, FN)                                    \
    static TriggerDef sym##_def;                                            \
    static void* __fastcall sym##_factory(void)                             \
    { return Trigger_NewInstance(sym##_def.vtStorage + 1); }                 \
    static unsigned char __fastcall sym##_eval(void* self, void* scope)      \
    { return Trigger_EvaluateBool(self, scope, FN); }                        \
    static void* __fastcall sym##_tooltip(void* self, void* out, void* ctx,   \
                                          unsigned char invert, int indent) \
    { (void)indent; return Trigger_BuildTooltip(self, out, ctx, invert, LK); }\
    static void sym##_fill(void)                                            \
    {                                                                       \
        sym##_def.name = NM; sym##_def.desc = DS; sym##_def.locKey = LK;      \
        sym##_def.eval = sym##_eval; sym##_def.factory = sym##_factory;      \
        sym##_def.tooltip = sym##_tooltip;                                  \
    }
