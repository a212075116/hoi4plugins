#include "protocol.h"
#include "completion.h"
#include "command_catalog.h"
#include <tlhelp32.h>
#include <shlobj.h>
#include <stdio.h>
#include <iostream>
#include <string>
#include <vector>
#include <deque>
#include <mutex>
#include <thread>
#include <atomic>
#include <algorithm>
#include <condition_variable>
#include <functional>
#include <chrono>

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
static bool g_interactiveLane;
static HANDLE g_cancel;
static std::wstring g_logDirectory;
static int g_wheelRemainder;
static uint64_t g_editRevision;
struct CompletionState {
    bool pending = false, ready = false;
    uint64_t revision = 0;
    std::wstring edit;
    size_t cursor = 0, begin = 0, end = 0;
    std::string prefix, error;
    std::vector<std::string> names;
};
static CompletionState g_completion;

static void ScrollConsole(const MOUSE_EVENT_RECORD& mouse) {
    if (mouse.dwEventFlags != MOUSE_WHEELED) return;
    std::lock_guard<std::mutex> lock(g_display);
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (!GetConsoleScreenBufferInfo(g_out, &info)) return;
    UINT lines = 3;
    SystemParametersInfoW(SPI_GETWHEELSCROLLLINES, 0, &lines, 0);
    int delta = g_wheelRemainder + (SHORT)HIWORD(mouse.dwButtonState);
    int notches = delta / WHEEL_DELTA;
    g_wheelRemainder = delta % WHEEL_DELTA;
    if (!notches || !lines) return;
    int height = info.srWindow.Bottom - info.srWindow.Top + 1;
    if (height <= 0 || height > info.dwSize.Y) return;
    int bottom = (std::max)(0, (std::min)((int)info.dwSize.Y - height, (int)info.dwCursorPosition.Y - height + 1));
    int64_t step = lines == WHEEL_PAGESCROLL ? height : lines;
    int64_t top = (int64_t)info.srWindow.Top - notches * step;
    SMALL_RECT view = info.srWindow;
    view.Top = (SHORT)(std::max)((int64_t)0, (std::min)((int64_t)bottom, top));
    view.Bottom = (SHORT)(view.Top + height - 1);
    SetConsoleWindowInfo(g_out, TRUE, &view);
}

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
static WORD LineAttributes(const std::wstring& line, WORD normal) {
    std::wstring tags = line;
    for (auto& c : tags) if (c >= L'A' && c <= L'Z') c += L'a' - L'A';
    WORD foreground;
    if (tags.find(L"[error]") != std::wstring::npos || tags.find(L"[fatal]") != std::wstring::npos)
        foreground = FOREGROUND_RED | FOREGROUND_INTENSITY;
    else if (tags.find(L"[warning]") != std::wstring::npos || tags.find(L"[waring]") != std::wstring::npos || tags.find(L"[warn]") != std::wstring::npos)
        foreground = FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY;
    else if (tags.find(L"[success]") != std::wstring::npos || tags.find(L"[ok]") != std::wstring::npos || tags.find(L"[pass]") != std::wstring::npos)
        foreground = FOREGROUND_GREEN | FOREGROUND_INTENSITY;
    else if (tags.find(L"[info]") != std::wstring::npos || tags.find(L"[notice]") != std::wstring::npos)
        foreground = FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY;
    else if (tags.find(L"[debug]") != std::wstring::npos || tags.find(L"[trace]") != std::wstring::npos)
        foreground = FOREGROUND_INTENSITY;
    else return normal;
    return (normal & ~0x0f) | foreground;
}
static void Print(const std::wstring& line) {
    std::lock_guard<std::mutex> lock(g_display);
    CONSOLE_SCREEN_BUFFER_INFO before;
    bool display = g_console && GetConsoleScreenBufferInfo(g_out, &before);
    bool history = display && before.dwCursorPosition.Y > before.srWindow.Bottom;
    if (g_console) ErasePrompt();
    if (!display) Write(line + L"\r\n");
    else {
        size_t begin = 0;
        do {
            size_t end = line.find(L'\n', begin);
            std::wstring part = line.substr(begin, end == std::wstring::npos ? end : end - begin + 1);
            SetConsoleTextAttribute(g_out, LineAttributes(part, before.wAttributes));
            Write(part);
            if (end == std::wstring::npos) break;
            begin = end + 1;
        } while (begin <= line.size());
        Write(L"\r\n");
        SetConsoleTextAttribute(g_out, before.wAttributes);
    }
    if (g_console) Prompt();
    if (history) SetConsoleWindowInfo(g_out, TRUE, &before.srWindow);
}

