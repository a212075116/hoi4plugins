#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <sddl.h>
#include <shellapi.h>
#include <stdio.h>
#include <string.h>
#include "console_cmd.h"
#include "debug_console.h"
#include "inline_hook.h"
#include "MinHook.h"
#include "../../../debug_console/protocol.h"

#include "../common/plugin_log.h"
typedef struct {
    LONG state;
    ULONGLONG deadline;
    ULONGLONG serial;
    DcRequest request;
    DcResponse response;
    HANDLE done;
    char input[DC_INPUT_MAX + 1], output[DC_OUTPUT_MAX + 1];
} Pending;
static SRWLOCK g_lock = SRWLOCK_INIT;
static Pending g_queue[DC_QUEUE_MAX];
static HANDLE g_pipes[DC_PEERS + 1];
static DWORD g_thread;
static ULONGLONG g_serial;
static volatile LONG g_started, g_failed, g_commandsReady;
static volatile LONG g_peerState;
static long long (__fastcall *g_frame)(long long, char);
static HANDLE g_helper;
static SRWLOCK g_helperLock = SRWLOCK_INIT;
static __declspec(thread) int g_dispatching;

static unsigned char __fastcall ExternalDeveloperPermission(void* object) {
    (void)object;
    return 0;
}

static int DispatchExternal(unsigned char* base, void* manager, CmdResult* result, CmdArgs* args, char* output, size_t outputSize) {
    typedef unsigned char (__fastcall *Predicate)(void*);
    typedef long long (__fastcall *Dispatch)(void*, CmdResult*, CmdArgs*);
    void* network = *(void**)((char*)manager + 144);
    void** table = *(void***)network;
    void* permissionTable[3] = {NULL, NULL, (void*)ExternalDeveloperPermission};
    void** permissionObject = permissionTable;
    void* originalPermission;
    unsigned char originalUiState[2];
    if (!ConsoleCmd_IsReadable(table, 3 * sizeof(void*)) || !ConsoleCmd_IsReadable(table[2], 1)) {
        strcpy_s(output, outputSize, "Multiplayer permission check unavailable; request not executed.");
        return 0;
    }
    if (((Predicate)table[2])(network)) {
        strcpy_s(output, outputSize, "External console commands are disabled in multiplayer.");
        return 0;
    }
    memcpy(originalUiState, (char*)manager + 216, sizeof(originalUiState));
    originalPermission = InterlockedExchangePointer((PVOID volatile*)((char*)manager + 80), &permissionObject);
    __try {
        ((Dispatch)(base + 0x24B4D40))(manager, result, args);
    } __finally {
        InterlockedExchangePointer((PVOID volatile*)((char*)manager + 80), originalPermission);
        memcpy((char*)manager + 216, originalUiState, sizeof(originalUiState));
    }
    return 1;
}

static void ReleaseString(CmdString* s) {
    if (s->cap > 15) {
        void* p = s->u.ptr;
        if (s->cap + 1 >= 4096) {
            void* raw;
            if (!ConsoleCmd_IsReadable((char*)p - 8, 8)) return;
            raw = *((void**)p - 1);
            if ((uintptr_t)p - (uintptr_t)raw - 8 > 31) return;
            p = raw;
        }
        ((void (__cdecl*)(void*))((char*)GetModuleHandleW(NULL) + 0x21C9B00))(p);
    }
    memset(s, 0, sizeof(*s)); s->cap = 15;
}

