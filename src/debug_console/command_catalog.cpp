#include "command_catalog.h"
#include "completion.h"
#include <tlhelp32.h>
#include <bcrypt.h>
#include <cstring>
#include <fstream>
#include <map>
#include <set>
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
    ok = ok && file.eof() && !file.bad() && BCryptFinishHash(hash, digest, sizeof(digest), 0) >= 0;
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
    if (!ok) return {};
    static const char hex[] = "0123456789abcdef";
    std::string text;
    for (UCHAR byte : digest) { text += hex[byte >> 4]; text += hex[byte & 15]; }
    return text;
}

std::string ProfileTrim(const std::string& text) {
    size_t first = text.find_first_not_of(" \t\r\n");
    return first == std::string::npos ? std::string() : text.substr(first, text.find_last_not_of(" \t\r\n") - first + 1);
}

std::set<std::string> ProfileKeys() {
    std::set<std::string> keys = {"schema", "image_sha256", "contract"};
#define NATIVE_GROUP(id,name,registry,first,second) keys.insert(std::string("approve.") + name);
#define NATIVE_CODE(id,group,key) keys.insert(key);
#define NATIVE_DATA(id,group,key,bytes) keys.insert(key);
#define NATIVE_SLOT(id,group,key,type,offset,slot)
#define NATIVE_TABLE(id,group,key,type,offset,slots)
#define NATIVE_FIELD(id,group,key) keys.insert(std::string("field.") + key);
#include "../plugin/adapter/symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
#undef NATIVE_FIELD
    return keys;
}

bool ProfileNumber(const std::string& text, DWORD& value) {
    unsigned radix = 10; size_t start = 0;
    if (text.size() > 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) { radix = 16; start = 2; }
    if (text.empty()) return false;
    value = 0;
    for (size_t i = start; i < text.size(); ++i) {
        char c = text[i];
        unsigned digit = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : 16;
        if (digit >= radix || value > (MAXDWORD - digit) / radix) return false;
        value = value * radix + digit;
    }
    return true;
}

DWORD ProfileManagerRva(const std::string& bytes, const std::string& sha, DWORD imageSize, std::string& error) {
    auto reject = [&](const char* reason) { error = std::string("Console binding: ") + reason; return DWORD(0); };
    if (bytes.empty() || bytes.size() > 32768 || std::any_of(bytes.begin(), bytes.end(), [](unsigned char c) {
        return c > 126 || (c < 32 && c != '\t' && c != '\r' && c != '\n');
    })) return reject("PROFILE_SIZE_OR_ENCODING");
    std::map<std::string, std::string> fields;
    for (size_t start = 0; start < bytes.size();) {
        size_t end = bytes.find('\n', start);
        if (end == std::string::npos) end = bytes.size();
        std::string line = ProfileTrim(bytes.substr(start, end - start)); start = end + 1;
        if (line.empty()) continue;
        size_t equal = line.find('=');
        if (equal == std::string::npos) return reject("PROFILE_SYNTAX");
        std::string key = ProfileTrim(line.substr(0, equal)), value = ProfileTrim(line.substr(equal + 1));
        if (key.empty() || value.empty() || !fields.emplace(key, value).second) return reject("PROFILE_DUPLICATE_OR_EMPTY");
    }
    static const auto expected = ProfileKeys();
    if (fields.size() != expected.size()) return reject("PROFILE_KEY_SET");
    for (const auto& key : expected) if (!fields.count(key)) return reject("PROFILE_KEY_SET");
    if (sha.size() != 64 || fields["schema"] != "1" || fields["contract"] != "symbols_v2" || fields["image_sha256"] != sha)
        return reject("PROFILE_IDENTITY_OR_SCHEMA");
    for (const auto& field : fields) if (field.first.compare(0, 8, "approve.") == 0 && field.second != "0" && field.second != "1")
        return reject("PROFILE_APPROVAL_VALUE");
    if (fields["approve.core"] != "1" || fields["approve.console"] != "1") return reject("CONSOLE_NOT_APPROVED");
    DWORD rva = 0;
    if (!ProfileNumber(fields["console.manager"], rva) || !rva || imageSize < sizeof(void*) || rva > imageSize - sizeof(void*))
        return reject("CONSOLE_RVA_INVALID");
    return rva;
}

bool ImageStamp(const std::wstring& path, BY_HANDLE_FILE_INFORMATION& info) {
    OwnedHandle file(CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                                 nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr));
    return file.get() != INVALID_HANDLE_VALUE && file && GetFileType(file.get()) == FILE_TYPE_DISK &&
           GetFileInformationByHandle(file.get(), &info) && !(info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY);
}

bool SameStamp(const BY_HANDLE_FILE_INFORMATION& a, const BY_HANDLE_FILE_INFORMATION& b) {
    return a.dwVolumeSerialNumber == b.dwVolumeSerialNumber && a.nFileIndexHigh == b.nFileIndexHigh && a.nFileIndexLow == b.nFileIndexLow &&
           a.nFileSizeHigh == b.nFileSizeHigh && a.nFileSizeLow == b.nFileSizeLow &&
           !CompareFileTime(&a.ftCreationTime, &b.ftCreationTime) && !CompareFileTime(&a.ftLastWriteTime, &b.ftLastWriteTime);
}

DWORD ConsoleManagerRva(const std::wstring& exe, DWORD imageSize, std::string& error) {
    static std::wstring cachedPath;
    static BY_HANDLE_FILE_INFORMATION cachedInfo = {};
    static std::string cachedSha;
    BY_HANDLE_FILE_INFORMATION info = {}, after = {};
    if (!ImageStamp(exe, info)) { error = "Cannot read the game image identity."; return 0; }
    if (exe != cachedPath || cachedSha.empty() || !SameStamp(info, cachedInfo)) {
        std::string sha = FileSha256(exe);
        if (sha.empty() || !ImageStamp(exe, after) || !SameStamp(info, after)) { error = "Game image unreadable or changed while hashing."; return 0; }
        cachedPath = exe; cachedInfo = after; cachedSha = sha;
    }
    size_t slash = exe.find_last_of(L"\\/");
    std::wstring profile = exe.substr(0, slash == std::wstring::npos ? 0 : slash + 1) + L"hoi4plugins\\bindings\\" +
                           std::wstring(cachedSha.begin(), cachedSha.end()) + L".symbols";
    std::ifstream file(profile, std::ios::binary);
    if (!file) { error = "Console binding: PROFILE_UNREADABLE"; return 0; }
    std::string bytes(32769, '\0');
    file.read(&bytes[0], (std::streamsize)bytes.size()); bytes.resize((size_t)file.gcount());
    if (file.bad()) { error = "Console binding: PROFILE_READ_FAILED"; return 0; }
    return ProfileManagerRva(bytes, cachedSha, imageSize, error);
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
