#include "protocol.h"
#include <tlhelp32.h>
#include <shlobj.h>
#include <stdio.h>
#include <string>
#include <vector>
#include <deque>
#include <mutex>
#include <thread>
#include <atomic>
#include <algorithm>

static DWORD g_pid;
static HANDLE g_game, g_pipe = INVALID_HANDLE_VALUE, g_mutex;
static uint32_t g_id;
static std::mutex g_display;
static std::wstring g_edit;
static size_t g_cursor;
static std::atomic<bool> g_stop(false);
static std::atomic<int> g_filter(0);
static HANDLE g_in, g_out;
static DWORD g_oldMode;
static bool g_console;

static std::wstring Wide(const std::string& text) {
    int n = MultiByteToWideChar(CP_UTF8, 0, text.data(), (int)text.size(), NULL, 0);
    std::wstring w(n, 0);
    if (n) MultiByteToWideChar(CP_UTF8, 0, text.data(), (int)text.size(), &w[0], n);
    for (auto& c : w) if ((c < 32 && c != L'\t') || c == 127) c = L' ';
    return w;
}
static std::string Utf8(const std::wstring& w) {
    int n = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, w.data(), (int)w.size(), NULL, 0, NULL, NULL);
    std::string s(n, 0);
    if (n) WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, w.data(), (int)w.size(), &s[0], n, NULL, NULL);
    return s;
}
static void Write(const std::wstring& w) {
    DWORD n;
    if (g_console) WriteConsoleW(g_out, w.data(), (DWORD)w.size(), &n, NULL);
    else { auto s = Utf8(w); fwrite(s.data(), 1, s.size(), stdout); fflush(stdout); }
}
static void ErasePrompt() {
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (!GetConsoleScreenBufferInfo(g_out, &info)) return;
    COORD start = {0, info.dwCursorPosition.Y}; DWORD n;
    FillConsoleOutputCharacterW(g_out, L' ', info.dwSize.X, start, &n);
    SetConsoleCursorPosition(g_out, start);
}
static void Prompt() {
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (!g_console || !GetConsoleScreenBufferInfo(g_out, &info)) return;
    size_t width = info.dwSize.X > 6 ? info.dwSize.X - 5 : 1;
    size_t begin = g_cursor > width ? g_cursor - width : 0;
    std::wstring visible = g_edit.substr(begin, width);
    Write(L"> " + visible);
    COORD pos = {(SHORT)(2 + g_cursor - begin), info.dwCursorPosition.Y};
    SetConsoleCursorPosition(g_out, pos);
}
static void Print(const std::wstring& line) {
    std::lock_guard<std::mutex> lock(g_display);
    if (g_console) ErasePrompt();
    Write(line + L"\r\n");
    if (g_console) Prompt();
}

