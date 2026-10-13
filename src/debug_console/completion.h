#pragma once
#include <string>
#include <vector>
#include <algorithm>
#include <cstddef>
#include <cstdint>

namespace Completion {
inline size_t RowSize() { return 5; }
inline unsigned short CandidateColor(size_t index) { return index % 2 == 0 ? 9 : 11; }
inline bool SnapshotMatches(uint64_t beforeRevision, uint64_t nowRevision, const std::wstring& beforeEdit, const std::wstring& nowEdit, size_t beforeCursor, size_t nowCursor) {
    return beforeRevision == nowRevision && beforeEdit == nowEdit && beforeCursor == nowCursor;
}
inline char Lower(char c) { return c >= 'A' && c <= 'Z' ? char(c + 'a' - 'A') : c; }
inline bool NameChar(char c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.' || c == '?' || c == '/'; }
inline bool Starts(const std::string& name, const std::string& prefix) {
    if (name.size() < prefix.size()) return false;
    for (size_t i = 0; i < prefix.size(); ++i) if (Lower(name[i]) != Lower(prefix[i])) return false;
    return true;
}
inline std::vector<std::string> Matching(std::vector<std::string> names, const std::string& prefix) {
    names.erase(std::remove_if(names.begin(), names.end(), [&](const std::string& name) {
        return name.empty() || name.size() > 128 || !std::all_of(name.begin(), name.end(), NameChar) || !Starts(name, prefix);
    }), names.end());
    std::sort(names.begin(), names.end());
    names.erase(std::unique(names.begin(), names.end()), names.end());
    return names;
}
inline std::string Common(const std::vector<std::string>& names) {
    if (names.empty()) return "";
    std::string common = names[0];
    for (const auto& name : names) {
        size_t n = 0; while (n < common.size() && n < name.size() && Lower(common[n]) == Lower(name[n])) ++n;
        common.resize(n);
    }
    return common;
}
inline bool Token(const std::wstring& edit, size_t cursor, size_t& begin, size_t& end, std::string& prefix) {
    begin = edit.find_first_not_of(L" \t"); if (begin == std::wstring::npos) begin = edit.size();
    end = edit.find_first_of(L" \t", begin); if (end == std::wstring::npos) end = edit.size();
    if (cursor < begin || cursor > end) return false;
    prefix.clear();
    for (size_t i = begin; i < cursor; ++i) { if (edit[i] > 127 || !NameChar((char)edit[i])) return false; prefix += Lower((char)edit[i]); }
    return prefix.size() <= 128;
}
}
