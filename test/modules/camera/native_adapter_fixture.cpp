#include "../../../src/plugin/adapter/native_adapter.cpp"
static const char kLegacySha[]="7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5";

static BYTE* objectPool;
static int checks,failed;
static void Check(const char* name,bool ok) {++checks;if(!ok){++failed;printf("FAIL %s\n",name);}}
static void Put32(DWORD rva,DWORD n) {memcpy(g_file.data()+rva,&n,4);}
static void Put64(DWORD rva,ULONGLONG n) {memcpy(g_file.data()+rva,&n,8);}
static void RuntimePtr(DWORD rva,uintptr_t n) {memcpy(g_base+rva,&n,8);}
static void ObjectPtr(size_t at,uintptr_t n) {memcpy(objectPool+at,&n,8);}
static void Synthetic() {
    if(g_base)VirtualFree(g_base,0,MEM_RELEASE);
    if(objectPool)VirtualFree(objectPool,0,MEM_RELEASE);
    g_base=(BYTE*)VirtualAlloc(nullptr,0x5000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    objectPool=(BYTE*)VirtualAlloc(nullptr,0x3000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    g_imageSize=0x5000;g_preferred=0x140000000ULL;g_file.assign(0x4000,0);
    g_sections={{0x1000,0x1000,0x1000,IMAGE_SCN_MEM_READ|IMAGE_SCN_MEM_EXECUTE,0x1000},{0x2000,0x1000,0x1000,IMAGE_SCN_MEM_READ,0x2000},{0x3000,0x1000,0x1000,IMAGE_SCN_MEM_READ|IMAGE_SCN_MEM_WRITE,0x3000}};
    strcpy_s((char*)g_file.data()+0x3010,128,".?AVCInGameIdler@@");strcpy_s((char*)g_file.data()+0x3110,128,".?AVCFrontEndIdler@@");
    for(int i=0;i<2;++i) {DWORD at=0x2200+i*0x20;DWORD col[]={1,0,0,(DWORD)(0x3000+i*0x100),0x2f00,at};memcpy(g_file.data()+at,col,24);}
    Put64(0x23f8,g_preferred+0x2200);Put64(0x25f8,g_preferred+0x2220);
    for(int i=0;i<39;++i)Put64(0x2400+i*8,g_preferred+0x1000);
    for(int i=0;i<4;++i)Put64(0x2600+i*8,g_preferred+0x1000);
    const BYTE code[]={0x48,0x8b,0x81,0x50,7,0,0,0xc3};memcpy(g_file.data()+0x1120,code,8);
    Put64(0x2400+37*8,g_preferred+0x1120);Put64(0x2400+38*8,g_preferred+0x1120);
    g_profile={0x750,0x69c,0x6d0,0x6d4,true};g_binding={};g_roots.clear();g_groupReady[NG_CAMERA_WRITE]=true;
    InterlockedExchange(&g_prepared,1);
    Check("synthetic-bind",Bind(g_preferred));g_bound=true;
    memcpy(g_base,g_file.data(),g_file.size());
    RuntimePtr(0x23f8,(uintptr_t)(g_base+0x2200));RuntimePtr(0x25f8,(uintptr_t)(g_base+0x2220));
    for(int i=0;i<39;++i)RuntimePtr(0x2400+i*8,(uintptr_t)(g_base+(i==37||i==38?0x1120:0x1000)));
    RuntimePtr(0x3200,(uintptr_t)objectPool);RuntimePtr(0x3208,(uintptr_t)objectPool);
    ObjectPtr(0,(uintptr_t)(g_base+0x2400));ObjectPtr(0x750,(uintptr_t)(objectPool+0x1000));
    float h=310;int lo=50,hi=3000;memcpy(objectPool+0x169c,&h,4);memcpy(objectPool+0x16d0,&lo,4);memcpy(objectPool+0x16d4,&hi,4);
}
static void Expect(const char* name,const char* code,bool full=true) {
    NativeCameraSnapshot s={sizeof(s),1};bool ok=Capture(s,full);
    Check(name,!strcmp(s.status,code) && ok==!strcmp(code,"READY_READ_ONLY"));
}
static std::string ProfileText() {
    return std::string("schema=1\nimage_sha256=")+kLegacySha+"\nread_contract=leaf_rtti_v1\ncamera_pointer=0x750\nheight=0x69c\nminimum=0x6d0\nmaximum=0x6d4\nruntime_read=1\n";
}
static bool Parse(const std::string& text) {Profile p;return ParseProfile(std::vector<BYTE>(text.begin(),text.end()),kLegacySha,p);}
int wmain(int argc,wchar_t** argv) {
    if(argc==3 && !wcscmp(argv[1],L"--offline")) {
        g_profile.camera=0x750;
        if(!LoadImage(argv[2],false)||!Bind(g_preferred)) {printf("%s\n",g_reason.c_str());return 1;}
        printf("sha=%s ingame=0x%X frontend=0x%X getter=0x%X slot=%u\n",g_sha.c_str(),g_binding.ingame,g_binding.frontend,g_binding.getter,g_binding.slot);return 0;
    }
    std::string valid=ProfileText();Check("valid-profile",Parse(valid));
    for(const char* extra:{"schema=1\n","unknown=1\n","height=1\n"})Check("duplicate-or-extra",!Parse(valid+extra));
    for(const char* key:{"camera_pointer","height","minimum","maximum"})for(const char* value:{"-1","+4","0x100000000","0x10001","junk","0x751"}) {
        std::string text=valid,needle=std::string(key)+"=";size_t at=text.find(needle),end=text.find('\n',at);text.replace(at,end-at,needle+value);Check("invalid-number",!Parse(text));
    }
    for(auto pair:{std::make_pair("schema=1","schema=2"),std::make_pair("runtime_read=1","runtime_read=2"),std::make_pair("leaf_rtti_v1","unknown_contract"),std::make_pair("height=0x69c","height=0x6d0")}) {
        std::string text=valid;size_t at=text.find(pair.first);text.replace(at,strlen(pair.first),pair.second);Check("invalid-contract",!Parse(text));
    }
    Check("oversize-profile",!Parse(std::string(4097,'x')));Check("embedded-nul",!Parse(valid+std::string(1,'\0')));
    Profile bad;std::vector<BYTE> bytes(valid.begin(),valid.end());Check("wrong-sha",!ParseProfile(bytes,std::string(64,'0'),bad));
    std::string disabled=valid;disabled.replace(disabled.find("runtime_read=1"),14,"runtime_read=0");Check("disabled-profile-parses",Parse(disabled));
    Synthetic();Expect("read-ready","READY_READ_ONLY");Check("getter-alias",g_binding.slot==37);Check("duplicate-roots",g_roots.size()==2);
    Synthetic();ObjectPtr(0,(uintptr_t)(g_base+0x2600));DWORD old;VirtualProtect(objectPool+0x1000,0x1000,PAGE_NOACCESS,&old);Expect("frontend-with-guarded-camera","NOT_IN_MAP");
    Synthetic();RuntimePtr(0x3200,0);RuntimePtr(0x3208,0);Expect("missing-object","OBJECT_MISSING");
    Synthetic();RuntimePtr(0x3208,(uintptr_t)(objectPool+0x2000));ObjectPtr(0x2000,(uintptr_t)(g_base+0x2400));Expect("ambiguous-objects","OBJECT_AMBIGUOUS");
    Synthetic();ObjectPtr(0x750,0);Expect("null-camera","CAMERA_MISSING");
    Synthetic();VirtualProtect(objectPool+0x1000,0x1000,PAGE_NOACCESS,&old);Expect("camera-unreadable","READ_FAILED");
    for(float value:{NAN,INFINITY,-1.0f,3001.0f}) {Synthetic();memcpy(objectPool+0x169c,&value,4);Expect("invalid-height","INVALID_VALUES");}
    Synthetic();float invalid=NAN;memcpy(objectPool+0x169c,&invalid,4);Check("legacy-recovery-keeps-validated-object",NativeAdapter_CameraObject()==objectPool+0x1000);
    for(auto range:{std::make_pair(50,50),std::make_pair(3000,50),std::make_pair(-1,3000),std::make_pair(50,1000001)}) {Synthetic();memcpy(objectPool+0x16d0,&range.first,4);memcpy(objectPool+0x16d4,&range.second,4);Expect("invalid-range","INVALID_VALUES");}
    Synthetic();RuntimePtr(0x2400+37*8,0);Expect("changed-vslot","GETTER_CHANGED");
    Synthetic();g_base[0x1120]=0x90;Expect("changed-getter-code","GETTER_CHANGED");
    Synthetic();RuntimePtr(0x23f8,0);Expect("changed-col-prefix","TYPE_LAYOUT_CHANGED");
    Synthetic();g_base[0x2200]=2;Expect("changed-col-body","TYPE_LAYOUT_CHANGED");
    Synthetic();Check("cache-seed",ScanRoots());ObjectPtr(0,0);Expect("cached-type-change","TYPE_CHANGED",false);
    Synthetic();Check("cache-seed",ScanRoots());RuntimePtr(0x3208,0);Expect("cached-root-change","STATE_CHANGED",false);
    Synthetic();g_file[0x3010]='!';DWORD table=0;Check("missing-type",!FindTable("CInGameIdler",g_preferred,table)&&g_reason=="TABLE_MISSING");
    Synthetic();DWORD col[]={1,0,0,0x3000,0x2f00,0x2240};memcpy(g_file.data()+0x2240,col,24);Put64(0x27f8,g_preferred+0x2240);for(int i=0;i<4;++i)Put64(0x2800+i*8,g_preferred+0x1000);Check("duplicate-primary",!FindTable("CInGameIdler",g_preferred,table)&&g_reason=="TABLE_AMBIGUOUS");
    Synthetic();g_file[0x1127]=0x90;Check("nonleaf-getter",!Bind(g_preferred)&&g_reason=="GETTER_MISSING");
    Synthetic();memcpy(g_file.data()+0x1140,g_file.data()+0x1120,8);Put64(0x2400+38*8,g_preferred+0x1140);Check("distinct-getters",!Bind(g_preferred)&&g_reason=="GETTER_AMBIGUOUS");
    Synthetic();g_bound=false;g_reason="PROFILE_INVALID";Expect("binding-not-ready","PROFILE_INVALID");
    Synthetic();g_groupReady[NG_CAMERA_WRITE]=false;Check("unapproved-camera-write-blocked",!NativeAdapter_CameraWriteAllowed());g_groupReady[NG_CAMERA_WRITE]=true;g_profile.height+=4;Check("changed-layout-write-blocked",!NativeAdapter_CameraWriteAllowed());
    Synthetic();g_groupReady[NG_CAMERA_WRITE]=false;NativeCameraSnapshot approved={sizeof(approved),1};Check("approved-read-independent-of-write-group",Hoi4Plugin_ReadCameraV1(&approved)&&!NativeAdapter_CameraObject());
    InterlockedExchange(&g_prepared,0);Check("initialization-publication",!Hoi4Plugin_ReadCameraV1(&approved)&&!strcmp(approved.status,"INITIALIZING"));InterlockedExchange(&g_prepared,1);
    NativeCameraSnapshot badOut={0,1};Check("abi-size-refused",!Hoi4Plugin_ReadCameraV1(&badOut));
    wchar_t temp[MAX_PATH],file[MAX_PATH];GetTempPathW(MAX_PATH,temp);GetTempFileNameW(temp,L"h4s",0,file);g_log=file;g_status.clear();
    NativeAdapter_Report("test.cap",0,"PENDING");NativeAdapter_Report("test.cap",0,"PENDING");NativeAdapter_Report("test.cap",1,"READY");NativeAdapter_Report("test.cap",0,"FAILED");
    std::vector<BYTE> log;Check("status-file",ReadFileBytes(g_log,log,4096));Check("status-dedup",std::count(log.begin(),log.end(),'\n')==3);DeleteFileW(file);
    VirtualFree(g_base,0,MEM_RELEASE);VirtualFree(objectPool,0,MEM_RELEASE);g_base=nullptr;objectPool=nullptr;
    printf("native checks=%d failed=%d\n",checks,failed);return failed?1:0;
}