struct Tail {
    std::wstring path;
    uint64_t offset = 0, identity = 0;
    DWORD volume = 0;
    std::string partial;
    std::string sentinel;
    bool dropping = false;
    std::vector<std::string> Poll() {
        std::vector<std::string> rows;
        HANDLE h = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
        if (h == INVALID_HANDLE_VALUE) return rows;
        BY_HANDLE_FILE_INFORMATION info; LARGE_INTEGER size;
        if (!GetFileInformationByHandle(h, &info) || !GetFileSizeEx(h, &size)) { CloseHandle(h); return rows; }
        uint64_t id = ((uint64_t)info.nFileIndexHigh << 32) | info.nFileIndexLow;
        bool changed = id != identity || info.dwVolumeSerialNumber != volume || (uint64_t)size.QuadPart < offset;
        if (!changed && !sentinel.empty()) {
            LARGE_INTEGER pos; pos.QuadPart = offset - sentinel.size(); char previous[32]; DWORD n;
            changed = !SetFilePointerEx(h, pos, NULL, FILE_BEGIN) || !ReadFile(h, previous, (DWORD)sentinel.size(), &n, NULL) ||
                n != sentinel.size() || memcmp(previous, sentinel.data(), n) != 0;
        }
        if (changed) {
            if (identity) rows.push_back("[log reset/recreated]");
            identity = id; volume = info.dwVolumeSerialNumber; offset = 0; partial.clear(); sentinel.clear(); dropping = false;
        }
        if ((uint64_t)size.QuadPart - offset > 1024 * 1024) {
            offset = (uint64_t)size.QuadPart - 65536; partial.clear(); sentinel.clear(); dropping = true;
            rows.push_back("[log backlog exceeded 1MiB; older output skipped]");
        }
        LARGE_INTEGER pos; pos.QuadPart = offset;
        if (!SetFilePointerEx(h, pos, NULL, FILE_BEGIN)) { CloseHandle(h); return rows; }
        char buffer[65536]; DWORD n = 0;
        if (ReadFile(h, buffer, sizeof(buffer), &n, NULL)) {
            offset += n;
            sentinel.append(buffer, n);
            if (sentinel.size() > 32) sentinel.erase(0, sentinel.size() - 32);
            size_t emitted = 0;
            for (DWORD i = 0; i < n; ++i) {
                char c = buffer[i];
                if (c == '\n') {
                    if (!dropping) {
                        if (!partial.empty() && partial.back() == '\r') partial.pop_back();
                        if (emitted++ < 256) rows.push_back(partial);
                    }
                    partial.clear(); dropping = false;
                } else if (!dropping) {
                    partial.push_back(c);
                    if (partial.size() >= 65536) { partial.clear(); dropping = true; rows.push_back("[oversized log line skipped]"); }
                }
            }
            if (emitted > 256) rows.push_back("[output rate limit: extra lines skipped]");
        }
        CloseHandle(h); return rows;
    }
};

static bool Connect() {
    if (g_pipe != INVALID_HANDLE_VALUE) {
        DWORD available;
        if (PeekNamedPipe(g_pipe, NULL, 0, NULL, &available, NULL)) return true;
        CloseHandle(g_pipe); g_pipe = INVALID_HANDLE_VALUE;
    }
    wchar_t name[128]; DcPipeName(name, _countof(name), g_pid);
    ULONGLONG end = GetTickCount64() + 3000;
    do {
        g_pipe = CreateFileW(name, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING,
            FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION, NULL);
        if (g_pipe != INVALID_HANDLE_VALUE) {
            ULONG server;
            if (GetNamedPipeServerProcessId(g_pipe, &server) && server == g_pid &&
                WaitForSingleObject(g_game, 0) == WAIT_TIMEOUT) return true;
            CloseHandle(g_pipe); g_pipe = INVALID_HANDLE_VALUE; return false;
        }
        WaitNamedPipeW(name, 100);
        Sleep(50);
    } while (GetTickCount64() < end && WaitForSingleObject(g_game, 0) == WAIT_TIMEOUT);
    return false;
}
static bool Send(const std::string& line, DcResponse& result, std::string& output) {
    if (line.empty() || line.size() > DC_INPUT_MAX) { output = "Input must be 1..2048 UTF-8 bytes; not sent."; return false; }
    if (!Connect()) { output = "Cannot connect to this game's local console service."; return false; }
    DcRequest req = {DC_MAGIC, DC_PROTOCOL_VERSION, ++g_id, (uint32_t)line.size()};
    if (!req.id) req.id = ++g_id;
    if (DcTransfer(g_pipe, &req, sizeof(req), 1, 5000) &&
        DcTransfer(g_pipe, (void*)line.data(), req.length, 1, 5000) &&
        DcTransfer(g_pipe, &result, sizeof(result), 0, 15000) &&
        result.magic == DC_MAGIC && result.version == DC_PROTOCOL_VERSION && result.id == req.id && result.length <= DC_OUTPUT_MAX) {
        output.resize(result.length);
        if (!result.length || DcTransfer(g_pipe, &output[0], result.length, 0, 5000)) return true;
    }
    CloseHandle(g_pipe); g_pipe = INVALID_HANDLE_VALUE;
    output = "Connection lost: execution outcome is unknown. NOT automatically retried; reconnect before deciding to repeat.";
    return false;
}