struct Tail {
    std::wstring path;
    uint64_t offset = 0, identity = 0;
    DWORD volume = 0;
    std::string partial;
    std::string sentinel;
    bool dropping = false;
    uint64_t Backlog() const {
        WIN32_FILE_ATTRIBUTE_DATA a;
        if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &a)) return 0;
        uint64_t n = ((uint64_t)a.nFileSizeHigh << 32) | a.nFileSizeLow;
        return n > offset ? n - offset : 0;
    }
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
        LARGE_INTEGER pos; pos.QuadPart = offset;
        if (!SetFilePointerEx(h, pos, NULL, FILE_BEGIN)) { CloseHandle(h); return rows; }
        char buffer[65536]; DWORD n = 0;
        if (ReadFile(h, buffer, sizeof(buffer), &n, NULL)) {
            DWORD consumed = 0;
            for (DWORD i = 0; i < n; ++i) {
                char c = buffer[i]; consumed = i + 1;
                if (c == '\n') {
                    if (!partial.empty() && partial.back() == '\r') partial.pop_back();
                    rows.push_back(partial); partial.clear();
                } else {
                    partial.push_back(c);
                    if (partial.size() >= 65536) {
                        size_t boundary = partial.size();
                        size_t start = boundary - 1;
                        while (start && (((unsigned char)partial[start] & 0xc0) == 0x80)) --start;
                        unsigned char lead = (unsigned char)partial[start];
                        size_t width = lead >= 0xf0 ? 4 : lead >= 0xe0 ? 3 : lead >= 0xc0 ? 2 : 1;
                        if (start + width > boundary) boundary = start;
                        rows.push_back(partial.substr(0, boundary) + " [line continues]");
                        partial.erase(0, boundary);
                    }
                }
                if (rows.size() >= 256) break;
            }
            offset += consumed;
            sentinel.append(buffer, consumed);
            if (sentinel.size() > 32) sentinel.erase(0, sentinel.size() - 32);
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
    wchar_t name[128]; if (g_interactiveLane) DcInteractivePipeName(name, _countof(name), g_pid);
    else DcPipeName(name, _countof(name), g_pid);
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
    } while (!g_stop && GetTickCount64() < end && WaitForSingleObject(g_game, 0) == WAIT_TIMEOUT);
    return false;
}
static bool Send(const std::string& line, DcResponse& result, std::string& output) {
    if (line.empty() || line.size() > DC_INPUT_MAX) { output = "Input must be 1..2048 UTF-8 bytes; not sent."; return false; }
    if (!Connect()) { output = "Cannot connect to this game's local console service."; return false; }
    DcRequest req = {DC_MAGIC, DC_PROTOCOL_VERSION, ++g_id, (uint32_t)line.size()};
    if (!req.id) req.id = ++g_id;
    if (DcTransferWithCancel(g_pipe, &req, sizeof(req), 1, 5000, g_cancel) &&
        DcTransferWithCancel(g_pipe, (void*)line.data(), req.length, 1, 5000, g_cancel) &&
        DcTransferWithCancel(g_pipe, &result, sizeof(result), 0, 15000, g_cancel) &&
        result.magic == DC_MAGIC && result.version == DC_PROTOCOL_VERSION && result.id == req.id && result.length <= DC_OUTPUT_MAX) {
        output.resize(result.length);
        if (!result.length || DcTransferWithCancel(g_pipe, &output[0], result.length, 0, 5000, g_cancel)) return true;
    }
    CloseHandle(g_pipe); g_pipe = INVALID_HANDLE_VALUE;
    output = "Connection lost: execution outcome is unknown. NOT automatically retried; reconnect before deciding to repeat.";
    return false;
}

