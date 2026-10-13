#pragma once
#include "variable64_name.h"

typedef enum {
    VAR64_NAME_BYTES_ONLY = 0,
    VAR64_NAME_WITH_TERMINATOR = 1
} Var64NameReadMode;

static int Var64_CopyTargetName(const unsigned char* field, char* out,
                               unsigned int outSize, Var64NameReadMode mode) {
    unsigned long long size = *(const unsigned long long*)(field + 16);
    unsigned long long capacity = *(const unsigned long long*)(field + 24);
    const unsigned char* source;
    unsigned long long i;
    if (size == 0 || size > VAR64_MAIN_NAME_LIMIT || size >= outSize) return 0;
    source = capacity <= 15 ? field : *(const unsigned char* const*)field;
    if (source == NULL || !ConsoleCmd_IsReadable(source, size + (mode == VAR64_NAME_WITH_TERMINATOR))) return 0;
    for (i = 0; i < size; ++i) out[i] = (char)source[i];
    out[size] = 0;
    return 1;
}