static void Logs(std::wstring root) {
    wchar_t docs[MAX_PATH];
    std::vector<Tail> tails;
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_PERSONAL, NULL, SHGFP_TYPE_CURRENT, docs))) {
        tails.push_back({std::wstring(docs) + L"\\Paradox Interactive\\Hearts of Iron IV\\logs\\game.log"});
        tails.push_back({std::wstring(docs) + L"\\Paradox Interactive\\Hearts of Iron IV\\logs\\error.log"});
    } else { tails.push_back({L""}); tails.push_back({L""}); }
    tails.push_back({root + L"\\reports\\mod_loader_tbb.log"});
    const wchar_t* labels[] = {L"GAME", L"ERROR", L"PLUGIN"};
    while (!g_stop && WaitForSingleObject(g_game, 0) == WAIT_TIMEOUT) {
        for (size_t i = 0; i < tails.size(); ++i) {
            for (const auto& line : tails[i].Poll()) {
                if (!g_filter || g_filter == (int)i + 1) {
                    SYSTEMTIME st; GetLocalTime(&st); wchar_t tag[80];
                    _snwprintf_s(tag, _countof(tag), _TRUNCATE, L"[%02u:%02u:%02u][%s] ", st.wHour, st.wMinute, st.wSecond, labels[i]);
                    Print(tag + Wide(line));
                }
            }
        }
        Sleep(200);
    }
    if (!g_stop) { Print(L"[CONSOLE] Game exited; closing console."); g_stop = true; }
}

static int SelfTest() {
    wchar_t temp[MAX_PATH], file[MAX_PATH]; GetTempPathW(MAX_PATH, temp); GetTempFileNameW(temp, L"hdc", 0, file);
    DeleteFileW(file); Tail t{file}; int count = 0;
    auto check = [&](bool ok, const char* name) { printf("%s %s\n", ok ? "PASS" : "FAIL", name); if (ok) ++count; };
    auto write = [&](const std::string& s, DWORD disposition) {
        HANDLE h = CreateFileW(file, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_DELETE, NULL, disposition, 0, NULL);
        SetFilePointer(h, 0, NULL, FILE_END); DWORD n; WriteFile(h, s.data(), (DWORD)s.size(), &n, NULL); CloseHandle(h);
    };
    check(t.Poll().empty(), "missing-file");
    write("partial", CREATE_ALWAYS); check(t.Poll().empty(), "partial-line");
    write(" done\n", OPEN_EXISTING); check(t.Poll() == std::vector<std::string>{"partial done"}, "partial-complete");
    check(t.Poll().empty(), "no-duplicate");
    write("\xe4\xb8", OPEN_EXISTING); check(t.Poll().empty(), "split-utf8-prefix");
    write("\xad\n", OPEN_EXISTING); check(t.Poll() == std::vector<std::string>{"\xe4\xb8\xad"}, "split-utf8-complete");
    write("r\n", CREATE_ALWAYS); auto r = t.Poll(); check(r.size() == 2 && r.back() == "r", "truncate");
    DeleteFileW(file); write("new-file\n", CREATE_ALWAYS); r = t.Poll(); check(r.size() == 2 && r.back() == "new-file", "recreate");
    write(std::string(70000, 'x') + "\nlast\n", OPEN_EXISTING); r = t.Poll(); auto r2 = t.Poll();
    check(r.size() == 1 && r[0] == "[oversized log line skipped]" && r2.back() == "last", "long-line-bounded");
    write(std::string(2 * 1024 * 1024, 'y') + "\ntail\n", OPEN_EXISTING); r = t.Poll();
    check(r.front().find("backlog") != std::string::npos && r.back() == "tail", "backlog-bounded");
    write(std::string(600, '\n'), OPEN_EXISTING); r = t.Poll(); check(r.size() == 257, "rate-limit");
    write("old\n", CREATE_ALWAYS); t.Poll();
    write(std::string(500, 'z') + "\n", CREATE_ALWAYS); r = t.Poll();
    check(r.size() == 2 && r.back() == std::string(500, 'z'), "truncate-regrow-between-polls");
    check(Wide("\x1b[31m") == L" [31m", "escape-sanitized");
    check(Utf8(Wide("\xe4\xb8\xad")) == "\xe4\xb8\xad", "utf8-roundtrip");
    DeleteFileW(file); printf("%d/14\n", count); return count == 14 ? 0 : 1;
}