static void Execute(Pending* p) {
    unsigned char* base = (unsigned char*)GetModuleHandleW(NULL);
    CmdString strings[CMD_MAX_ARGS + 1] = {0};
    CmdArgs args = { strings, CMD_MAX_ARGS + 1, 0 };
    CmdResult result;
    char storage[DC_INPUT_MAX + 1];
    char* at = p->input;
    int i, bad = 0;
    void* manager;
    typedef void** (__fastcall *Assign)(void**, const void*, size_t);
    typedef long long (__fastcall *Dispatch)(void*, CmdResult*, CmdArgs*);
    if (!InterlockedCompareExchange(&g_commandsReady, 0, 0)) {
        p->response.status = DC_REJECTED;
        strcpy_s(p->output, sizeof(p->output), "Plugin command registration is not complete; request not executed.");
        return;
    }
    ConsoleCmd_InitResult(&result);
    for (i = 0; i < CMD_MAX_ARGS + 1; ++i) strings[i].cap = 15;
    while (*at) {
        size_t n = 0; char quote = 0;
        while (*at == ' ' || *at == '\t') ++at;
        if (!*at) break;
        if (args.count == CMD_MAX_ARGS + 1) { bad = 1; break; }
        while (*at && (quote || (*at != ' ' && *at != '\t'))) {
            char c = *at++;
            if (c == '"') { quote = !quote; continue; }
            if (c == '\\' && (*at == '"' || *at == '\\')) c = *at++;
            storage[n++] = c;
        }
        if (quote) { bad = 1; break; }
        storage[n] = 0;
        ((Assign)(base + 0x129CA0))((void**)&strings[args.count++], storage, n);
    }
    p->response.status = DC_REJECTED;
    if (bad || !args.count || !strings[0].size) {
        strcpy_s(p->output, sizeof(p->output), "Invalid syntax: use command plus at most 8 arguments, balanced double quotes.");
    } else {
        manager = *(void**)(base + 0x35E1A80);
        if (!ConsoleCmd_IsReadable(manager, 224) ||
            !ConsoleCmd_IsReadable(*(void**)((char*)manager + 80), 8) ||
            !ConsoleCmd_IsReadable(*(void**)((char*)manager + 144), 8) ||
            !ConsoleCmd_IsReadable(*(void**)((char*)manager + 208), 8)) {
            strcpy_s(p->output, sizeof(p->output), "Command manager is not ready; request was not executed.");
        } else {
            if (!DispatchExternal(base, manager, &result, &args, p->output, sizeof(p->output))) {
                for (i = 0; i < args.count; ++i) ReleaseString(&strings[i]);
                ReleaseString(&result.message);
                return;
            }
            p->response.status = DC_EXECUTED;
            p->response.ok = result.ok;
            if (result.message.size && result.message.size <= 16 * 1024 * 1024) {
                const char* text = result.message.cap > 15 ? result.message.u.ptr : result.message.u.buf;
                size_t n = result.message.size;
                if (n > DC_OUTPUT_MAX - 32) n = DC_OUTPUT_MAX - 32;
                if (ConsoleCmd_IsReadable(text, n)) {
                    memcpy(p->output, text, n); p->output[n] = 0;
                    if (n < result.message.size) strcat_s(p->output, sizeof(p->output), " [response truncated]");
                }
            }
        }
    }
    for (i = 0; i < args.count; ++i) ReleaseString(&strings[i]);
    ReleaseString(&result.message);
}

static long long __fastcall Frame(long long object, char mode) {
    long long r = g_frame(object, mode);
    int i, count;
    if (GetCurrentThreadId() != g_thread || g_failed || g_dispatching) return r;
    g_dispatching = 1;
    for (count = 0; count < 2; ++count) {
        Pending* p = NULL;
        AcquireSRWLockExclusive(&g_lock);
        for (i = 0; i < DC_QUEUE_MAX; ++i)
            if (g_queue[i].state == 1 && (!p || g_queue[i].serial < p->serial)) p = &g_queue[i];
        if (!p) { ReleaseSRWLockExclusive(&g_lock); break; }
        p->state = 2;
        ReleaseSRWLockExclusive(&g_lock);
        p->response.thread = GetCurrentThreadId();
        if (GetTickCount64() >= p->deadline) {
            p->response.status = DC_CANCELLED;
            strcpy_s(p->output, sizeof(p->output), "Expired before execution; request cancelled.");
        } else {
            __try { Execute(p); }
            __except(EXCEPTION_EXECUTE_HANDLER) {
                InterlockedExchange(&g_failed, 1);
                p->response.status = DC_FAULT;
                strcpy_s(p->output, sizeof(p->output), "Native dispatch fault; bridge disabled. Restart the game.");
            }
        }
        p->response.length = (uint32_t)strlen(p->output);
        AcquireSRWLockExclusive(&g_lock); p->state = 3; SetEvent(p->done); ReleaseSRWLockExclusive(&g_lock);
    }
    g_dispatching = 0;
    return r;
}

static BOOL CALLBACK FindWindowThread(HWND w, LPARAM unused) {
    DWORD pid = 0, tid = GetWindowThreadProcessId(w, &pid);
    (void)unused;
    if (pid == GetCurrentProcessId() && !GetWindow(w, GW_OWNER) && IsWindowVisible(w)) {
        g_thread = tid; return FALSE;
    }
    return TRUE;
}

