#pragma once
#include <string.h>

#define VAR64_HIGH_SUFFIX "_var64h"
#define VAR64_FRAC_SUFFIX "_var64f"
#define VAR64_NAME_LIMIT 40u
#define VAR64_MAIN_NAME_LIMIT (VAR64_NAME_LIMIT - sizeof(VAR64_HIGH_SUFFIX) + 1u)

static int Var64_MakePartName(const char* name, const char* suffix, size_t suffixBytes,
                            char* out, unsigned int outSize) {
    size_t length;
    if (name == NULL || out == NULL) return 0;
    length = strlen(name);
    if (length == 0 || length + suffixBytes > outSize) return 0;
    if (length + suffixBytes - 1 > VAR64_NAME_LIMIT) return 0;
    memcpy(out, name, length);
    memcpy(out + length, suffix, suffixBytes);
    return 1;
}

static int Var64_MakeHighPartName(const char* name, char* out, unsigned int outSize) {
    return Var64_MakePartName(name, VAR64_HIGH_SUFFIX, sizeof(VAR64_HIGH_SUFFIX), out, outSize);
}

static int Var64_MakeFracPartName(const char* name, char* out, unsigned int outSize) {
    return Var64_MakePartName(name, VAR64_FRAC_SUFFIX, sizeof(VAR64_FRAC_SUFFIX), out, outSize);
}
