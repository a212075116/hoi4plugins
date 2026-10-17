#pragma once
#include <stddef.h>

#define NATIVE_STRING_SSO_MAX 15u

#pragma pack(push, 8)
typedef struct {
    union { char buf[16]; char* ptr; } u;
    size_t size;
    size_t cap;
} NativeString;
#pragma pack(pop)

typedef char native_string_layout_check[
    (sizeof(void*) == 8 && sizeof(NativeString) == 32 &&
     offsetof(NativeString, size) == 16 && offsetof(NativeString, cap) == 24) ? 1 : -1];

typedef void** (__fastcall *NativeStringAssignFn)(void** destination, const void* data, size_t bytes);

static inline const char* NativeString_Data(const NativeString* value) {
    return value->cap <= NATIVE_STRING_SSO_MAX ? value->u.buf : value->u.ptr;
}