static int OpenHelper(void) {
    wchar_t exe[MAX_PATH], command[MAX_PATH + 100];
    STARTUPINFOW si = {sizeof(si)};
    PROCESS_INFORMATION pi;
    wchar_t* slash;
    int ok = 0;
    AcquireSRWLockExclusive(&g_helperLock);
    if (g_helper && WaitForSingleObject(g_helper, 0) == WAIT_TIMEOUT) { ReleaseSRWLockExclusive(&g_helperLock); return 1; }
    if (g_helper) { CloseHandle(g_helper); g_helper = NULL; }
    {
        wchar_t mutexName[120]; HANDLE existing;
        _snwprintf_s(mutexName, _countof(mutexName), _TRUNCATE, L"Local\\hoi4-plugin-console-%lu", GetCurrentProcessId());
        existing = OpenMutexW(SYNCHRONIZE, FALSE, mutexName);
        if (existing) { CloseHandle(existing); ReleaseSRWLockExclusive(&g_helperLock); return 1; }
    }
    GetModuleFileNameW(NULL, exe, MAX_PATH);
    slash = wcsrchr(exe, L'\\'); if (!slash) { ReleaseSRWLockExclusive(&g_helperLock); return 0; }
    wcscpy_s(slash + 1, MAX_PATH - (slash + 1 - exe), L"hoi4_debug_console.exe");
    _snwprintf_s(command, _countof(command), _TRUNCATE, L"\"%s\" --pid %lu", exe, GetCurrentProcessId());
    if (CreateProcessW(exe, command, NULL, NULL, FALSE, CREATE_NEW_CONSOLE, NULL, NULL, &si, &pi)) {
        g_helper = pi.hProcess; CloseHandle(pi.hThread);
        ok = 1;
        Plugin_Log("[debugconsole] helper pid=%lu", pi.dwProcessId);
    } else Plugin_Log("[debugconsole] helper launch failed error=%lu", GetLastError());
    ReleaseSRWLockExclusive(&g_helperLock);
    return ok;
}

static long long __fastcall OpenCommand(CmdResult* out, CmdArgs* args) {
    (void)args; ConsoleCmd_InitResult(out);
    if (g_started == 2) {
        out->ok = (unsigned char)OpenHelper();
        ConsoleCmd_SetMessage(out, out->ok ? "External console opened." : "External console launch failed; check plugin log.");
    }
    else ConsoleCmd_SetMessage(out, "External console service is not ready.");
    return (long long)out;
}

