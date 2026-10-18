#pragma once
#include "../../src/plugin/adapter/native_adapter.h"
static int g_symbolFixtureDisabled = -2;
#include "native_symbols_values.h"
static int NativeSymbolFixture_GroupOf(int symbol) {
    static const int groups[NSY_COUNT] = {
#define NATIVE_GROUP(id, name, registry, first, second)
#define NATIVE_CODE(id, group, key) group,
#define NATIVE_DATA(id, group, key, bytes) group,
#define NATIVE_SLOT(id, group, key, type, offset, slot) group,
#define NATIVE_TABLE(id, group, key, type, offset, slots) group,
#define NATIVE_FIELD(id, group, key)
#include "../../src/plugin/adapter/symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
#undef NATIVE_FIELD
    };
    return groups[symbol];
}
int NativeAdapter_GroupReady(int group) {
    return group >= 0 && group < NG_COUNT && g_symbolFixtureDisabled != -1 && g_symbolFixtureDisabled != group;
}
unsigned int NativeAdapter_Symbol(int symbol) {
    if (symbol < 0 || symbol >= NSY_COUNT || !NativeAdapter_GroupReady(NativeSymbolFixture_GroupOf(symbol))) return 0;
    return kNativeSymbolValues[symbol];
}
const char* NativeAdapter_GroupDiagnostic(int group) {
    return NativeAdapter_GroupReady(group) ? "READY_FIXTURE" : "GROUP_FIXTURE_UNAVAILABLE";
}
static int NativeSymbolFixture_FieldGroup(int field) {
    static const int groups[NFL_COUNT] = {
#define NATIVE_GROUP(id, name, registry, first, second)
#define NATIVE_CODE(id, group, key)
#define NATIVE_DATA(id, group, key, bytes)
#define NATIVE_SLOT(id, group, key, type, offset, slot)
#define NATIVE_TABLE(id, group, key, type, offset, slots)
#define NATIVE_FIELD(id, group, key) group,
#include "../../src/plugin/adapter/symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
#undef NATIVE_FIELD
    };
    return groups[field];
}
unsigned int NativeAdapter_Field(int field) {
    if (field < 0 || field >= NFL_COUNT || !NativeAdapter_GroupReady(NativeSymbolFixture_FieldGroup(field))) return 0;
    return kNativeFieldValues[field];
}
