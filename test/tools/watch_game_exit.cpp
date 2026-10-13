#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <io.h>
#include <share.h>
#include <cstdio>
#include <cwchar>
#include <vector>

int wmain(int argc, wchar_t** argv) {
    if (argc != 5) return 2;
    DWORD pid = wcstoul(argv[2], nullptr, 10);
    if (!pid) return 2;
    if (wcscmp(argv[1], L"--observe") == 0) {
        HANDLE process = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
        if (!process) return 3;
        wchar_t actual[32768]; DWORD chars = 32768;
        if (!QueryFullProcessImageNameW(process, 0, actual, &chars) || _wcsicmp(actual, argv[4]) != 0) {
            CloseHandle(process); return 4;
        }
        FILE* file = _wfsopen(argv[3], L"wb", _SH_DENYWR);
        if (!file) { CloseHandle(process); return 5; }
        BOOL inJob = TRUE; IsProcessInJob(GetCurrentProcess(), nullptr, &inJob);
        fprintf(file, "{\"event\":\"watch_started\",\"pid\":%lu,\"watcher_pid\":%lu,\"watcher_in_job\":%s,\"timeout_kills_game\":false}\n", pid, GetCurrentProcessId(), inJob ? "true" : "false");
        fflush(file); FlushFileBuffers((HANDLE)_get_osfhandle(_fileno(file)));
        DWORD wait = WaitForSingleObject(process, INFINITE), code = STILL_ACTIVE;
        BOOL ok = GetExitCodeProcess(process, &code);
        SYSTEMTIME now; GetSystemTime(&now);
        fprintf(file, "{\"event\":\"process_ended\",\"pid\":%lu,\"wait\":%lu,\"query_ok\":%s,\"exit_code\":%lu,\"exit_hex\":\"0x%08lX\",\"utc\":\"%04u-%02u-%02uT%02u:%02u:%02uZ\"}\n", pid, wait, ok ? "true" : "false", code, code, now.wYear, now.wMonth, now.wDay, now.wHour, now.wMinute, now.wSecond);
        fflush(file); FlushFileBuffers((HANDLE)_get_osfhandle(_fileno(file)));
        fclose(file); CloseHandle(process); return ok ? 0 : 6;
    }
    if (wcscmp(argv[1], L"--start") != 0) return 2;
    DWORD shellPid = 0; GetWindowThreadProcessId(GetShellWindow(), &shellPid);
    HANDLE parent = OpenProcess(PROCESS_CREATE_PROCESS, FALSE, shellPid);
    if (!parent) return 7;
    SIZE_T bytes = 0; InitializeProcThreadAttributeList(nullptr, 1, 0, &bytes);
    std::vector<char> storage(bytes);
    STARTUPINFOEXW si = {}; si.StartupInfo.cb = sizeof(si);
    si.lpAttributeList = (LPPROC_THREAD_ATTRIBUTE_LIST)storage.data();
    if (!InitializeProcThreadAttributeList(si.lpAttributeList, 1, 0, &bytes) ||
        !UpdateProcThreadAttribute(si.lpAttributeList, 0, PROC_THREAD_ATTRIBUTE_PARENT_PROCESS, &parent, sizeof(parent), nullptr, nullptr)) {
        CloseHandle(parent); return 8;
    }
    wchar_t self[32768], command[65536];
    GetModuleFileNameW(nullptr, self, 32768);
    _snwprintf_s(command, 65536, _TRUNCATE, L"\"%ls\" --observe %lu \"%ls\" \"%ls\"", self, pid, argv[3], argv[4]);
    PROCESS_INFORMATION child = {};
    BOOL ok = CreateProcessW(self, command, nullptr, nullptr, FALSE, EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW, nullptr, nullptr, &si.StartupInfo, &child);
    DeleteProcThreadAttributeList(si.lpAttributeList); CloseHandle(parent);
    if (!ok) return 9;
    BOOL job = TRUE; BOOL queried = IsProcessInJob(child.hProcess, nullptr, &job);
    printf("{\"observer_pid\":%lu,\"game_pid\":%lu,\"in_job\":%s,\"query_ok\":%s}\n", child.dwProcessId, pid, job ? "true" : "false", queried ? "true" : "false");
    CloseHandle(child.hThread); CloseHandle(child.hProcess); return queried && !job ? 0 : 10;
}
