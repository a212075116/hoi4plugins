#pragma once
#include <stddef.h>

typedef struct {
    const char* data;
    unsigned long long size;
} NativeNameView;

typedef char native_name_view_layout_check[
    (sizeof(void*) == 8 && sizeof(NativeNameView) == 16 &&
     offsetof(NativeNameView, data) == 0 && offsetof(NativeNameView, size) == 8) ? 1 : -1];
