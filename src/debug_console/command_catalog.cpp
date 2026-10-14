#include "command_catalog.h"
#include "completion.h"
#include <tlhelp32.h>
#include <cstring>
#include <utility>
#include <memory>

namespace {
struct KernelHandleCloser {
    void operator()(HANDLE handle) const noexcept {
        if (handle && handle != INVALID_HANDLE_VALUE) CloseHandle(handle);
    }
};
using OwnedHandle = std::unique_ptr<void, KernelHandleCloser>;
}

std::vector<std::string> CommandCatalog::Query(DWORD pid, const std::string& prefix, std::string& error) {
    if (!prefix.empty() && prefix[0] == '/') {
        return Completion::Matching({"/help", "/filter", "/clear", "/reconnect", "/quit"}, prefix);
    }
    OwnedHandle process(OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
    if (!process) { error = "Cannot read this game's command catalog."; return {}; }
    uintptr_t base = 0;
    {
        OwnedHandle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
        MODULEENTRY32W module = {}; module.dwSize = sizeof(module);
        if (snapshot.get() != INVALID_HANDLE_VALUE) {
            if (Module32FirstW(snapshot.get(), &module)) do { if (!_wcsicmp(module.szModule, L"hoi4.exe")) { base = (uintptr_t)module.modBaseAddr; break; } } while (Module32NextW(snapshot.get(), &module));
        }
    }
    auto read = [&](uintptr_t address, void* out, size_t size) {
        SIZE_T got = 0; return address && ReadProcessMemory(process.get(), (const void*)address, out, size, &got) && got == size;
    };
    IMAGE_DOS_HEADER dos = {}; IMAGE_NT_HEADERS64 nt = {};
    if (!read(base, &dos, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew <= 0 || dos.e_lfanew > 4096 ||
        !read(base + dos.e_lfanew, &nt, sizeof(nt)) || nt.Signature != IMAGE_NT_SIGNATURE || nt.FileHeader.TimeDateStamp != 0x6AA123BB || nt.OptionalHeader.SizeOfImage != 0x37EC000) {
        error = "Unsupported game version; command catalog not read."; return {};
    }
    struct Table { uintptr_t data; int capacity, count; };
    struct RemoteString { unsigned char data[16]; uint64_t size, capacity; };
    auto name = [&](const RemoteString& value, std::string& text) {
        if (!value.size || value.size > 128 || value.capacity < value.size) return false;
        if (value.capacity <= 15) text.assign((const char*)value.data, (size_t)value.size);
        else { uintptr_t pointer = 0; memcpy(&pointer, value.data, sizeof(pointer)); text.resize((size_t)value.size); if (!read(pointer, &text[0], text.size())) return false; }
        return std::all_of(text.begin(), text.end(), Completion::NameChar);
    };
    std::vector<std::string> names;
    bool stable = false;
    for (int attempt = 0; attempt < 3 && !stable; ++attempt) {
        uintptr_t manager = 0; Table before = {}, after = {}; names.clear();
        if (!read(base + 0x35E1A80, &manager, sizeof(manager)) || !read(manager, &before, sizeof(before)) || before.count <= 0 || before.count > 8192 || before.capacity < before.count || before.capacity > 100000) break;
        std::vector<unsigned char> entries((size_t)before.count * 456);
        if (!read(before.data, entries.data(), entries.size())) continue;
        bool valid = true;
        for (int i = 0; i < before.count && valid; ++i) {
            const unsigned char* entry = entries.data() + (size_t)i * 456;
            RemoteString value = {}; std::string text;
            memcpy(&value, entry + 8, sizeof(value));
            if (!name(value, text)) { valid = false; break; }
            names.push_back(text);
            int aliases = 0; memcpy(&aliases, entry + 40, sizeof(aliases));
            if (aliases < 0 || aliases > 3) { valid = false; break; }
            for (int j = 0; j < aliases; ++j) {
                uintptr_t pointer = 0; memcpy(&pointer, entry + 48 + j * 8, sizeof(pointer));
                text.clear(); bool terminated = false;
                for (int k = 0; k < 129; ++k) { char c = 0; if (!read(pointer + k, &c, 1)) break; if (!c) { terminated = true; break; } if (!Completion::NameChar(c)) break; text += c; }
                if (!terminated || text.empty()) { valid = false; break; }
                names.push_back(text);
            }
        }
        uintptr_t currentManager = 0;
        stable = valid && read(base + 0x35E1A80, &currentManager, sizeof(currentManager)) && currentManager == manager && read(manager, &after, sizeof(after)) && memcmp(&before, &after, sizeof(before)) == 0;
    }
    process.reset();
    if (!stable) { error = "Command catalog not ready or changed during snapshot; try Tab again."; return {}; }
    return Completion::Matching(std::move(names), prefix);
}