static void CompleteWorker() {
    std::string prefix;
    { std::lock_guard<std::mutex> lock(g_display); prefix = g_completion.prefix; }
    std::string error; auto names = CommandCatalog::Query(g_pid, prefix, error);
    { std::lock_guard<std::mutex> lock(g_display); g_completion.names = std::move(names); g_completion.error = error; g_completion.ready = true; }
}
static void PrintCompletionCandidates(const std::vector<std::string>& names) {
    Print(L"[info] Matching commands (" + std::to_wstring(names.size()) + L"):");
    std::lock_guard<std::mutex> lock(g_display);
    CONSOLE_SCREEN_BUFFER_INFO before = {};
    bool display = g_console && GetConsoleScreenBufferInfo(g_out, &before);
    if (display) ErasePrompt();
    size_t rowCount = 0, rowWidth = 2;
    for (size_t i = 0; i < names.size(); ++i) {
        size_t width = display && before.dwSize.X > 4 ? (size_t)before.dwSize.X : 160;
        if (rowCount && (rowCount == Completion::RowSize() || rowWidth + names[i].size() + 2 > width)) { Write(L"\r\n"); rowCount = 0; rowWidth = 2; }
        if (!rowCount) Write(L"  ");
        if (display) SetConsoleTextAttribute(g_out, (before.wAttributes & 0xfff0) | Completion::CandidateColor(i));
        Write(Wide(names[i]));
        if (display) SetConsoleTextAttribute(g_out, before.wAttributes);
        ++rowCount; rowWidth += names[i].size() + 2;
        Write(i + 1 == names.size() ? L"\r\n" : L"  ");
    }
    if (display) { SetConsoleTextAttribute(g_out, before.wAttributes); Prompt(); }
}
static void PumpCompletion() {
    std::vector<std::string> names; std::string error; bool applied = false;
    {
        std::lock_guard<std::mutex> lock(g_display);
        if (!g_completion.ready) return;
        g_completion.ready = false; g_completion.pending = false;
        if (!Completion::SnapshotMatches(g_completion.revision, g_editRevision, g_completion.edit, g_edit, g_completion.cursor, g_cursor)) return;
        names = g_completion.names; error = g_completion.error;
        if (error.empty() && !names.empty()) {
            std::string common = Completion::Common(names);
            if (common.size() >= g_completion.prefix.size()) {
                std::wstring replacement = Wide(common), edit = g_edit;
                edit.replace(g_completion.begin, g_completion.end - g_completion.begin, replacement);
                if (Utf8(edit).size() <= DC_INPUT_MAX) { ErasePrompt(); g_edit = edit; g_cursor = g_completion.begin + replacement.size(); ++g_editRevision; Prompt(); applied = true; }
            }
        }
    }
    if (!error.empty()) Print(L"[warning] Completion unavailable: " + Wide(error));
    else if (names.empty()) Print(L"[info] No matching command.");
    else if (names.size() > 1) PrintCompletionCandidates(names);
    else if (!applied) Print(L"[warning] Completion would exceed the input limit.");
    else Print(L"[info] Completed: " + Wide(names[0]));
}

