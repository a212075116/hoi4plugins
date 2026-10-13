#pragma once

#include <stddef.h>
#include "../common/native_string.h"

#pragma pack(push, 8)

typedef NativeString CmdString;

#define CMD_MAX_ALIAS 3

typedef struct {
    int         entryStateFlag;
    int         reservedField04;
    CmdString   name;
    int         aliasCount;
    int         reservedField2C;
    const char* aliases[CMD_MAX_ALIAS];
    CmdString   description;
    void*       handler;
    void*       reservedField70;
    void*       reservedField78;
    int         argCount;
    int         reservedField84;
    CmdString   args[10];
} CmdEntry;

typedef struct {
    CmdEntry* data;
    int       capacity;
    int       count;
} CmdTable;

typedef struct {
    CmdString* data;
    int        capacity;
    int        count;
} CmdArgs;

typedef struct {
    unsigned char ok;
    unsigned char pad[7];
    CmdString     message;
} CmdResult;

#pragma pack(pop)

#define CMD_SSO_MAX   15
#define CMD_MAX_ARGS  8
#define CMD_MAX_BATCH 16

typedef long long (__fastcall *CmdHandlerFn)(CmdResult* out, CmdArgs* args);

typedef struct {
    const char*  name;
    const char*  description;
    const char*  alias;
    int          argCount;
    const char*  argNames[CMD_MAX_ARGS];
    CmdHandlerFn handler;
} CmdDef;

typedef void (*CmdLogFn)(const char* fmt, ...);

extern CmdLogFn g_CmdLog;

int  ConsoleCmd_RegisterAll(const CmdDef* defs, int n);
void ConsoleCmd_InitResult(CmdResult* out);
void ConsoleCmd_SetMessage(CmdResult* out, const char* s);
int  ConsoleCmd_GetArg(CmdArgs* args, int i, char* dst, size_t dstn);
int  ConsoleCmd_IsReadable(const void* p, size_t n);
