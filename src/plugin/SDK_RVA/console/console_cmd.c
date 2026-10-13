#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#include "console_cmd.h"
#include "carrier.h"
#include "../common/log.h"
#include "../common/native_memory.h"

#define RVA_CMD_MANAGER   0x35E1A80u
#define RVA_CMDTBL_MERGE  0x24B4920u
#define RVA_CMDMGR_INIT   0x24B4C40u

typedef char assert_cmdstring[(sizeof(CmdString) == 32) ? 1 : -1];
typedef char assert_cmdentry [(sizeof(CmdEntry)  == 456) ? 1 : -1];

static void ConsoleCmd_DefaultLog(const char* fmt, ...) {
    va_list arguments;
    va_start(arguments, fmt);
    Log_AppendV(LOADER_LOG_DIR "/console_cmd.log", fmt, arguments);
    va_end(arguments);
}

CmdLogFn g_CmdLog = ConsoleCmd_DefaultLog;

int ConsoleCmd_IsReadable(const void* p, size_t n) {
    return NativeMemory_IsReadable(p, n);
}

void ConsoleCmd_InitResult(CmdResult* out) {
    if (out == NULL) return;
    out->ok = 0;
    out->message.u.buf[0] = 0;
    out->message.size = 0;
    out->message.cap  = 15;
}

static void ConsoleCmd_WriteShortString(CmdString* s, const char* str) {
    size_t n = 0;
    while (str[n] != 0) ++n;
    if (n > CMD_SSO_MAX) n = CMD_SSO_MAX;
    s->size = n;
    s->cap  = 15;
    memcpy(s->u.buf, str, n);
    s->u.buf[n] = 0;
}


static void ConsoleCmd_WriteString(CmdString* s, const char* str) {
    HMODULE base;
    NativeStringAssignFn assign;
    size_t n = 0;

    if (s == NULL || str == NULL) return;
    while (str[n] != 0) ++n;
    if (n <= CMD_SSO_MAX) { ConsoleCmd_WriteShortString(s, str); return; }

    base = GetModuleHandleA(NULL);
    if (base == NULL) { ConsoleCmd_WriteShortString(s, str); return; }
    assign = (NativeStringAssignFn)((unsigned char*)base + NATIVE_STRING_ASSIGN_RVA);
    assign((void**)s, str, n);
}

void ConsoleCmd_SetMessage(CmdResult* out, const char* s) {
    if (out == NULL || s == NULL) return;
    if (out->message.cap == 0) {
        out->message.u.buf[0] = 0;
        out->message.size = 0;
        out->message.cap = CMD_SSO_MAX;
    }
    ConsoleCmd_WriteString(&out->message, s);
}

int ConsoleCmd_GetArg(CmdArgs* args, int i, char* dst, size_t dstn) {
    CmdString* e;
    if (args == NULL || dst == NULL || dstn == 0) return 0;
    if (i < 0 || i >= args->count || args->count > CMD_MAX_ARGS) return 0;
    if (args->data == NULL || !ConsoleCmd_IsReadable(args->data, 32)) return 0;
    e = (CmdString*)((char*)args->data + (size_t)i * sizeof(CmdString));
    if (!ConsoleCmd_IsReadable(e, 32)) return 0;

    if (e->cap <= CMD_SSO_MAX) {
        size_t k;
        for (k = 0; k + 1 < dstn && k < CMD_SSO_MAX; ++k) {
            char c = e->u.buf[k];
            if (c == 0) break;
            dst[k] = c;
        }
        dst[k] = 0;
        return k > 0;
    }
    if (e->cap < 4096 && e->size < 512) {
        const char* sp = e->u.ptr;
        size_t k;
        if (!ConsoleCmd_IsReadable(sp, e->size + 1)) return 0;
        for (k = 0; k + 1 < dstn && k < e->size; ++k) dst[k] = sp[k];
        dst[k] = 0;
        return k > 0;
    }
    return 0;
}

static void ConsoleCmd_FillEntry(CmdEntry* e, const CmdDef* d) {
    memset(e, 0, sizeof(*e));
    e->entryStateFlag     = 1;
    e->handler  = (void*)d->handler;
    e->argCount = d->argCount;
    ConsoleCmd_WriteString(&e->name, d->name);
    if (d->alias != NULL && d->alias[0] != 0) {
        e->aliases[0] = d->alias;
        e->aliasCount = 1;
    }
    ConsoleCmd_WriteString(&e->description, d->description ? d->description : "");
    if (d->argCount > 0) {
        int i;
        for (i = 0; i < d->argCount && i < CMD_MAX_ARGS; ++i) {
            if (d->argNames[i] != NULL) ConsoleCmd_WriteString(&e->args[i], d->argNames[i]);
        }
    }
}

