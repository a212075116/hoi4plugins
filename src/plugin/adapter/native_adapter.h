#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct NativeCameraSnapshot {
    unsigned int size;
    unsigned int version;
    float height;
    int minimum;
    int maximum;
    void* object;
    char status[64];
} NativeCameraSnapshot;

int NativeAdapter_Initialize(void);
int NativeAdapter_LegacyAllowed(void);
int NativeAdapter_CameraWriteAllowed(void);
const char* NativeAdapter_Diagnostic(void);
void NativeAdapter_Report(const char* capability, int available, const char* reason);
void NativeAdapter_StartMonitor(void);
void NativeAdapter_OpenLogConsole(void);
void NativeAdapter_CameraRegistered(int commands, int effects);
void* NativeAdapter_CameraObject(void);
#ifdef NATIVE_ADAPTER_IMPLEMENTATION
__declspec(dllexport)
#endif
int Hoi4Plugin_ReadCameraV1(NativeCameraSnapshot* out);

#ifdef __cplusplus
}
#endif
