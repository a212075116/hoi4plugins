#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "../../../src/plugin/adapter/native_adapter.h"
int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 2;
    HMODULE library=LoadLibraryW(argv[1]);if(!library)return 3;
    auto read=(int(*)(NativeCameraSnapshot*))GetProcAddress(library,"Hoi4Plugin_ReadCameraV1");if(!read)return 4;
    for(int i=0;i<500;++i) {
        NativeCameraSnapshot snapshot={sizeof(snapshot),1};int ok=read(&snapshot);
        if(strstr(snapshot.status,"PROFILE_") || strstr(snapshot.status,"IMAGE_")) {
            printf("unknown host camera=%d status=%s\n",ok,snapshot.status);Sleep(100);return ok?1:0;
        }
        Sleep(10);
    }
    return 5;
}
