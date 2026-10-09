#pragma once

#define EFF_VT_SLOTS         25
#define EFF_VT_TOOLTIP       0x38
#define EFF_VT_EXEC          0x68
#define EFF_ENTRY_VT_FACTORY 0x08
#define EFF_PARAMDESC_SIZE   0x68
#define EFF_SSO_MAX          15
#define EFF_FIXED_SCALE      100000.0

#define RVA_EFFECT_MAP      0x03330000u
#define RVA_ADD_TOKEN       0x024BB460u
#define RVA_REG_ENTRY       0x005415A0u
#define RVA_STAB_VT         0x0276EDF8u
#define RVA_STAB_ENTRY_VT   0x0277CED8u
#define RVA_STAB_FACTORY    0x0033C420u
#define RVA_STAB_TOOLTIP    0x0378500u
#define RVA_LEXER_INIT      0x035E1AB0u
#define RVA_LEXER_SYNC      0x035E1AB1u
#define RVA_EFF_GETPARAM    0x00544C90u
#define RVA_EFF_PACKKEY     0x2245E60u
#define RVA_EFF_FORMAT      0x10E48A0u
#define RVA_EFF_PARAM_CTOR  0x0029DAD0u
#define RVA_EFF_PARAM_DTOR  0x0029DFE0u
#define RVA_EFF_PARAM_TAG   0x2745A00u
#define RVA_EFF_STR_APPEND  0x011DBC0u

#define EFF_STATE_PENDING    0
#define EFF_STATE_OK         1
#define EFF_STATE_FAILED     2

typedef void (__fastcall *EffectExecFn)(void* self, void* scope);

typedef struct EffectDef {
    const char*  name;
    const char*  desc;
    const char*  locKey;
    EffectExecFn exec;
    void*      (*factory)(void);
    void*      (*tooltip)(void* self, void* out, void* ctx);
    int          tokenId;
    int          state;
    void*        vt[EFF_VT_SLOTS];
    void*        entryVt[2];
    unsigned char entry[16];
} EffectDef;

int  Effect_RegistryReady(void);
int  Effect_RegistryRegister(EffectDef* def);
int  Effect_RegistryRegisterAll(EffectDef** defs, int count);
int  Effect_RegistryRegisteredCount(void);

void* Effect_NewInstance(void* vt);
void* Effect_BuildTooltip(void* self, void* out, void* ctx, const char* locKey);
float Effect_ParamFloat(void* self, void* ctx);
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
