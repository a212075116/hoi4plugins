#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct NativeCameraSnapshot {
    unsigned int size;
    unsigned int version;
    float height;
    int minimum;
    int maximum;
    void* object;
    char status[64];
} NativeCameraSnapshot;

enum NativeScriptSymbol {
    NS_EFFECT_MAP, NS_EFFECT_REGISTER, NS_ADD_TOKEN, NS_LEXER_INIT, NS_LEXER_SYNC,
    NS_PARAM_GET, NS_PARAM_CTOR, NS_PARAM_DTOR, NS_PARAM_TAG, NS_TEXT_PACK,
    NS_TEXT_FORMAT, NS_TEXT_APPEND, NS_TRIGGER_MAP, NS_TRIGGER_REGISTER,
    NS_GAME_ALLOC, NS_GAME_FREE, NS_STATIC_TOKENS, NS_SCOPE_MASK, NS_TEMPORARY,
    NS_PARAM_NAME, NS_CONTAINS, NS_CONTAINER, NS_STRING_CTOR, NS_SYMBOL_COUNT
};
#define NG_NONE (-1)
enum NativeGroup {
#define NATIVE_GROUP(id, name, registry, first, second) id,
#define NATIVE_CODE(id, group, key)
#define NATIVE_DATA(id, group, key, bytes)
#define NATIVE_SLOT(id, group, key, type, offset, slot)
#define NATIVE_TABLE(id, group, key, type, offset, slots)
#include "symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
    NG_COUNT
};
enum NativeSymbol {
#define NATIVE_GROUP(id, name, registry, first, second)
#define NATIVE_CODE(id, group, key) id,
#define NATIVE_DATA(id, group, key, bytes) id,
#define NATIVE_SLOT(id, group, key, type, offset, slot) id,
#define NATIVE_TABLE(id, group, key, type, offset, slots) id,
#include "symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
    NSY_COUNT
};
int NativeAdapter_GroupReady(int group);
unsigned int NativeAdapter_Symbol(int symbol);
const char* NativeAdapter_GroupDiagnostic(int group);
typedef struct NativeScriptTemplate {
    unsigned int vt, entryVt, factory, parse, eval, slots, allocation;
} NativeScriptTemplate;
int NativeAdapter_RegistryReady(void);
unsigned int NativeAdapter_RegistryRva(unsigned int symbol);
unsigned int NativeAdapter_StaticTokenCount(void);
int NativeAdapter_ScriptTemplate(int kind, NativeScriptTemplate* out);
const char* NativeAdapter_RegistryDiagnostic(void);
int NativeAdapter_RegisterScriptDiagnostic(void);

int NativeAdapter_Initialize(void);
int NativeAdapter_CameraWriteAllowed(void);
const char* NativeAdapter_Diagnostic(void);
void NativeAdapter_Report(const char* capability, int available, const char* reason);
void NativeAdapter_StartMonitor(void);
void NativeAdapter_OpenLogConsole(void);
void NativeAdapter_CameraRegistered(int commands, int effects);
void* NativeAdapter_CameraObject(void);
#ifdef NATIVE_ADAPTER_IMPLEMENTATION
__declspec(dllexport)
#endif
int Hoi4Plugin_ReadCameraV1(NativeCameraSnapshot* out);

#ifdef __cplusplus
}
#endif
