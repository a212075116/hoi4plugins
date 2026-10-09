#pragma once

#include <stddef.h>

#pragma pack(push, 8)

typedef struct {
    union { char buf[16]; char* ptr; } u;
    size_t size;
    size_t cap;
} CmdString;

typedef struct {
    int       flag;
    int       unknown04;
    CmdString name;
    CmdString usage;
    CmdString description;
    void*     handler;
    void*     p70;
    void*     p78;
    int       argCount;
    int       p84;
    CmdString args[10];
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
    const char*  usage;
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
