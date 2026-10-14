#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <shellapi.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <math.h>
#include <algorithm>
#include <map>
#include <set>
#include <string>
#include <vector>
#define NATIVE_ADAPTER_IMPLEMENTATION
#include "native_adapter.h"

namespace {
const char kLegacySha[] = "7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5";
struct Section { DWORD rva, bytes, mapped, flags, raw; };
struct Profile { unsigned camera=0, height=0, minimum=0, maximum=0; bool read=false; };
struct Binding { DWORD ingame=0, frontend=0, getter=0; unsigned slot=0; BYTE code[8]={}; };
struct Status { int available; std::string reason; };
BYTE* g_base;
DWORD g_imageSize;
ULONGLONG g_preferred;
std::vector<BYTE> g_file;
std::vector<Section> g_sections;
std::wstring g_root, g_log;
std::string g_sha, g_reason="NOT_INITIALIZED";
Profile g_profile;
Binding g_binding;
bool g_legacy=false, g_bound=false;
SRWLOCK g_cameraLock=SRWLOCK_INIT, g_logLock=SRWLOCK_INIT;
std::vector<DWORD> g_roots;
std::map<std::string,Status> g_status;
volatile LONG g_commands=0, g_effects=0, g_monitor=0;
volatile LONG g_prepared=0;
struct PublishInitialization { ~PublishInitialization() {InterlockedExchange(&g_prepared,1);} };

bool Read(const void* p, void* out, size_t bytes) {
    uintptr_t address=(uintptr_t)p, end=address+bytes;
    if (!p || !bytes || end<address) return false;
    for (uintptr_t at=address;at<end;) {
        MEMORY_BASIC_INFORMATION m;
        if (!VirtualQuery((void*)at,&m,sizeof(m)) || m.State!=MEM_COMMIT ||
            (m.Protect&(PAGE_NOACCESS|PAGE_GUARD)) || !(m.Protect&(PAGE_READONLY|PAGE_READWRITE|PAGE_WRITECOPY|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY))) return false;
        uintptr_t next=(uintptr_t)m.BaseAddress+m.RegionSize;
        if (next<=at) return false;
        at=next;
    }
    __try { memcpy(out,p,bytes); return true; }
    __except(EXCEPTION_EXECUTE_HANDLER) { return false; }
}
bool Ptr(const void* p, uintptr_t& value) { return Read(p,&value,sizeof(value)); }
bool Range(size_t offset,size_t bytes) { return offset<=g_file.size() && bytes<=g_file.size()-offset; }
const BYTE* FileAt(DWORD rva,size_t bytes) {
    for (const auto& s:g_sections) if (rva>=s.rva && rva-s.rva<=s.bytes && bytes<=s.bytes-(rva-s.rva) && Range((size_t)s.raw+rva-s.rva,bytes)) return g_file.data()+s.raw+rva-s.rva;
    return nullptr;
}
bool Execute(DWORD rva) {
    for (const auto& s:g_sections) if (rva>=s.rva && rva-s.rva<s.mapped) return (s.flags&IMAGE_SCN_MEM_EXECUTE)!=0;
    return false;
}
bool Writable(DWORD rva) {
    for (const auto& s:g_sections) if (rva>=s.rva && rva-s.rva<s.mapped) return (s.flags&IMAGE_SCN_MEM_WRITE)!=0;
    return false;
}
bool ReadFileBytes(const std::wstring& path,std::vector<BYTE>& out,size_t limit) {
    HANDLE h=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if (h==INVALID_HANDLE_VALUE) return false;
    LARGE_INTEGER size; bool ok=GetFileSizeEx(h,&size)!=0 && size.QuadPart>0 && (unsigned long long)size.QuadPart<=limit;
    if (ok) {
        out.resize((size_t)size.QuadPart); size_t at=0;
        while (at<out.size()) {
            DWORD got=0, part=(DWORD)(std::min)(out.size()-at,(size_t)0x1000000);
            if (!ReadFile(h,out.data()+at,part,&got,nullptr)||got!=part) {ok=false;break;}
            at+=got;
        }
    }
    CloseHandle(h); return ok;
}
bool Hash(const std::vector<BYTE>& data,std::string& result) {
    BCRYPT_ALG_HANDLE alg=nullptr; BCRYPT_HASH_HANDLE hash=nullptr; BYTE digest[32];
    bool ok=BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0;
    if (ok) ok=BCryptCreateHash(alg,&hash,nullptr,0,nullptr,0,0)>=0;
    if (ok) ok=BCryptHashData(hash,(PUCHAR)data.data(),(ULONG)data.size(),0)>=0;
    if (ok) ok=BCryptFinishHash(hash,digest,sizeof(digest),0)>=0;
    if (hash) BCryptDestroyHash(hash);
    if (alg) BCryptCloseAlgorithmProvider(alg,0);
    if (ok) {char hex[65]; for (int i=0;i<32;++i) sprintf_s(hex+i*2,3,"%02x",digest[i]);result=hex;}
    return ok;
}
bool LoadImage(const std::wstring& path,bool verifyLoaded=true) {
    if (!ReadFileBytes(path,g_file,512u*1024u*1024u) || !Hash(g_file,g_sha)) {g_reason="IMAGE_READ_OR_HASH_FAILED";return false;}
    if (!Range(0,sizeof(IMAGE_DOS_HEADER))) return false;
    const auto* dos=(const IMAGE_DOS_HEADER*)g_file.data();
    if (dos->e_magic!=IMAGE_DOS_SIGNATURE || dos->e_lfanew<0 || !Range(dos->e_lfanew,sizeof(IMAGE_NT_HEADERS64))) return false;
    const auto* nt=(const IMAGE_NT_HEADERS64*)(g_file.data()+dos->e_lfanew);
    if (nt->Signature!=IMAGE_NT_SIGNATURE || nt->FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64 || nt->OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC ||
        nt->FileHeader.NumberOfSections>96 || nt->FileHeader.SizeOfOptionalHeader<sizeof(IMAGE_OPTIONAL_HEADER64) || nt->OptionalHeader.SizeOfImage>1024u*1024u*1024u) return false;
    size_t first=(size_t)dos->e_lfanew+offsetof(IMAGE_NT_HEADERS64,OptionalHeader)+nt->FileHeader.SizeOfOptionalHeader;
    if (!Range(first,(size_t)nt->FileHeader.NumberOfSections*sizeof(IMAGE_SECTION_HEADER))) return false;
    g_imageSize=nt->OptionalHeader.SizeOfImage;
    g_preferred=nt->OptionalHeader.ImageBase;
    for (unsigned i=0;i<nt->FileHeader.NumberOfSections;++i) {
        const auto* s=(const IMAGE_SECTION_HEADER*)(g_file.data()+first+i*sizeof(IMAGE_SECTION_HEADER));
        DWORD mapped=(std::max)(s->Misc.VirtualSize,s->SizeOfRawData);
        if (s->VirtualAddress>g_imageSize || mapped>g_imageSize-s->VirtualAddress || !Range(s->PointerToRawData,s->SizeOfRawData)) return false;
        g_sections.push_back({s->VirtualAddress,s->SizeOfRawData,mapped,s->Characteristics,s->PointerToRawData});
    }
    if (!verifyLoaded) return true;
    DWORD headerBytes=nt->OptionalHeader.SizeOfHeaders;
    if (!headerBytes || headerBytes>1024*1024 || !Range(0,headerBytes)) return false;
    std::vector<BYTE> loaded(headerBytes),expected(g_file.begin(),g_file.begin()+headerBytes);
    if (!Read(g_base,loaded.data(),loaded.size())) return false;
    size_t baseField=(size_t)dos->e_lfanew+offsetof(IMAGE_NT_HEADERS64,OptionalHeader)+offsetof(IMAGE_OPTIONAL_HEADER64,ImageBase);
    if (baseField+8>expected.size()) return false;
    ULONGLONG actual=0;memcpy(&actual,loaded.data()+baseField,8);
    if (actual==(ULONGLONG)g_base) memcpy(expected.data()+baseField,&actual,8);
    if (loaded!=expected) {g_reason="LOADED_IMAGE_MISMATCH";return false;}
    return true;
}
std::string Trim(std::string s) {
    size_t first=s.find_first_not_of(" \t\r"),last=s.find_last_not_of(" \t\r");
    return first==std::string::npos?"":s.substr(first,last-first+1);
}
bool Number(const std::string& text,unsigned& n) {
    if (text.empty() || text[0]=='-' || text[0]=='+') return false;
    char* end=nullptr;errno=0;unsigned long value=strtoul(text.c_str(),&end,0);
    if (errno || !end || *end || value>0x10000) return false;
    n=(unsigned)value;return true;
}
bool ParseProfile(const std::vector<BYTE>& bytes,const std::string& sha,Profile& p) {
    if (bytes.empty() || bytes.size()>4096 || std::any_of(bytes.begin(),bytes.end(),[](BYTE c){return c==0 || c>127;})) return false;
    std::map<std::string,std::string> values;size_t start=0;
    while (start<bytes.size()) {
        size_t end=start;while(end<bytes.size() && bytes[end]!='\n')++end;
        std::string line=Trim(std::string((const char*)bytes.data()+start,end-start));start=end+1;
        if (line.empty()) continue;
        size_t equal=line.find('=');if(equal==std::string::npos) return false;
        std::string key=Trim(line.substr(0,equal)),value=Trim(line.substr(equal+1));
        if (key.empty() || value.empty() || !values.emplace(key,value).second) return false;
    }
    static const char* keys[]={"schema","image_sha256","read_contract","camera_pointer","height","minimum","maximum","runtime_read"};
    if (values.size()!=8) return false;
    for (auto key:keys) if (!values.count(key)) return false;
    if (values["schema"]!="1" || values["image_sha256"]!=sha || values["read_contract"]!="leaf_rtti_v1" || (values["runtime_read"]!="0" && values["runtime_read"]!="1")) return false;
    if (!Number(values["camera_pointer"],p.camera) || !Number(values["height"],p.height) || !Number(values["minimum"],p.minimum) || !Number(values["maximum"],p.maximum)) return false;
    p.read=values["runtime_read"]=="1";
    if (!p.read) return true;
    return p.camera>=8 && p.camera<0x10000 && p.camera%8==0 && p.height>=4 && p.height<0x10000 && p.minimum>=4 && p.minimum<0x10000 && p.maximum>=4 && p.maximum<0x10000 &&
           p.height%4==0 && p.minimum%4==0 && p.maximum%4==0 && p.height!=p.minimum && p.height!=p.maximum && p.minimum!=p.maximum;
}
bool FindTable(const char* name,ULONGLONG preferred,DWORD& table) {
    std::string decorated=std::string(".?AV")+name+"@@";decorated.push_back(0);
    std::set<DWORD> descriptors,locators,tables;
    for (const auto& s:g_sections) for(size_t i=16;i+decorated.size()<=s.bytes;++i)
        if (!memcmp(g_file.data()+s.raw+i,decorated.data(),decorated.size())) descriptors.insert(s.rva+(DWORD)i-16);
    for (const auto& s:g_sections) {
        if (s.flags&(IMAGE_SCN_MEM_WRITE|IMAGE_SCN_MEM_EXECUTE)) continue;
        for(size_t i=0;i+24<=s.bytes;i+=4) {
            DWORD col[6];memcpy(col,g_file.data()+s.raw+i,24);
            if(col[0]==1 && !col[1] && !col[2] && descriptors.count(col[3]) && FileAt(col[4],16) && col[5]==s.rva+i) locators.insert(col[5]);
        }
    }
    for (const auto& s:g_sections) {
        if (s.flags&(IMAGE_SCN_MEM_WRITE|IMAGE_SCN_MEM_EXECUTE)) continue;
        for(size_t i=0;i+40<=s.bytes;i+=8) {
            ULONGLONG col=0;memcpy(&col,g_file.data()+s.raw+i,8);
            if (col<preferred || col-preferred>MAXDWORD || !locators.count((DWORD)(col-preferred))) continue;
            bool ok=true;
            for(int j=0;j<4;++j) {ULONGLONG fn;memcpy(&fn,g_file.data()+s.raw+i+8+j*8,8);if(fn<preferred || fn-preferred>MAXDWORD || !Execute((DWORD)(fn-preferred)))ok=false;}
            if(ok) tables.insert(s.rva+(DWORD)i+8);
        }
    }
    if(tables.size()!=1) {g_reason=tables.empty()?"TABLE_MISSING":"TABLE_AMBIGUOUS";return false;}
    table=*tables.begin();return true;
}
bool Bind(ULONGLONG preferred) {
    if(!FindTable("CInGameIdler",preferred,g_binding.ingame) || !FindTable("CFrontEndIdler",preferred,g_binding.frontend)) return false;
    std::map<DWORD,unsigned> functions;
    for(unsigned slot=0;slot<256;++slot) {
        const BYTE* item=FileAt(g_binding.ingame+slot*8,8);if(!item) break;
        ULONGLONG target;memcpy(&target,item,8);
        if(target<preferred || target-preferred>MAXDWORD || !Execute((DWORD)(target-preferred)))break;
        DWORD rva=(DWORD)(target-preferred);const BYTE* code=FileAt(rva,8);if(!code)continue;
        int displacement=-1;
        if(code[0]==0x48 && code[1]==0x8b && code[2]==0x81 && code[7]==0xc3)memcpy(&displacement,code+3,4);
        else if(code[0]==0x48 && code[1]==0x8b && code[2]==0x41 && code[4]==0xc3)displacement=(signed char)code[3];
        if(displacement==(int)g_profile.camera)functions.emplace(rva,slot);
    }
    if(functions.size()!=1) {g_reason=functions.empty()?"GETTER_MISSING":"GETTER_AMBIGUOUS";return false;}
    g_binding.getter=functions.begin()->first;g_binding.slot=functions.begin()->second;
    memcpy(g_binding.code,FileAt(g_binding.getter,8),8);
    return true;
}
bool ScanRoots() {
    std::map<uintptr_t,std::vector<DWORD>> objects;std::map<uintptr_t,uintptr_t> seen;
    for(const auto& s:g_sections) {
        if(!(s.flags&IMAGE_SCN_MEM_WRITE))continue;
        std::vector<BYTE> bytes(s.mapped);
        if(!Read(g_base+s.rva,bytes.data(),bytes.size())) {g_reason="ROOT_SECTION_UNREADABLE";return false;}
        for(size_t i=0;i+8<=bytes.size();i+=8) {
            uintptr_t obj;memcpy(&obj,bytes.data()+i,8);
            if(obj<0x10000 || obj>0x7fffffffffffULL || obj%8)continue;
            if(obj>=(uintptr_t)g_base && obj-(uintptr_t)g_base<g_imageSize && !Writable((DWORD)(obj-(uintptr_t)g_base)))continue;
            auto it=seen.find(obj);uintptr_t vt=0;
            if(it==seen.end()) {Ptr((void*)obj,vt);seen.emplace(obj,vt);}else vt=it->second;
            if(vt==(uintptr_t)(g_base+g_binding.ingame) || vt==(uintptr_t)(g_base+g_binding.frontend)) objects[obj].push_back(s.rva+(DWORD)i);
        }
    }
    g_roots.clear();
    if(objects.size()!=1) {g_reason=objects.empty()?"OBJECT_MISSING":"OBJECT_AMBIGUOUS";return false;}
    g_roots=objects.begin()->second;return true;
}
bool LoadedTable(DWORD table) {
    const BYTE* expected=table>=8?FileAt(table-8,8):nullptr;
    if(!expected)return false;
    ULONGLONG disk;memcpy(&disk,expected,8);uintptr_t loaded=0;
    if(disk<g_preferred || disk-g_preferred>MAXDWORD || !Ptr(g_base+table-8,loaded) || loaded!=(uintptr_t)(g_base+(DWORD)(disk-g_preferred)))return false;
    const BYTE* col=FileAt((DWORD)(disk-g_preferred),24);BYTE actual[24];
    return col && Read((void*)loaded,actual,24) && !memcmp(col,actual,24);
}
bool Capture(NativeCameraSnapshot& out,bool full,bool validateValues=true) {
    if(!g_bound) {strcpy_s(out.status,g_reason.c_str());return false;}
    if(full || g_roots.empty()) if(!ScanRoots()) {strcpy_s(out.status,g_reason.c_str());return false;}
    uintptr_t obj=0,vt=0,cam=0,fn=0;
    for(DWORD root:g_roots) {uintptr_t p=0;if(!Ptr(g_base+root,p) || !p || (obj && p!=obj)){g_roots.clear();strcpy_s(out.status,"STATE_CHANGED");return false;}obj=p;}
    if(!Ptr((void*)obj,vt)) {g_roots.clear();strcpy_s(out.status,"OBJECT_UNREADABLE");return false;}
    if(vt==(uintptr_t)(g_base+g_binding.frontend)) {strcpy_s(out.status,LoadedTable(g_binding.frontend)?"NOT_IN_MAP":"TYPE_LAYOUT_CHANGED");return false;}
    if(vt!=(uintptr_t)(g_base+g_binding.ingame)) {g_roots.clear();strcpy_s(out.status,"TYPE_CHANGED");return false;}
    if(!LoadedTable(g_binding.ingame)) {strcpy_s(out.status,"TYPE_LAYOUT_CHANGED");return false;}
    BYTE code[8];
    if(!Ptr((void*)(vt+g_binding.slot*8),fn) || fn!=(uintptr_t)(g_base+g_binding.getter) || !Read((void*)fn,code,8) || memcmp(code,g_binding.code,8)) {strcpy_s(out.status,"GETTER_CHANGED");return false;}
    if(!Ptr((void*)(obj+g_profile.camera),cam) || cam<0x10000 || cam%8) {strcpy_s(out.status,"CAMERA_MISSING");return false;}
    float height;int low,high;
    if(!Read((void*)(cam+g_profile.height),&height,4) || !Read((void*)(cam+g_profile.minimum),&low,4) || !Read((void*)(cam+g_profile.maximum),&high,4)) {strcpy_s(out.status,"READ_FAILED");return false;}
    if(validateValues && (!isfinite(height) || low<0 || low>=high || high>1000000 || height<low || height>high)) {strcpy_s(out.status,"INVALID_VALUES");return false;}
    uintptr_t again=0;float h2;int l2,u2;
    bool same=Ptr((void*)obj,again) && again==vt && Ptr((void*)(obj+g_profile.camera),again) && again==cam;
    for(DWORD root:g_roots) same=same && Ptr(g_base+root,again) && again==obj;
    same=same && LoadedTable(g_binding.ingame) && Ptr((void*)(vt+g_binding.slot*8),again) && again==fn && Read((void*)fn,code,8) && !memcmp(code,g_binding.code,8);
    same=same && Read((void*)(cam+g_profile.height),&h2,4) && Read((void*)(cam+g_profile.minimum),&l2,4) && Read((void*)(cam+g_profile.maximum),&u2,4) && !memcmp(&height,&h2,4) && low==l2 && high==u2;
    if(!same){strcpy_s(out.status,"STATE_CHANGED");return false;}
    out.height=height;out.minimum=low;out.maximum=high;out.object=(void*)cam;strcpy_s(out.status,"READY_READ_ONLY");return true;
}
void Append(const std::string& line) {
    HANDLE file=CreateFileW(g_log.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE) {OutputDebugStringA("[hoi4plugins] function log write failed\n");return;}
    SYSTEMTIME time;GetLocalTime(&time);char prefix[64];sprintf_s(prefix,"[%02u:%02u:%02u.%03u] ",time.wHour,time.wMinute,time.wSecond,time.wMilliseconds);
    std::string text=prefix+line+"\r\n";DWORD used=0;WriteFile(file,text.data(),(DWORD)text.size(),&used,nullptr);CloseHandle(file);
}
DWORD WINAPI Monitor(void*) {
    std::string lastRead,lastWrite;
    for(;;) {
        NativeCameraSnapshot s={sizeof(s),1};int ok=Hoi4Plugin_ReadCameraV1(&s);
        if(lastRead!=s.status) {char why[256];sprintf_s(why,"%s height=%.6g limits=[%d,%d]",s.status,s.height,s.minimum,s.maximum);NativeAdapter_Report("camera.read",ok,why);lastRead=s.status;}
        bool recoverable=!strcmp(s.status,"INVALID_VALUES") && NativeAdapter_CameraObject()!=nullptr;
        bool writing=(ok || recoverable) && NativeAdapter_CameraWriteAllowed() && g_commands==3 && g_effects==4;
        std::string reason=writing?"CURRENT_BUILD_CONTRACT_AND_REGISTRATION_READY":(!NativeAdapter_CameraWriteAllowed()?"WRITE_CONTRACT_NOT_APPROVED":(!ok?s.status:"REGISTRATION_PENDING_OR_FAILED"));
        if(lastWrite!=reason) {NativeAdapter_Report("camera.write",writing,reason.c_str());lastWrite=reason;}
        Sleep(1000);
    }
}
}

