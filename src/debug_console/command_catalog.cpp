#include "command_catalog.h"
#include "completion.h"
#include <tlhelp32.h>
#include <bcrypt.h>
#include <cstring>
#include <fstream>
#include <map>
#include <utility>
#include "owned_kernel_handle.h"

#pragma comment(lib, "bcrypt.lib")

namespace {
using ClientResource::OwnedHandle;

std::string FileSha256(const std::wstring& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return {};
    BCRYPT_ALG_HANDLE algorithm = nullptr; BCRYPT_HASH_HANDLE hash = nullptr; UCHAR digest[32] = {};
    bool ok = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0 &&
              BCryptCreateHash(algorithm, &hash, nullptr, 0, nullptr, 0, 0) >= 0;
    std::vector<char> buffer(1 << 20);
    while (ok && file) {
        file.read(buffer.data(), (std::streamsize)buffer.size());
        if (file.gcount() > 0) ok = BCryptHashData(hash, (PUCHAR)buffer.data(), (ULONG)file.gcount(), 0) >= 0;
    }
    ok = ok && BCryptFinishHash(hash, digest, sizeof(digest), 0) >= 0;
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
    if (!ok) return {};
    static const char hex[] = "0123456789abcdef";
    std::string text;
    for (UCHAR byte : digest) { text += hex[byte >> 4]; text += hex[byte & 15]; }
    return text;
}

DWORD ConsoleManagerRva(const std::wstring& exe, DWORD imageSize, std::string& error) {
    static std::map<std::wstring, std::pair<FILETIME, DWORD>> cache;
    WIN32_FILE_ATTRIBUTE_DATA info = {};
    if (!GetFileAttributesExW(exe.c_str(), GetFileExInfoStandard, &info)) { error = "Cannot read the game image."; return 0; }
    auto cached = cache.find(exe);
    if (cached != cache.end() && !CompareFileTime(&cached->second.first, &info.ftLastWriteTime)) return cached->second.second;
    std::string sha = FileSha256(exe);
    size_t slash = exe.find_last_of(L"\\/");
    std::wstring profile = exe.substr(0, slash == std::wstring::npos ? 0 : slash + 1) + L"hoi4plugins\\bindings\\" +
                           std::wstring(sha.begin(), sha.end()) + L".symbols";
    std::ifstream file(profile);
    std::map<std::string, std::string> fields;
    for (std::string line; std::getline(file, line);) {
        while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
        size_t equal = line.find('=');
        if (equal != std::string::npos) fields[line.substr(0, equal)] = line.substr(equal + 1);
    }
    DWORD rva = 0;
    try { rva = (DWORD)std::stoul(fields["console.manager"], nullptr, 0); } catch (...) { rva = 0; }
    if (sha.empty() || fields["image_sha256"] != sha || fields["approve.console"] != "1" || !rva || rva + sizeof(void*) > imageSize) {
        error = "Unsupported game version; no approved console binding for this image."; return 0;
    }
    cache[exe] = std::make_pair(info.ftLastWriteTime, rva);
    return rva;
}
}

std::vector<std::string> CommandCatalog::Query(DWORD pid, const std::string& prefix, std::string& error) {
    if (!prefix.empty() && prefix[0] == '/') {
        return Completion::Matching({"/help", "/filter", "/clear", "/reconnect", "/quit"}, prefix);
    }
    OwnedHandle process(OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
    if (!process) { error = "Cannot read this game's command catalog."; return {}; }
    uintptr_t base = 0; std::wstring exe;
    {
        OwnedHandle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
        MODULEENTRY32W module = {}; module.dwSize = sizeof(module);
        if (snapshot.get() != INVALID_HANDLE_VALUE) {
            if (Module32FirstW(snapshot.get(), &module)) do { if (!_wcsicmp(module.szModule, L"hoi4.exe")) { base = (uintptr_t)module.modBaseAddr; exe = module.szExePath; break; } } while (Module32NextW(snapshot.get(), &module));
        }
    }
    auto read = [&](uintptr_t address, void* out, size_t size) {
        SIZE_T got = 0; return address && ReadProcessMemory(process.get(), (const void*)address, out, size, &got) && got == size;
    };
    IMAGE_DOS_HEADER dos = {}; IMAGE_NT_HEADERS64 nt = {};
    if (!read(base, &dos, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew <= 0 || dos.e_lfanew > 4096 ||
        !read(base + dos.e_lfanew, &nt, sizeof(nt)) || nt.Signature != IMAGE_NT_SIGNATURE) {
        error = "Unsupported game version; command catalog not read."; return {};
    }
    DWORD managerRva = ConsoleManagerRva(exe, nt.OptionalHeader.SizeOfImage, error);
    if (!managerRva) return {};
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
        if (!read(base + managerRva, &manager, sizeof(manager)) || !read(manager, &before, sizeof(before)) || before.count <= 0 || before.count > 8192 || before.capacity < before.count || before.capacity > 100000) break;
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
        stable = valid && read(base + managerRva, &currentManager, sizeof(currentManager)) && currentManager == manager && read(manager, &after, sizeof(after)) && memcmp(&before, &after, sizeof(before)) == 0;
    }
    process.reset();
    if (!stable) { error = "Command catalog not ready or changed during snapshot; try Tab again."; return {}; }
    return Completion::Matching(std::move(names), prefix);
}