static DWORD WINAPI Peer(LPVOID value) {
    HANDLE h = (HANDLE)value;
    for (;;) {
        BOOL connected = DcConnect(h);
        uint32_t lastId = 0;
        if (!connected) {
            DisconnectNamedPipe(h);
            Sleep(50);
            continue;
        }
        if (connected) {
            ULONG pid; DWORD mine = 0, theirs = 1;
            if (!GetNamedPipeClientProcessId(h, &pid) || !ProcessIdToSessionId(pid, &theirs) ||
                !ProcessIdToSessionId(GetCurrentProcessId(), &mine) || mine != theirs) connected = FALSE;
        }
        if (connected && h == g_pipes[DC_PEERS]) {
            ULONG pid; wchar_t expected[MAX_PATH], actual[MAX_PATH]; DWORD size = _countof(actual);
            HANDLE process = NULL;
            if (GetNamedPipeClientProcessId(h, &pid)) process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
            GetModuleFileNameW(NULL, expected, _countof(expected));
            { wchar_t* slash = wcsrchr(expected, L'\\');
              if (slash) wcscpy_s(slash+1, _countof(expected)-(slash+1-expected), L"hoi4_debug_console.exe"); }
            if (!process || !QueryFullProcessImageNameW(process, 0, actual, &size) || _wcsicmp(actual, expected)) connected = FALSE;
            if (process) CloseHandle(process);
        }
        while (connected) {
            DcRequest req; DcResponse res = {DC_MAGIC, DC_PROTOCOL_VERSION, 0, 0, DC_REJECTED, 0, 0};
            char input[DC_INPUT_MAX + 1], output[DC_OUTPUT_MAX + 1] = {0}; Pending* p = NULL;
            int i;
            if (!DcTransfer(h, &req, sizeof(req), 0, 30000)) break;
            if (req.magic != DC_MAGIC || req.version != DC_PROTOCOL_VERSION || req.id <= lastId || !req.length || req.length > DC_INPUT_MAX) break;
            lastId = req.id;
            if (!DcTransfer(h, input, req.length, 0, 5000)) break;
            input[req.length] = 0; res.id = req.id;
            if (memchr(input, 0, req.length) || memchr(input, '\r', req.length) || memchr(input, '\n', req.length) ||
                !MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, input, req.length, NULL, 0)) {
                strcpy_s(output, sizeof(output), "Invalid UTF-8 or embedded control separator; request not executed.");
            } else if (g_failed) {
                strcpy_s(output, sizeof(output), "Native bridge disabled after fault; request not executed.");
            } else {
                AcquireSRWLockExclusive(&g_lock);
                for (i = 0; i < DC_QUEUE_MAX; ++i) if (!g_queue[i].state) { p = &g_queue[i]; break; }
                if (p) {
                    p->request = req; p->response = res; p->output[0] = 0;
                    memcpy(p->input, input, req.length + 1); p->deadline = GetTickCount64() + 5000;
                    p->serial = ++g_serial;
                    ResetEvent(p->done); p->state = 1;
                }
                ReleaseSRWLockExclusive(&g_lock);
                if (!p) strcpy_s(output, sizeof(output), "Queue full; request not executed.");
                else {
                    if (WaitForSingleObject(p->done, 5000) == WAIT_TIMEOUT) {
                        AcquireSRWLockExclusive(&g_lock);
                        if (p->state == 1) {
                            p->state = 3; p->response.status = DC_CANCELLED;
                            strcpy_s(p->output, sizeof(p->output), "Execution context not available; cancelled before execution.");
                            SetEvent(p->done);
                        }
                        ReleaseSRWLockExclusive(&g_lock);
                        WaitForSingleObject(p->done, INFINITE);
                    }
                    AcquireSRWLockExclusive(&g_lock);
                    res = p->response; strcpy_s(output, sizeof(output), p->output); p->state = 0;
                    ReleaseSRWLockExclusive(&g_lock);
                }
            }
            res.length = (uint32_t)strlen(output);
            if (!DcTransfer(h, &res, sizeof(res), 1, 5000) || (res.length && !DcTransfer(h, output, res.length, 1, 5000))) break;
        }
        DisconnectNamedPipe(h);
    }
}

static void CloseStartupHandles(int pipeCount, int eventCount) {
    while (eventCount) CloseHandle(g_queue[--eventCount].done);
    while (pipeCount) CloseHandle(g_pipes[--pipeCount]);
}

static DWORD WINAPI PeerStart(LPVOID value) {
    LONG state;
    while (!(state = InterlockedCompareExchange(&g_peerState, 0, 0))) Sleep(1);
    return state > 0 ? Peer(value) : 0;
}

static int StartPeerThreads(void) {
    HANDLE threads[DC_PEERS + 1];
    int i, count = 0;
    for (i = 0; i <= DC_PEERS; ++i) {
        threads[count] = CreateThread(NULL, 0, PeerStart, g_pipes[i], 0, NULL);
        if (!threads[count]) {
            Plugin_Log("[debugconsole] peer thread creation failed index=%d error=%lu", i, GetLastError());
            InterlockedExchange(&g_peerState, -1);
            while (count) {
                --count;
                WaitForSingleObject(threads[count], INFINITE);
                CloseHandle(threads[count]);
            }
            return 0;
        }
        ++count;
    }
    while (count) CloseHandle(threads[--count]);
    return 1;
}