static int ConsoleCmd_CheckDefinition(const CmdDef* d) {
    static const char* kFields[4] = { "name", "alias", "description", "argName" };
    const char* vals[4];
    int k;

    if (d->name == NULL || d->handler == NULL) {
        g_CmdLog("[cmdreg] skip: name or handler is null");
        return 0;
    }
    if (d->alias != NULL && d->alias[0] != 0 && CMD_MAX_ALIAS < 1) {
        g_CmdLog("[cmdreg] skip %s: alias not supported", d->name);
        return 0;
    }
    if (d->argCount < 0 || d->argCount > CMD_MAX_ARGS) {
        g_CmdLog("[cmdreg] skip %s: argCount=%d out of [0,%d]",
                 d->name, d->argCount, CMD_MAX_ARGS);
        return 0;
    }
    vals[0] = d->name;
    vals[1] = d->alias ? d->alias : "";
    vals[2] = d->description ? d->description : "";
    for (k = 0; k < 3; ++k) {
        if (vals[k][0] == 0 && k != 1) {
            g_CmdLog("[cmdreg] skip %s: %s is empty", d->name, kFields[k]);
            return 0;
        }
    }
    for (k = 0; k < d->argCount; ++k) {
        if (d->argNames[k] != NULL && d->argNames[k][0] == 0) {
            g_CmdLog("[cmdreg] skip %s: argNames[%d] is empty", d->name, k);
            return 0;
        }
    }
    return 1;
}

int ConsoleCmd_RegisterAll(const CmdDef* defs, int n) {
    HMODULE base;
    unsigned char* img;
    void** mgrSlot;
    void* mgr;
    typedef void (*MergeFn)(void* mgr, CmdTable* src);
    typedef void (*InitFn)(void);
    static CmdEntry entries[16];
    static CmdTable  table;
    int i;
    int ok = 0;

    if (defs == NULL || n <= 0) return 0;
    if (n > (int)(sizeof(entries) / sizeof(entries[0]))) {
        g_CmdLog("[cmdreg] max %d per call, got %d",
                 (int)(sizeof(entries) / sizeof(entries[0])), n);
        return 0;
    }

    base = GetModuleHandleA(NULL);
    if (base == NULL) { g_CmdLog("[cmdreg] no main module base"); return 0; }
    img = (unsigned char*)base;

    mgrSlot = (void**)(img + RVA_CMD_MANAGER);
    if (!ConsoleCmd_IsReadable(mgrSlot, sizeof(void*))) {
        g_CmdLog("[cmdreg] manager slot %p unreadable", (void*)mgrSlot);
        return 0;
    }
    if (*mgrSlot == NULL) {
        InitFn init = (InitFn)(img + RVA_CMDMGR_INIT);
        g_CmdLog("[cmdreg] manager not built, init %p", (void*)init);
        init();
    }
    mgr = *mgrSlot;
    if (mgr == NULL) { g_CmdLog("[cmdreg] manager still null, abort"); return 0; }

    g_CmdLog("[cmdreg] manager = %p (count=%d capacity=%d)",
             mgr, *(int*)((char*)mgr + 12), *(int*)((char*)mgr + 8));

    for (i = 0; i < n; ++i) {
        if (!ConsoleCmd_CheckDefinition(&defs[i])) continue;
        ConsoleCmd_FillEntry(&entries[ok], &defs[i]);
        g_CmdLog("[cmdreg] + [%d] \"%s\" desc=\"%s\" argc=%d handler=%p",
                 ok, defs[i].name, defs[i].description ? defs[i].description : "",
                 defs[i].argCount, (void*)defs[i].handler);
        ++ok;
    }
    if (ok == 0) { g_CmdLog("[cmdreg] nothing passed checks, abort"); return 0; }

    table.data     = entries;
    table.capacity = ok;
    table.count    = ok;

    {
        MergeFn merge = (MergeFn)(img + RVA_CMDTBL_MERGE);
        g_CmdLog("[cmdreg] merge %p with %d entry(ies)", (void*)merge, ok);
        merge(mgr, &table);
    }
    g_CmdLog("[cmdreg] done: count=%d", *(int*)((char*)mgr + 12));
    return ok;
}