int wmain(int argc, wchar_t** argv) {
    std::wstring command;
    DWORD logsMs = 0;
    for (int i = 1; i < argc; ++i) {
        if (!wcscmp(argv[i], L"--self-test")) return SelfTest();
        if (!wcscmp(argv[i], L"--pid") && i + 1 < argc) g_pid = wcstoul(argv[++i], NULL, 10);
        else if (!wcscmp(argv[i], L"--command") && i + 1 < argc) command = argv[++i];
        else if (!wcscmp(argv[i], L"--logs-ms") && i + 1 < argc) {
            logsMs = wcstoul(argv[++i], NULL, 10);
            if (!logsMs || logsMs > 60000) { fprintf(stderr, "--logs-ms range: 1..60000\n"); return 2; }
        }
        else { fwprintf(stderr, L"Usage: hoi4_debug_console.exe [--pid GAME_PID] [--command \"game command\" | --logs-ms 1000] | --self-test\n"); return 2; }
    }
    if (!g_pid) {
        HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0); PROCESSENTRY32W e = {sizeof(e)};
        if (Process32FirstW(snap, &e)) do {
            if (!_wcsicmp(e.szExeFile, L"hoi4.exe")) {
                if (g_pid) { CloseHandle(snap); fprintf(stderr, "Multiple games: specify --pid.\n"); return 2; }
                g_pid = e.th32ProcessID;
            }
        } while (Process32NextW(snap, &e));
        CloseHandle(snap);
    }
    g_game = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, g_pid);
    if (!g_game) { fprintf(stderr, "Game is not running or cannot be opened.\n"); return 2; }
    wchar_t gamePath[32768]; DWORD len = _countof(gamePath);
    if (!QueryFullProcessImageNameW(g_game, 0, gamePath, &len)) return 2;
    wchar_t* slash = wcsrchr(gamePath, L'\\');
    if (!slash || _wcsicmp(slash + 1, L"hoi4.exe")) { fprintf(stderr, "PID is not hoi4.exe.\n"); return 2; }
    *slash = 0;
    if (logsMs && !command.empty()) { fprintf(stderr, "Choose --command or --logs-ms, not both.\n"); return 2; }
    if (logsMs) {
        std::thread logs(Logs, std::wstring(gamePath)); Sleep(logsMs); g_stop = true; logs.join();
        CloseHandle(g_game); return 0;
    }
    if (!command.empty()) {
        DcResponse result = {0}; std::string text;
        bool ok = Send(Utf8(command), result, text);
        printf("transport=%u id=%u status=%u ok=%u thread=%u\n", ok, result.id, result.status, result.ok, result.thread);
        fwrite(text.data(), 1, text.size(), stdout); printf("\n"); CloseHandle(g_game);
        if (g_pipe != INVALID_HANDLE_VALUE) CloseHandle(g_pipe);
        return !ok ? 2 : result.status != DC_EXECUTED ? 3 : result.ok ? 0 : 1;
    }
    wchar_t mutexName[120]; _snwprintf_s(mutexName, _countof(mutexName), _TRUNCATE, L"Local\\hoi4-plugin-console-%lu", g_pid);
    g_mutex = CreateMutexW(NULL, FALSE, mutexName);
    if (!g_mutex || GetLastError() == ERROR_ALREADY_EXISTS) { fprintf(stderr, "Console is already open for this game.\n"); return 0; }
    g_in = GetStdHandle(STD_INPUT_HANDLE); g_out = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD outMode;
    g_console = GetConsoleMode(g_in, &g_oldMode) && GetConsoleMode(g_out, &outMode);
    if (!g_console) { fprintf(stderr, "Interactive console required; use --command for scripted requests.\n"); return 2; }
    SetConsoleMode(g_in, (g_oldMode | ENABLE_WINDOW_INPUT | ENABLE_EXTENDED_FLAGS) & ~(ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_QUICK_EDIT_MODE | ENABLE_PROCESSED_INPUT));
    SetConsoleTitleW(L"HOI4 plugin debug console (local / single-player)");
    Write(L"HOI4 external console v1. /help for local actions; game commands use the native dispatcher.\r\n"); Prompt();
    std::thread logs(Logs, std::wstring(gamePath));
    std::deque<std::wstring> history; size_t hist = 0; bool quit = false;
    while (!g_stop && !quit) {
        if (WaitForSingleObject(g_in, 100) != WAIT_OBJECT_0) continue;
        INPUT_RECORD rec; DWORD n; if (!ReadConsoleInputW(g_in, &rec, 1, &n)) break;
        if (rec.EventType != KEY_EVENT || !rec.Event.KeyEvent.bKeyDown) continue;
        auto k = rec.Event.KeyEvent;
        if (k.wVirtualKeyCode == VK_RETURN) {
            std::wstring line;
            { std::lock_guard<std::mutex> lock(g_display); line = g_edit; ErasePrompt(); Write(L"> " + line + L"\r\n"); g_edit.clear(); g_cursor = 0; Prompt(); }
            if (line.empty()) continue;
            if (history.empty() || history.back() != line) { history.push_back(line); if (history.size() > 128) history.pop_front(); } hist = history.size();
            if (line == L"/quit") quit = true;
            else if (line == L"/help") Print(L"[CONSOLE] /filter all|game|error|plugin, /clear, /reconnect, /quit; Up/Down history; Left/Right/Home/End/Delete edit. No OS shell.");
            else if (line == L"/reconnect") { if (g_pipe != INVALID_HANDLE_VALUE) CloseHandle(g_pipe); g_pipe = INVALID_HANDLE_VALUE; Print(Connect() ? L"[CONSOLE] Reconnected." : L"[CONSOLE] Service unavailable."); }
            else if (line == L"/clear") {
                std::lock_guard<std::mutex> lock(g_display); CONSOLE_SCREEN_BUFFER_INFO info; GetConsoleScreenBufferInfo(g_out, &info); DWORD w; COORD zero = {0,0};
                FillConsoleOutputCharacterW(g_out, L' ', info.dwSize.X * info.dwSize.Y, zero, &w); SetConsoleCursorPosition(g_out, zero); Prompt();
            } else if (line.rfind(L"/filter ", 0) == 0) {
                std::wstring f = line.substr(8); int filter = f == L"all" ? 0 : f == L"game" ? 1 : f == L"error" ? 2 : f == L"plugin" ? 3 : -1;
                if (filter < 0) Print(L"[CONSOLE] Unknown filter."); else { g_filter = filter; Print(L"[CONSOLE] Filter=" + f); }
            } else if (line[0] == L'/') Print(L"[CONSOLE] Unknown local action; /help.");
            else {
                DcResponse res = {0}; std::string text; bool ok = Send(Utf8(line), res, text);
                wchar_t meta[160]; _snwprintf_s(meta, _countof(meta), _TRUNCATE, L"[RESULT id=%u status=%u ok=%u thread=%u] ", res.id, res.status, res.ok, res.thread);
                Print((ok ? std::wstring(meta) : L"[CONSOLE] ") + Wide(text));
            }
            continue;
        }
        std::lock_guard<std::mutex> lock(g_display); ErasePrompt();
        switch (k.wVirtualKeyCode) {
        case VK_LEFT: if (g_cursor) --g_cursor; break;
        case VK_RIGHT: if (g_cursor < g_edit.size()) ++g_cursor; break;
        case VK_HOME: g_cursor = 0; break;
        case VK_END: g_cursor = g_edit.size(); break;
        case VK_BACK: if (g_cursor) g_edit.erase(--g_cursor, 1); break;
        case VK_DELETE: if (g_cursor < g_edit.size()) g_edit.erase(g_cursor, 1); break;
        case VK_UP: if (hist) { g_edit = history[--hist]; g_cursor = g_edit.size(); } break;
        case VK_DOWN: if (hist < history.size()) { ++hist; g_edit = hist < history.size() ? history[hist] : L""; g_cursor = g_edit.size(); } break;
        default: if (k.uChar.UnicodeChar >= 32 && g_edit.size() < 2048) g_edit.insert(g_cursor++, 1, k.uChar.UnicodeChar); break;
        }
        Prompt();
    }
    g_stop = true; logs.join(); SetConsoleMode(g_in, g_oldMode);
    if (g_pipe != INVALID_HANDLE_VALUE) CloseHandle(g_pipe);
    CloseHandle(g_mutex); CloseHandle(g_game); return 0;
}
