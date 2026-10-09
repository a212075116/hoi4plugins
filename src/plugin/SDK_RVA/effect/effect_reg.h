#pragma once

typedef void (__fastcall *EffectExecFn)(void* self, void* scope);

#define RVA_EFFECT_MAP      0x03330000u
#define RVA_ADD_TOKEN       0x024BB460u
#define RVA_REG_ENTRY       0x005415A0u
#define RVA_STAB_VT         0x0276EDF8u
#define RVA_STAB_ENTRY_VT   0x0277CED8u
#define RVA_STAB_FACTORY    0x0033C420u
#define RVA_LEXER_INIT      0x035E1AB0u
#define RVA_LEXER_SYNC      0x035E1AB1u

#define EFF_VT_SLOTS        25
#define EFF_VT_EXEC         0x68
#define EFF_VT_DTOR         0x00
#define EFF_ENTRY_VT_FACTORY 0x08
#define EFF_OFF_PARAM        0x108
#define EFF_OFF_PARAM_SIZE   0x10
#define EFF_OFF_PARAM_CAP    0x18
#define EFF_SSO_MAX          15

int  Effect_LexerReady(void);
int  Effect_AddToken(const char* name, int* outId);
int  Effect_Register(const char* name, const char* desc, EffectExecFn exec, int* outId);
int  Effect_IsCameraHeightRegistered(void);
int  Effect_RegisterCameraHeight(void);
int  Effect_GetLastError(void);
int  Effect_GetTokenId(void);
