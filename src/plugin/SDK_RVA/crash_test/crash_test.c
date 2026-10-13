#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include "carrier.h"
#include "console_cmd.h"
#include "crash_test.h"

#include "../common/plugin_log.h"

static DWORD WINAPI CrashTest_DereferenceNullInWorkerThread(LPVOID param)
{
    volatile unsigned int* nullPointer = (volatile unsigned int*)0;
    (void)param;
    *nullPointer = 1u;
    return 0;
}

static long long __fastcall Handler_CrashOnCallingThread(CmdResult* out, CmdArgs* args)
{
    volatile unsigned int* nullPointer = (volatile unsigned int*)0;
    (void)args;
    Plugin_Log("[crashme_main] about to dereference NULL on the calling thread");
    *nullPointer = 1u;
    (void)out;
    return 0;
}

static long long __fastcall Handler_CrashInWorkerThread(CmdResult* out, CmdArgs* args)
{
    HANDLE workerThread;
    (void)args;
    Plugin_Log("[crashme] spawning a thread that dereferences NULL");
    workerThread = CreateThread(NULL, 0, CrashTest_DereferenceNullInWorkerThread, NULL, 0, NULL);
    if (workerThread != NULL) CloseHandle(workerThread);
    (void)out;
    return 0;
}

static const CmdDef kCrashTestCommandDefs[] = {
    { "crashme", "Deliberately crash in a worker thread (tests the crash reporter)", "crm", 0, { "" }, &Handler_CrashInWorkerThread },
    { "crashme_main", "Deliberately crash on the calling thread (tests the crash reporter)", "crmm", 0, { "" }, &Handler_CrashOnCallingThread },
};

int CrashTest_RegisterCommands(void)
{
    return ConsoleCmd_RegisterAll(kCrashTestCommandDefs,
                                  (int)(sizeof(kCrashTestCommandDefs) / sizeof(kCrashTestCommandDefs[0])));
}
