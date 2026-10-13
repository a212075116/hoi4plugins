#pragma once
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif
int NativeMemory_IsReadable(const void* address, size_t bytes);
#ifdef __cplusplus
}
#endif