int NativeAdapter_Initialize(void) {
    PublishInitialization publication;
    wchar_t path[32768];DWORD length=GetModuleFileNameW(nullptr,path,_countof(path));
    if(!length || length>=_countof(path)) {g_reason="IMAGE_PATH_FAILED";return 0;}
    std::wstring image=path;size_t slash=image.find_last_of(L"\\/");
    if(slash==std::wstring::npos)return 0;
    g_root=image.substr(0,slash);g_log=g_root+L"\\hoi4plugin_function_log.log";
    HANDLE log=CreateFileW(g_log.c_str(),GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(log==INVALID_HANDLE_VALUE) {g_reason="FUNCTION_LOG_CREATE_FAILED";return 0;}CloseHandle(log);
    g_base=(BYTE*)GetModuleHandleW(nullptr);
    try {
        g_reason="INVALID_IMAGE";
        if(!LoadImage(image)) {NativeAdapter_Report("adapter.identity",0,g_reason.c_str());return 0;}
        g_legacy=g_sha==kLegacySha;
        NativeAdapter_Report("adapter.identity",1,g_sha.c_str());
        std::vector<BYTE> bytes;
        std::wstring sha(g_sha.begin(),g_sha.end());
        if(!ReadFileBytes(g_root+L"\\hoi4plugins\\bindings\\"+sha+L".profile",bytes,4096))g_reason="PROFILE_MISSING_OR_UNREADABLE";
        else if(!ParseProfile(bytes,g_sha,g_profile))g_reason="PROFILE_INVALID";
        else if(!g_profile.read)g_reason="PROFILE_RUNTIME_NOT_APPROVED";
        else {
            const auto* dos=(const IMAGE_DOS_HEADER*)g_file.data();
            const auto* nt=(const IMAGE_NT_HEADERS64*)(g_file.data()+dos->e_lfanew);
            g_bound=Bind(nt->OptionalHeader.ImageBase);
            if(g_bound)g_reason="BINDING_READY";
        }
        NativeAdapter_Report("camera.binding",g_bound,g_reason.c_str());
        char summary[160];sprintf_s(summary,"ingame=0x%X frontend=0x%X getter=0x%X slot=%u",g_binding.ingame,g_binding.frontend,g_binding.getter,g_binding.slot);
        if(g_bound)NativeAdapter_Report("camera.binding.details",1,summary);
    } catch(...) {g_bound=false;g_reason="ADAPTER_INITIALIZATION_EXCEPTION";NativeAdapter_Report("camera.binding",0,g_reason.c_str());}
    return g_legacy?1:0;
}
int NativeAdapter_LegacyAllowed(void) {return g_legacy?1:0;}
int NativeAdapter_CameraWriteAllowed(void) {return g_legacy && g_bound && g_profile.camera==0x750 && g_profile.height==0x69c && g_profile.minimum==0x6d0 && g_profile.maximum==0x6d4;}
const char* NativeAdapter_Diagnostic(void) {return g_reason.c_str();}
void NativeAdapter_Report(const char* name,int available,const char* reason) {
    if(!name || !reason || g_log.empty())return;
    AcquireSRWLockExclusive(&g_logLock);
    auto it=g_status.find(name);
    if(it==g_status.end() || it->second.available!=!!available || it->second.reason!=reason) {
        g_status[name]={!!available,reason};
        Append(std::string(available?"[function:available] ":"[function:unavailable] ")+name+" : "+reason);
    }
    ReleaseSRWLockExclusive(&g_logLock);
}
void NativeAdapter_CameraRegistered(int commands,int effects) {InterlockedExchange(&g_commands,commands);InterlockedExchange(&g_effects,effects);}
int Hoi4Plugin_ReadCameraV1(NativeCameraSnapshot* out) {
    if(!out || out->size!=sizeof(*out) || out->version!=1)return 0;
    NativeCameraSnapshot value={sizeof(value),1};bool ok=false;
    if(!InterlockedCompareExchange(&g_prepared,0,0)) {strcpy_s(value.status,"INITIALIZING");*out=value;return 0;}
    AcquireSRWLockExclusive(&g_cameraLock);
    try {ok=Capture(value,true);}catch(...) {strcpy_s(value.status,"SNAPSHOT_EXCEPTION");}
    ReleaseSRWLockExclusive(&g_cameraLock);
    *out=value;return ok?1:0;
}
void* NativeAdapter_CameraObject(void) {
    if(!InterlockedCompareExchange(&g_prepared,0,0))return nullptr;
    if(!NativeAdapter_CameraWriteAllowed())return nullptr;
    NativeCameraSnapshot value={sizeof(value),1};bool ok=false;
    AcquireSRWLockExclusive(&g_cameraLock);
    try {ok=Capture(value,false,false);}catch(...) {strcpy_s(value.status,"SNAPSHOT_EXCEPTION");}
    ReleaseSRWLockExclusive(&g_cameraLock);
    return ok?value.object:nullptr;
}
void NativeAdapter_StartMonitor(void) {
    if(InterlockedCompareExchange(&g_monitor,1,0))return;
    NativeAdapter_Report("camera.read",0,"WAITING_FOR_LIVE_OBJECT");NativeAdapter_Report("camera.write",0,"WAITING_FOR_READ_AND_REGISTRATION");
    HANDLE thread=CreateThread(nullptr,0,Monitor,nullptr,0,nullptr);
    if(thread)CloseHandle(thread);else NativeAdapter_Report("camera.read",0,"MONITOR_THREAD_FAILED");
}
void NativeAdapter_OpenLogConsole(void) {
    int count=0;wchar_t** arguments=CommandLineToArgvW(GetCommandLineW(),&count);bool enabled=true;
    for(int i=1;arguments && i<count;++i)if(!_wcsicmp(arguments[i],L"-no-plugin-console"))enabled=false;
    if(arguments)LocalFree(arguments);
    if(!enabled)return;
    std::wstring helper=g_root+L"\\hoi4_debug_console.exe";
    wchar_t command[32768];_snwprintf_s(command,_countof(command),_TRUNCATE,L"\"%s\" --pid %lu --read-only",helper.c_str(),GetCurrentProcessId());
    STARTUPINFOW si={sizeof(si)};PROCESS_INFORMATION pi={};
    if(CreateProcessW(helper.c_str(),command,nullptr,nullptr,FALSE,CREATE_NEW_CONSOLE,nullptr,g_root.c_str(),&si,&pi)) {CloseHandle(pi.hThread);CloseHandle(pi.hProcess);}
    else NativeAdapter_Report("console.log_viewer",0,"HELPER_LAUNCH_FAILED");
}