static DWORD WINAPI StartDebugService(LPVOID unused) {
    HANDLE token; DWORD bytes = 0; TOKEN_USER* user; LPWSTR sid = NULL;
    wchar_t sddl[512], name[128]; PSECURITY_DESCRIPTOR sd = NULL;
    SECURITY_ATTRIBUTES sa = {sizeof(sa), NULL, FALSE};
    int i, argc = 0, autoOpen = 0; LPWSTR* argv;
    (void)unused;
    {
        unsigned char* image = (unsigned char*)GetModuleHandleW(NULL);
        IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)image;
        IMAGE_NT_HEADERS64* nt = (IMAGE_NT_HEADERS64*)(image + dos->e_lfanew);
        if (nt->FileHeader.TimeDateStamp != 0x6AA123BB || nt->OptionalHeader.SizeOfImage != 0x37EC000) {
            Plugin_Log("[debugconsole] unsupported executable fingerprint; bridge not enabled"); return 6;
        }
    }
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) return 1;
    GetTokenInformation(token, TokenUser, NULL, 0, &bytes); user = (TOKEN_USER*)LocalAlloc(LPTR, bytes);
    if (!user || !GetTokenInformation(token, TokenUser, user, bytes, &bytes) || !ConvertSidToStringSidW(user->User.Sid, &sid)) {
        if (user) LocalFree(user); CloseHandle(token); return 2;
    }
    _snwprintf_s(sddl, _countof(sddl), _TRUNCATE, L"D:P(A;;GA;;;%s)", sid);
    LocalFree(sid); LocalFree(user); CloseHandle(token);
    if (!ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, &sd, NULL)) return 3;
    sa.lpSecurityDescriptor = sd; DcPipeName(name, _countof(name), GetCurrentProcessId());
    for (i = 0; i <= DC_PEERS; ++i) {
        if (i == DC_PEERS) DcInteractivePipeName(name, _countof(name), GetCurrentProcessId());
        g_pipes[i] = CreateNamedPipeW(name, PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED | ((i && i != DC_PEERS) ? 0 : FILE_FLAG_FIRST_PIPE_INSTANCE),
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
            i == DC_PEERS ? 1 : DC_PEERS, DC_OUTPUT_MAX + 32, DC_INPUT_MAX + 32, 5000, &sa);
        if (g_pipes[i] == INVALID_HANDLE_VALUE) {
            Plugin_Log("[debugconsole] pipe creation failed error=%lu", GetLastError());
            CloseStartupHandles(i, 0); LocalFree(sd); return 4;
        }
    }
    LocalFree(sd);
    for (i = 0; i < DC_QUEUE_MAX; ++i) {
        g_queue[i].done = CreateEventW(NULL, TRUE, FALSE, NULL);
        if (!g_queue[i].done) {
            CloseStartupHandles(DC_PEERS + 1, i);
            Plugin_Log("[debugconsole] completion event creation failed"); return 7;
        }
    }
    for (i = 0; i < 1200 && !g_thread; ++i) { EnumWindows(FindWindowThread, 0); if (!g_thread) Sleep(100); }
    if (!g_thread || !InlineHook_Init() ||
        !InlineHook_InstallInto((char*)GetModuleHandleW(NULL) + 0xDD3A50, Frame, (void**)&g_frame)) {
        Plugin_Log("[debugconsole] scheduler unavailable; service not enabled");
        CloseStartupHandles(DC_PEERS + 1, DC_QUEUE_MAX);
        return 5;
    }
    if (!StartPeerThreads()) {
        InterlockedExchange(&g_failed, 1);
        InterlockedExchange(&g_started, -1);
        CloseStartupHandles(DC_PEERS + 1, DC_QUEUE_MAX);
        return 8;
    }
    InterlockedExchange(&g_started, 2);
    InterlockedExchange(&g_peerState, 1);
    Plugin_Log("[debugconsole] service ready pid=%lu game_thread=%lu protocol=1 peers=4 interactive=1 queue=32", GetCurrentProcessId(), g_thread);
    argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    for (i = 1; argv && i < argc; ++i) if (!_wcsicmp(argv[i], L"-debug") || !_wcsicmp(argv[i], L"-plugin-console")) autoOpen = 1;
    for (i = 1; argv && i < argc; ++i) if (!_wcsicmp(argv[i], L"-no-plugin-console")) autoOpen = 0;
    if (argv) LocalFree(argv);
    if (autoOpen) OpenHelper();
    return 0;
}

void DebugConsole_RegisterCommands(void) {
    CmdDef def = {"debugconsole", "Open external debug console", NULL, 0, {0}, OpenCommand};
    if (ConsoleCmd_RegisterAll(&def, 1) > 0) InterlockedExchange(&g_commandsReady, 1);
}

void DebugConsole_Start(void) {
    HANDLE t;
    if (InterlockedCompareExchange(&g_started, 1, 0)) return;
    t = CreateThread(NULL, 0, StartDebugService, NULL, 0, NULL);
    if (t) CloseHandle(t);
    else {
        InterlockedExchange(&g_started, -1);
        Plugin_Log("[debugconsole] service thread creation failed error=%lu", GetLastError());
    }
}
