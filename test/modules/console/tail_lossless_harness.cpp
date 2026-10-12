#define wmain DebugConsoleOriginalMain
#include "../../../src/debug_console/main.cpp"
#undef wmain
int main() {
    wchar_t dir[MAX_PATH], path[MAX_PATH]; GetTempPathW(MAX_PATH, dir); GetTempFileNameW(dir, L"dcq", 0, path);
    HANDLE h = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, CREATE_ALWAYS, 0, NULL);
    std::string expected;
    for (int i = 0; i < 90000; ++i) { char row[64]; sprintf_s(row, "SEQ:%08d payload\n", i); expected += row; }
    DWORD n; WriteFile(h, expected.data(), (DWORD)expected.size(), &n, NULL); CloseHandle(h);
    Tail tail{path}; std::string actual; size_t lines = 0;
    for (int k = 0; k < 10000; ++k) {
        auto rows = tail.Poll();
        for (const auto& row : rows) { actual += row; actual += '\n'; ++lines; }
        if (tail.offset >= expected.size()) break;
    }
    bool good = actual == expected;
    printf("expected_lines=90000 observed_lines=%zu exact=%u\n", lines, good);
    DeleteFileW(path); return good ? 0 : 1;
}
