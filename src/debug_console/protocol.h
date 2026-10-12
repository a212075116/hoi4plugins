#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define DC_MAGIC 0x31434448u
#define DC_PROTOCOL_VERSION 1u
#define DC_INPUT_MAX 2048u
#define DC_OUTPUT_MAX 8192u
#define DC_QUEUE_MAX 32u
#define DC_PEERS 4u
enum { DC_EXECUTED = 0, DC_REJECTED = 1, DC_CANCELLED = 2, DC_FAULT = 3 };
typedef struct { uint32_t magic, version, id, length; } DcRequest;
typedef struct { uint32_t magic, version, id, length, status, ok, thread; } DcResponse;
static void DcPipeName(wchar_t* out, size_t count, DWORD pid) {
    _snwprintf_s(out, count, _TRUNCATE, L"\\\\.\\pipe\\hoi4-plugin-debug-v1-%lu", pid);
}
static int DcTransfer(HANDLE h, void* data, DWORD count, int writing, DWORD timeout) {
    unsigned char* p = (unsigned char*)data;
    ULONGLONG end = GetTickCount64() + timeout;
    while (count) {
        OVERLAPPED ov = {0}; DWORD n = 0, err; BOOL ok;
        ULONGLONG now = GetTickCount64();
        if (now >= end) return 0;
        ov.hEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
        if (!ov.hEvent) return 0;
        ok = writing ? WriteFile(h, p, count, &n, &ov) : ReadFile(h, p, count, &n, &ov);
        err = ok ? ERROR_SUCCESS : GetLastError();
        if (!ok && err == ERROR_IO_PENDING) {
            if (WaitForSingleObject(ov.hEvent, (DWORD)(end - now)) != WAIT_OBJECT_0) {
                CancelIoEx(h, &ov);
                GetOverlappedResult(h, &ov, &n, TRUE);
                CloseHandle(ov.hEvent); return 0;
            }
            ok = GetOverlappedResult(h, &ov, &n, FALSE);
        }
        CloseHandle(ov.hEvent);
        if (!ok || !n) return 0;
        p += n; count -= n;
    }
    return 1;
}