static int CompletionSelfTest() {
    int passed = 0, total = 0;
    auto check = [&](bool value) { ++total; if (value) ++passed; else printf("FAIL completion case=%d\n", total); };
    auto names = Completion::Matching({"set_variable64", "set_ruling_party", "reset_variable", "set_variable64"}, "set_");
    check(names == std::vector<std::string>({"set_ruling_party", "set_variable64"}));
    check(Completion::Common(names) == "set_");
    check(Completion::Matching({"set_variable64", "sv64"}, "sv") == std::vector<std::string>({"sv64"}));
    check(Completion::Matching({"set_variable64"}, "SET_").size() == 1);
    check(Completion::Common({"set_variable64"}) == "set_variable64");
    check(Completion::Common({"set_variable", "set_variable64"}) == "set_variable");
    size_t begin, end; std::string prefix;
    check(Completion::Token(L"  set_ arg", 6, begin, end, prefix) && begin == 2 && end == 6 && prefix == "set_");
    check(!Completion::Token(L"set_variable foo", 16, begin, end, prefix));
    check(!Completion::Token(L"set_;quit", 9, begin, end, prefix));
    check(Completion::Token(L"/he", 3, begin, end, prefix) && prefix == "/he");
    check(Completion::Matching({"[error] bad", " - desc"}, "").empty());
    check(Completion::Token(L"", 0, begin, end, prefix) && prefix.empty());
    check(Completion::Matching({"Use help to list commands", "Unknown command"}, "").empty());
    check(Completion::SnapshotMatches(1, 1, L"set_", L"set_", 4, 4));
    check(!Completion::SnapshotMatches(1, 2, L"set_", L"set_", 4, 4));
    check(!Completion::SnapshotMatches(1, 1, L"set_", L"set_x", 4, 4));
    check(!Completion::SnapshotMatches(1, 1, L"set_", L"set_", 4, 3));
    check(Completion::RowSize() == 5);
    check(Completion::CandidateColor(0) == 9 && Completion::CandidateColor(1) == 11);
    check(Completion::CandidateColor(4) == 9 && Completion::CandidateColor(5) == 11);
    printf("%d/%d completion tests; no game commands executed\n", passed, total); return passed == total ? 0 : 1;
}

static void Logs(std::wstring root) {
    wchar_t docs[MAX_PATH];
    std::vector<Tail> tails;
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_PERSONAL, NULL, SHGFP_TYPE_CURRENT, docs))) {
        tails.push_back({std::wstring(docs) + L"\\Paradox Interactive\\Hearts of Iron IV\\logs\\game.log"});
        tails.push_back({std::wstring(docs) + L"\\Paradox Interactive\\Hearts of Iron IV\\logs\\error.log"});
    } else { tails.push_back({L""}); tails.push_back({L""}); }
    tails.push_back({root + L"\\reports\\mod_loader_tbb.log"});
    if (!g_logDirectory.empty()) {
        tails.clear();
        for (auto name : {L"game.log", L"error.log", L"plugin.log"}) tails.push_back({g_logDirectory + L"\\" + name});
    }
    ULONGLONG warned = 0;
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
        uint64_t pending = 0; for (auto& t : tails) pending += t.Backlog();
        if (pending > 1024 * 1024 && GetTickCount64() - warned > 5000) {
            warned = GetTickCount64();
            Print(L"[CONSOLE] Log backlog=" + std::to_wstring(pending) + L" bytes; no complete lines skipped.");
        }
        Sleep(pending ? 5 : 200);
    }
    if (!g_stop) { Print(L"[CONSOLE] Game exited; closing console."); g_stop = true; }
}

