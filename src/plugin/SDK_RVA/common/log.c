#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "log.h"

void Log_AppendV(const char* path, const char* format, va_list arguments) {
    char message[2048], line[2304];
    SYSTEMTIME time;
    HANDLE file;
    DWORD written = 0;
    int length;
    if (_vsnprintf_s(message, sizeof(message), _TRUNCATE, format, arguments) < 0) return;
    GetLocalTime(&time);
    file = CreateFileA(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
                      NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return;
    length = _snprintf_s(line, sizeof(line), _TRUNCATE, "[%02d:%02d:%02d.%03d] %s\r\n",
                         time.wHour, time.wMinute, time.wSecond, time.wMilliseconds, message);
    if (length > 0) WriteFile(file, line, (DWORD)length, &written, NULL);
    CloseHandle(file);
}
