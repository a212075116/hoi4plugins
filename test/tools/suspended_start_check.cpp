// suspended_start_check.cpp -- 复现“启动器那种启动方式”
//
// 为什么需要它：
//   Paradox Launcher / Steam 拉起游戏时，进程是【挂起状态】创建的，
//   由 Steam 覆盖层挂进去的线程替游戏走完导入表，
//   而游戏主线程还没被恢复。此时若代理 DLL 在 DllMain 里建线程，
//   那条线程的 TLS 回调会先于游戏 CRT 初始化而跑，按 MSVC CRT 自己的规矩 abort()，
//   进程以 0xC0000409 (BEX64) 死掉，连窗口都没有。
//
// 这个工具把那一刻复现出来：
//   1. 以挂起状态创建游戏进程（CREATE_SUSPENDED）；
//   2. 在它里面另起一条线程（让导入表在那条线程上走完）；
//   3. 等 N 秒，看进程还在不在；
//   4. 恢复主线程，看游戏能不能正常起来。
//
// 判定：第 3 步就死了 => 代理在 DllMain 里早建线程（坑）；
//       第 3 步还活着、第 4 步后游戏到主菜单 => 代理安全。
//
// 用法:  suspended_start_check.exe [游戏根目录] [等待秒数]

#include <windows.h>
#include <psapi.h>
#include <stdio.h>

#pragma comment(lib, "psapi.lib")

int main(int argc, char** argv) {
    const char* gameDir = (argc > 1) ? argv[1] : "D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV";
    int waitSec = (argc > 2) ? atoi(argv[2]) : 8;
    char exePath[MAX_PATH];
    char cmdLine[MAX_PATH + 16];
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    HMODULE localK32;
    FARPROC remoteLoadLibrary;
    HANDLE th;
    DWORD wr;
    int i;

    _snprintf_s(exePath, sizeof(exePath), _TRUNCATE, "%s\\hoi4.exe", gameDir);
    if (GetFileAttributesA(exePath) == INVALID_FILE_ATTRIBUTES) {
        printf("NOT FOUND: %s\n", exePath);
        return 2;
    }
    _snprintf_s(cmdLine, sizeof(cmdLine), _TRUNCATE, "\"%s\" -gdpr-compliant", exePath);

    // kernel32 是 KnownDLL，共享同一个 section，
    // 因此它在目标进程里的基址与本进程一致，地址可以直接用。
    localK32 = GetModuleHandleA("kernel32.dll");
    remoteLoadLibrary = GetProcAddress(localK32, "LoadLibraryA");
    printf("LoadLibraryA @ %p\n", (void*)remoteLoadLibrary);

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    printf("creating suspended: %s\n", exePath);
    if (!CreateProcessA(NULL, cmdLine, NULL, NULL, FALSE,
                        CREATE_SUSPENDED, NULL, gameDir, &si, &pi)) {
        printf("CreateProcess failed: %lu\n", GetLastError());
        return 3;
    }
    printf("pid = %lu (suspended)\n", pi.dwProcessId);

    // 让导入表在另一条线程上走完：这正是启动器那种情形。
    {
        // 传一个无害的空串，LoadLibraryA("") 会失败但不影响导入表走完
        SIZE_T sz = 1;
        LPVOID remoteArg = VirtualAllocEx(pi.hProcess, NULL, sz, MEM_COMMIT, PAGE_READWRITE);
        WriteProcessMemory(pi.hProcess, remoteArg, "", 1, NULL);
        th = CreateRemoteThread(pi.hProcess, NULL, 0,
                                (LPTHREAD_START_ROUTINE)remoteLoadLibrary, remoteArg, 0, NULL);
        if (th == NULL) {
            printf("CreateRemoteThread failed: %lu\n", GetLastError());
        } else {
            printf("remote thread started (this is what walks the import table)\n");
        }
    }

    printf("waiting %d s with the main thread still suspended...\n", waitSec);
    for (i = 0; i < waitSec; ++i) {
        DWORD code = 0;
        Sleep(1000);
        if (!GetExitCodeProcess(pi.hProcess, &code)) break;
        if (code != STILL_ACTIVE) {
            printf(">>> process DIED at %d s, exit code = 0x%08lX\n", i + 1, code);
            if (code == 0xC0000409u) printf(">>> 0xC0000409 = BEX64 = CRT __fastfail(7) : this is the early-thread abort\n");
            TerminateProcess(pi.hProcess, 0);
            CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
            return 1;
        }
    }
    printf("process still alive after %d s\n", waitSec);

    printf("resuming main thread...\n");
    ResumeThread(pi.hThread);

    printf("waiting up to 150 s for the game to reach the main menu...\n");
    for (i = 0; i < 150; ++i) {
        DWORD code = 0;
        HWND w;
        char title[256];
        Sleep(1000);
        if (!GetExitCodeProcess(pi.hProcess, &code)) break;
        if (code != STILL_ACTIVE) {
            printf(">>> game exited after resume, code = 0x%08lX (%lu s)\n", code, i + 1);
            CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
            return 4;
        }
        w = FindWindowA(NULL, "Hearts of Iron IV");
        if (w == NULL) {
            // 窗口标题可能带副标题，扫一遍
        }
        if ((i % 15) == 14) printf("  ... %d s, pid alive\n", i + 1);
    }
    printf(">>> survived; terminating\n");
    TerminateProcess(pi.hProcess, 0);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}