class CommandQueue {
    std::mutex lock;
    std::condition_variable wake;
    std::deque<std::string> queue;
    bool stopping = false;
    std::function<void(const std::string&)> execute;
    std::thread worker;
    void Run() {
        for (;;) {
            std::string line;
            { std::unique_lock<std::mutex> guard(lock);
              wake.wait(guard, [&]{ return stopping || !queue.empty(); });
              if (stopping) return;
              line = std::move(queue.front()); queue.pop_front(); }
            execute(line);
        }
    }
public:
    explicit CommandQueue(std::function<void(const std::string&)> fn) : execute(std::move(fn)), worker(&CommandQueue::Run, this) {}
    bool Submit(const std::string& line) {
        std::lock_guard<std::mutex> guard(lock);
        if (stopping || queue.size() >= 8) return false;
        queue.push_back(line); wake.notify_one(); return true;
    }
    void RequestStop() {
        { std::lock_guard<std::mutex> guard(lock); stopping = true; queue.clear(); }
        if (g_cancel) SetEvent(g_cancel);
        wake.notify_all();
    }
    void Stop() {
        RequestStop(); if (worker.joinable()) worker.join();
    }
    ~CommandQueue() { Stop(); }
};
static void ExecuteLine(const std::string& line) {
    if (line == "/reconnect") {
        if (g_pipe != INVALID_HANDLE_VALUE) CloseHandle(g_pipe);
        g_pipe = INVALID_HANDLE_VALUE;
        Print(Connect() ? L"[CONSOLE] Reconnected." : L"[CONSOLE] Service unavailable.");
        return;
    }
    DcResponse res = {0}; std::string text; bool ok = Send(line, res, text);
    wchar_t meta[160]; _snwprintf_s(meta, _countof(meta), _TRUNCATE, L"[RESULT id=%u status=%u ok=%u thread=%u] ", res.id, res.status, res.ok, res.thread);
    Print((ok ? std::wstring(meta) : L"[CONSOLE] ") + Wide(text));
}
static int SelfTest() {
    wchar_t temp[MAX_PATH], file[MAX_PATH]; GetTempPathW(MAX_PATH, temp); GetTempFileNameW(temp, L"hdc", 0, file);
    DeleteFileW(file); Tail t{file}; int count = 0, total = 0;
    auto check = [&](bool ok, const char* name) { ++total; printf("%s %s\n", ok ? "PASS" : "FAIL", name); if (ok) ++count; };
    auto write = [&](const std::string& s, DWORD disposition) {
        HANDLE h = CreateFileW(file, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_DELETE, NULL, disposition, 0, NULL);
        SetFilePointer(h, 0, NULL, FILE_END); DWORD n; WriteFile(h, s.data(), (DWORD)s.size(), &n, NULL); CloseHandle(h);
    };
    auto drain = [&] { std::vector<std::string> all; for (int i=0;i<10000;++i) { auto r=t.Poll(); all.insert(all.end(),r.begin(),r.end()); if (!t.Backlog()) break; } return all; };
    check(t.Poll().empty(), "missing-file");
    write("partial", CREATE_ALWAYS); check(t.Poll().empty(), "partial-line");
    write(" done\n", OPEN_EXISTING); check(t.Poll() == std::vector<std::string>{"partial done"}, "partial-complete");
    check(t.Poll().empty(), "no-duplicate");
    write("\xe4\xb8", OPEN_EXISTING); check(t.Poll().empty(), "split-utf8-prefix");
    write("\xad\n", OPEN_EXISTING); check(t.Poll() == std::vector<std::string>{"\xe4\xb8\xad"}, "split-utf8-complete");
    write("r\n", CREATE_ALWAYS); auto r=t.Poll(); check(r.size()==2 && r.back()=="r", "truncate");
    DeleteFileW(file); write("new-file\n", CREATE_ALWAYS); r=t.Poll(); check(r.size()==2 && r.back()=="new-file", "recreate");
    write(std::string(70000,'x')+"\nlast\n", OPEN_EXISTING); r=drain();
    check(r.size()==3 && r[0]==std::string(65536,'x')+" [line continues]" && r[1]==std::string(4464,'x') && r.back()=="last", "long-line-lossless-chunks");
    std::string expected; for (int i=0;i<90000;++i) expected+="SEQ:"+std::to_string(i)+" payload\n";
    write(expected, OPEN_EXISTING); r=drain(); std::string actual; for(auto& line:r) actual+=line+'\n';
    check(actual==expected, "large-backlog-lossless");
    write(std::string(600,'\n'), OPEN_EXISTING); r=drain(); check(r.size()==600, "budget-resumes-without-drop");
    write("old\n",CREATE_ALWAYS); t.Poll(); write(std::string(500,'z')+"\n",CREATE_ALWAYS); r=t.Poll();
    check(r.size()==2 && r.back()==std::string(500,'z'), "truncate-regrow-between-polls");
    check(Wide("\x1b[31m")==L" [31m", "escape-sanitized");
    check(Utf8(Wide("\xe4\xb8\xad"))=="\xe4\xb8\xad", "utf8-roundtrip");
    std::atomic<bool> entered(false), release(false); std::atomic<int> executed(0);
    CommandQueue q([&](const std::string&) { entered=true; while(!release) Sleep(1); ++executed; });
    q.Submit("slow"); while(!entered) Sleep(1);
    auto start=GetTickCount64(); bool accepted=true; for(int i=0;i<8;++i) accepted &= q.Submit("queued");
    check(accepted && GetTickCount64()-start<100, "submit-does-not-block-input");
    check(!q.Submit("overflow"), "input-queue-bounded"); q.RequestStop(); release=true; q.Stop();
    check(executed==1, "shutdown-cancels-unsent-queue");
    DeleteFileW(file); printf("%d/%d\n",count,total); return count==total?0:1;
}

