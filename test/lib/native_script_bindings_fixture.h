#pragma once
#include "../../src/plugin/adapter/native_adapter.h"
#include "native_symbols_fixture.h"
static int g_scriptFixtureReady=1;
int NativeAdapter_RegistryReady(void) {return g_scriptFixtureReady;}
unsigned int NativeAdapter_RegistryRva(unsigned int id) {
    static const unsigned int values[]={0x3330000,0x5415a0,0x24bb460,0x35e1ab0,0x35e1ab1,0x544c90,0x29dad0,0x29dfe0,0x2745a00,0x2245e60,0x10e48a0,0x129c10,0x3330050,0x550970,0x21c9af0,0x21c9b00,0x338d170,0x537d90,0x54f730,0x5454a0,0xbc8d20,0x542500,0x11d970};
    return g_scriptFixtureReady && id<NS_SYMBOL_COUNT?values[id]:0;
}
unsigned int NativeAdapter_StaticTokenCount(void) {return g_scriptFixtureReady?10765:0;}
int NativeAdapter_ScriptTemplate(int kind,NativeScriptTemplate* out) {
    static const NativeScriptTemplate values[]={
        {0x276edf8,0x277ced8,0x33c420,0x2e2ff0,0x34c2f0,25,296},
        {0x278a3a0,0x27a14d8,0x3e32b0,0x13a2430,0x3cfd80,23,96},
        {0x27915a0,0x27a0bc0,0x3e6a70,0x13a2690,0x13a2180,26,304},
        {0x2799320,0x279ff90,0x3e3e10,0x54ae70,0x3d0bb0,23,544}
    };
    if(!out || kind<0 || kind>3 || !g_scriptFixtureReady)return 0;
    *out=values[kind];return 1;
}
