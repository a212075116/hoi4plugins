#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include "native_memory.h"

int NativeMemory_IsReadable(const void* p, size_t n) {
    MEMORY_BASIC_INFORMATION mbi;
    uintptr_t end;
    DWORD readable;

    if (p == NULL) return 0;
    if (VirtualQuery(p, &mbi, sizeof(mbi)) == 0) return 0;
    if (mbi.State != MEM_COMMIT) return 0;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return 0;
    readable = PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY
             | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY;
    if ((mbi.Protect & readable) == 0) return 0;
    end = (uintptr_t)p + n;
    if (end < (uintptr_t)p) return 0;
    if (end > (uintptr_t)mbi.BaseAddress + mbi.RegionSize) return 0;
    return 1;
}