int wmain(int argc, wchar_t** argv) {
    std::wstring command;
    DWORD logsMs = 0; bool sessionStdio = false, completionOnly = false;
    for (int i = 1; i < argc; ++i) {
        if (!wcscmp(argv[i], L"--self-test")) return SelfTest();
        if (!wcscmp(argv[i], L"--completion-self-test")) return CompletionSelfTest();
        if (!wcscmp(argv[i], L"--pid") && i + 1 < argc) g_pid = wcstoul(argv[++i], NULL, 10);
        else if (!wcscmp(argv[i], L"--session-stdio")) { sessionStdio = true; g_interactiveLane = true; }
        else if (!wcscmp(argv[i], L"--log-dir") && i + 1 < argc) g_logDirectory = argv[++i];
        else if (!wcscmp(argv[i], L"--interactive-command") && i + 1 < argc) { command = argv[++i]; g_interactiveLane = true; }
        else if (!wcscmp(argv[i], L"--command") && i + 1 < argc) command = argv[++i];
        else if (!wcscmp(argv[i], L"--complete") && i + 1 < argc) { command = argv[++i]; completionOnly = true; }
        else if (!wcscmp(argv[i], L"--logs-ms") && i + 1 < argc) {
            logsMs = wcstoul(argv[++i], NULL, 10);
            if (!logsMs || logsMs > 60000) { fprintf(stderr, "--logs-ms range: 1..60000\n"); return 2; }
        }
        else { fwprintf(stderr, L"Usage: hoi4_debug_console.exe [--pid GAME_PID] [--command \"game command\" | --complete PREFIX | --logs-ms 1000] | --self-test | --completion-self-test\n"); return 2; }
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
    g_cancel = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!g_cancel) return 2;
    if (sessionStdio) {
        setvbuf(stdout, NULL, _IONBF, 0);
        CommandQueue commands(ExecuteLine); std::string line;
        std::thread logWorker;
        if (!g_logDirectory.empty()) logWorker = std::thread(Logs, std::wstring(gamePath));
        while (std::getline(std::cin, line)) {
            if (line == "/quit") break;
            if (line == "/help") { Print(L"[LOCAL] responsive"); continue; }
            if (!commands.Submit(line)) Print(L"[CONSOLE] Queue busy; command not accepted.");
            else Print(L"[QUEUED] " + Wide(line));
        }
        g_stop = true; commands.Stop();
        if (logWorker.joinable()) logWorker.join();
        if (g_pipe != INVALID_HANDLE_VALUE) CloseHandle(g_pipe);
        CloseHandle(g_cancel); CloseHandle(g_game); return 0;
    }
    if (logsMs) {
        std::thread logs(Logs, std::wstring(gamePath)); Sleep(logsMs); g_stop = true; logs.join();
        CloseHandle(g_game); return 0;
    }
    if (completionOnly) {
        std::string prefix = Utf8(command), error;
        if (prefix.size() > 128 || !std::all_of(prefix.begin(), prefix.end(), Completion::NameChar)) return 2;
        auto names = CommandCatalog::Query(g_pid, prefix, error);
        if (!error.empty()) { fprintf(stderr, "%s\n", error.c_str()); return 3; }
        for (const auto& name : names) printf("%s\n", name.c_str());
        return 0;
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
    g_interactiveLane = true;
    SetConsoleMode(g_in, (g_oldMode | ENABLE_WINDOW_INPUT | ENABLE_EXTENDED_FLAGS) & ~(ENABLE_MOUSE_INPUT | ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_QUICK_EDIT_MODE | ENABLE_PROCESSED_INPUT));
    SetConsoleTitleW(L"HOI4 plugin debug console (local / single-player)");
    Write(L"HOI4 external console v1. /help for local actions; game commands use the native dispatcher.\r\n"); Prompt();
    std::thread logs(Logs, std::wstring(gamePath));
    CommandQueue commands([](const std::string& line) { if (line == "/__tab_completion__") CompleteWorker(); else ExecuteLine(line); });
    std::deque<std::wstring> history; size_t hist = 0; bool quit = false;
    while (!g_stop && !quit) {
        PumpCompletion();
        if (WaitForSingleObject(g_in, 100) != WAIT_OBJECT_0) continue;
        INPUT_RECORD rec; DWORD n; if (!ReadConsoleInputW(g_in, &rec, 1, &n)) break;
        if (rec.EventType == MOUSE_EVENT) { ScrollConsole(rec.Event.MouseEvent); continue; }
        if (rec.EventType != KEY_EVENT || !rec.Event.KeyEvent.bKeyDown) continue;
        auto k = rec.Event.KeyEvent;
        if (k.wVirtualKeyCode == VK_TAB) {
            bool submit = false;
            {
                std::lock_guard<std::mutex> lock(g_display);
                if (!g_completion.pending && Completion::Token(g_edit, g_cursor, g_completion.begin, g_completion.end, g_completion.prefix)) {
                    g_completion.pending = true; g_completion.edit = g_edit; g_completion.cursor = g_cursor; g_completion.revision = g_editRevision; submit = true;
                }
            }
            if (submit && !commands.Submit("/__tab_completion__")) { std::lock_guard<std::mutex> lock(g_display); g_completion.pending = false; }
            continue;
        }
        if (k.wVirtualKeyCode == VK_RETURN) {
            std::wstring line;
            { std::lock_guard<std::mutex> lock(g_display); line = g_edit; ErasePrompt(); Write(L"> " + line + L"\r\n"); g_edit.clear(); g_cursor = 0; ++g_editRevision; Prompt(); }
            if (line.empty()) continue;
            if (history.empty() || history.back() != line) { history.push_back(line); if (history.size() > 128) history.pop_front(); } hist = history.size();
            if (line == L"/quit") quit = true;
            else if (line == L"/help") Print(L"[CONSOLE] /filter all|game|error|plugin, /clear, /reconnect, /quit; Tab lists/completes command names; Up/Down history; Left/Right/Home/End/Delete edit. No OS shell.");
            else if (line == L"/reconnect") { if (!commands.Submit("/reconnect")) Print(L"[CONSOLE] Queue busy; reconnect not accepted."); }
            else if (line == L"/clear") {
                std::lock_guard<std::mutex> lock(g_display); CONSOLE_SCREEN_BUFFER_INFO info; GetConsoleScreenBufferInfo(g_out, &info); DWORD w; COORD zero = {0,0};
                FillConsoleOutputCharacterW(g_out, L' ', info.dwSize.X * info.dwSize.Y, zero, &w); SetConsoleCursorPosition(g_out, zero); Prompt();
            } else if (line.rfind(L"/filter ", 0) == 0) {
                std::wstring f = line.substr(8); int filter = f == L"all" ? 0 : f == L"game" ? 1 : f == L"error" ? 2 : f == L"plugin" ? 3 : -1;
                if (filter < 0) Print(L"[CONSOLE] Unknown filter."); else { g_filter = filter; Print(L"[CONSOLE] Filter=" + f); }
            } else if (line[0] == L'/') Print(L"[CONSOLE] Unknown local action; /help.");
            else {
                if (!commands.Submit(Utf8(line))) Print(L"[CONSOLE] Queue busy; command not accepted.");
                else Print(L"[CONSOLE] Request queued; input remains active.");
            }
            continue;
        }
        std::lock_guard<std::mutex> lock(g_display); ErasePrompt();
        ++g_editRevision;
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
    g_stop = true; commands.Stop(); logs.join(); SetConsoleMode(g_in, g_oldMode);
    if (g_pipe != INVALID_HANDLE_VALUE) CloseHandle(g_pipe);
    CloseHandle(g_mutex); CloseHandle(g_game); return 0;
}
