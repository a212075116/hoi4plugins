#pragma once
#include <stdarg.h>


#ifdef __cplusplus
extern "C" {
#endif
void Log_AppendV(const char* path, const char* format, va_list arguments);

#ifdef __cplusplus
}
#endif
