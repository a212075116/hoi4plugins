#pragma once
#include "../../src/plugin/adapter/native_adapter.h"
static int g_symbolFixtureDisabled = -2;
static const unsigned int kNativeSymbolFixture[NSY_COUNT] = {
    0x332F260,0x332F698,0x129CA0,0x35E1A80,0x24B4920,0x24B4C40,0x24B4D40,0xDD3A50,0x18A1EE0,
    0x542280,0xBC0880,0xDA04F0,0x12CF2B0,0x364C60,0x34F750,0x350240,0x34C760,0x366BC0,0x35B9E0,0x355C70,0x277C418,0x341F60,
    0xBC5C10,0xBC8FC0,0x2775698,
    0x3330460,0x34530D4,0x332EC69,0x1205A0,0x61D0D0,0x61CE50,0x6201F0,0x6202C0,0x620570,0x621040,0x24DC920,0x24BB300,0x6207E0,
    0x3DB5C0,0x2B5BE00,0x1CDA120,0x1CD4570,
    0x2721158,0x27211B0,0x27E7360,0x2936CC0,0x2971B18,0x297EA60,0x295A2B0,0x29530D8,0x27EB3D0,0x27D4990,0x27D55F0
};
static int NativeSymbolFixture_GroupOf(int symbol) {
    static const int groups[NSY_COUNT] = {
#define NATIVE_GROUP(id, name, registry, first, second)
#define NATIVE_CODE(id, group, key) group,
#define NATIVE_DATA(id, group, key, bytes) group,
#define NATIVE_SLOT(id, group, key, type, offset, slot) group,
#define NATIVE_TABLE(id, group, key, type, offset, slots) group,
#include "../../src/plugin/adapter/symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
    };
    return groups[symbol];
}
int NativeAdapter_GroupReady(int group) {
    return group >= 0 && group < NG_COUNT && g_symbolFixtureDisabled != -1 && g_symbolFixtureDisabled != group;
}
unsigned int NativeAdapter_Symbol(int symbol) {
    if (symbol < 0 || symbol >= NSY_COUNT || !NativeAdapter_GroupReady(NativeSymbolFixture_GroupOf(symbol))) return 0;
    return kNativeSymbolFixture[symbol];
}
const char* NativeAdapter_GroupDiagnostic(int group) {
    return NativeAdapter_GroupReady(group) ? "READY_FIXTURE" : "GROUP_FIXTURE_UNAVAILABLE";
}
