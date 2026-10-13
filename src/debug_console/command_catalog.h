#pragma once
#include <windows.h>
#include <string>
#include <vector>

namespace CommandCatalog {
std::vector<std::string> Query(DWORD pid, const std::string& prefix, std::string& error);
}
