#pragma once
#include <stddef.h>

#define TRG_VT_SLOTS 23
#define TRG_MAX_VT_SLOTS 26
#define TRG_TEMPLATE_BOOL 0
#define TRG_TEMPLATE_VALUE 1
#define TRG_TEMPLATE_VARIABLE 2
#define TRG_VT_TOOLTIP 21
#define TRG_VT_EVAL 22
#define TRG_PARAM_BOOL_OFFSET NativeAdapter_Field(NFL_PARAM_FIRST)
#define TRG_STATE_PENDING 0
#define TRG_STATE_OK 1
#define TRG_STATE_FAILED 2

typedef int (__fastcall *TriggerPredicateFn)(void* self, void* scope);
typedef unsigned char (__fastcall *TriggerEvalFn)(void* self, void* scope);
typedef void* (__fastcall *TriggerTooltipFn)(void* self, void* out, void* ctx,
                                           unsigned char inverted, int indent);
struct TriggerScopeView;

typedef struct TriggerDef {
    const char* name;
    const char* desc;
    const char* locKey;
    TriggerEvalFn eval;
    void* (__fastcall *factory)(void);
    TriggerTooltipFn tooltip;
    int tokenId;
    int state;
    int parameterTemplate;
    void* valueGetter;
    void* vtStorage[TRG_MAX_VT_SLOTS + 1];
    void* entryVtStorage[3];
    void* entry;
    int (__fastcall *operandReader)(void* self, const struct TriggerScopeView* scope, unsigned int offset, long long* out);
} TriggerDef;

typedef struct TriggerScopeView {
    void* nativeContext;
    unsigned int mask;
} TriggerScopeView;

typedef long long (__fastcall *TriggerValueFn)(void* self, const TriggerScopeView* scope);
int Trigger_ScopeView(void* context, TriggerScopeView* out);
int Trigger_ReadRawParameter(void* self, const TriggerScopeView* scope, unsigned int offset, long long* out);
int Trigger_CompareRaw(long long left, long long right, int token);
unsigned char Trigger_EvaluateValue(void* self, void* scope, TriggerValueFn value);
unsigned char __fastcall Trigger_EvaluateVariable(void* self, void* scope);
void* Trigger_NewTypedInstance(TriggerDef* def);
void* Trigger_TypedTooltip(TriggerDef* def, void* self, void* out, void* ctx, unsigned char invert, int indent);
int Trigger_FormatRaw(long long raw, char* out, size_t capacity);

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

#define TRG_VALUE_DEF(sym, NM, DS, LK, FN)                                   \
    static TriggerDef sym##_def;                                           \
    static void* __fastcall sym##_factory(void)                            \
    { return Trigger_NewTypedInstance(&sym##_def); }                        \
    static unsigned char __fastcall sym##_eval(void* s, void* c)            \
    { return Trigger_EvaluateValue(s, c, FN); }                             \
    static long long* __fastcall sym##_value(void* s, long long* out, void* c) \
    { TriggerScopeView view; *out = Trigger_ScopeView(c, &view) ? FN(s, &view) : 0; return out; } \
    static void* __fastcall sym##_tooltip(void* s, void* o, void* c, unsigned char inv, int indent) \
    { return Trigger_TypedTooltip(&sym##_def, s, o, c, inv, indent); }       \
    static void sym##_fill(void)                                           \
    { sym##_def.name=NM; sym##_def.desc=DS; sym##_def.locKey=LK;             \
      sym##_def.eval=sym##_eval; sym##_def.factory=sym##_factory;           \
      sym##_def.tooltip=sym##_tooltip; sym##_def.parameterTemplate=TRG_TEMPLATE_VALUE; \
      sym##_def.valueGetter=(void*)sym##_value; }

#define TRG_VARIABLE_DEF(sym, NM, DS, LK)                                   \
    static TriggerDef sym##_def;                                           \
    static void* __fastcall sym##_factory(void)                            \
    { return Trigger_NewTypedInstance(&sym##_def); }                        \
    static void* __fastcall sym##_tooltip(void* s, void* o, void* c, unsigned char inv, int indent) \
    { return Trigger_TypedTooltip(&sym##_def, s, o, c, inv, indent); }       \
    static void sym##_fill(void)                                           \
    { sym##_def.name=NM; sym##_def.desc=DS; sym##_def.locKey=LK;             \
      sym##_def.eval=Trigger_EvaluateVariable; sym##_def.factory=sym##_factory; \
      sym##_def.tooltip=sym##_tooltip; sym##_def.parameterTemplate=TRG_TEMPLATE_VARIABLE; }
