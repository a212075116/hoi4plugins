#include "../../../src/plugin/adapter/native_adapter.cpp"
static int checks,failed;
static void Check(const char* name,bool ok){++checks;if(!ok){++failed;printf("FAIL %s (%s)\n",name,g_scriptReason.c_str());}}
static void MapImage() {
    g_base=(BYTE*)VirtualAlloc(nullptr,g_imageSize,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    const auto* dos=(const IMAGE_DOS_HEADER*)g_file.data();const auto* nt=(const IMAGE_NT_HEADERS64*)(g_file.data()+dos->e_lfanew);
    memcpy(g_base,g_file.data(),nt->OptionalHeader.SizeOfHeaders);
    for(const auto& s:g_sections)memcpy(g_base+s.rva,g_file.data()+s.raw,s.bytes);
    auto relocation=nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC];
    for(DWORD at=0;at<relocation.Size;) {
        auto* block=(IMAGE_BASE_RELOCATION*)(g_base+relocation.VirtualAddress+at);if(block->SizeOfBlock<8)break;
        WORD* items=(WORD*)(block+1);
        for(unsigned i=0;i<(block->SizeOfBlock-8)/2;++i)if(items[i]>>12==IMAGE_REL_BASED_DIR64) {
            ULONGLONG* value=(ULONGLONG*)(g_base+block->VirtualAddress+(items[i]&0xfff));*value+=(ULONGLONG)g_base-g_preferred;
        }
        at+=block->SizeOfBlock;
    }
}
int wmain(int argc,wchar_t** argv) {
    if(argc<2 || !LoadImage(argv[1],false))return 2;
    NativeScriptTemplate t[4]={};DWORD allocation=0;
    if(!BindScriptTemplates(t,allocation,false)){printf("%s\n",g_scriptReason.c_str());return 1;}
    printf("image=%s allocator=0x%X\n",g_sha.c_str(),allocation);
    for(int i=0;i<4;++i)printf("template=%d vt=0x%X entry=0x%X factory=0x%X parse=0x%X eval=0x%X slots=%u bytes=%u\n",i,t[i].vt,t[i].entryVt,t[i].factory,t[i].parse,t[i].eval,t[i].slots,t[i].allocation);
    Check("all-factories-derived",allocation!=0);
    for(int kind=0;kind<4;++kind) {
        const BYTE* pos=FileAt(t[kind].factory,192);size_t offset=(size_t)(pos-g_file.data());BYTE saved=g_file[offset+8];g_file[offset+8]^=1;
        NativeScriptTemplate bad[4]={};DWORD alloc=0;Check("allocation-size-change-refused",!BindScriptTemplates(bad,alloc,false));g_file[offset+8]=saved;
    }
    if(argc==3) {
        MapImage();NativeScriptTemplate loaded[4]={};DWORD heap=0;Check("relocated-loaded-tables",BindScriptTemplates(loaded,heap,true));
        wchar_t temp[MAX_PATH],dir[MAX_PATH];GetTempPathW(MAX_PATH,temp);GetTempFileNameW(temp,L"h4r",0,dir);DeleteFileW(dir);CreateDirectoryW(dir,nullptr);
        g_root=dir;CreateDirectoryW((g_root+L"\\hoi4plugins").c_str(),nullptr);CreateDirectoryW((g_root+L"\\hoi4plugins\\bindings").c_str(),nullptr);
        std::wstring hash(g_sha.begin(),g_sha.end()),profile=g_root+L"\\hoi4plugins\\bindings\\"+hash+L".registry";
        CopyFileW(argv[2],profile.c_str(),FALSE);Check("full-runtime-bindings",InitializeScriptBindings());InterlockedExchange(&g_prepared,1);
        Check("ready-api",NativeAdapter_RegistryReady() && NativeAdapter_RegistryRva(NS_GAME_ALLOC)==allocation && NativeAdapter_StaticTokenCount()==10765);
        Check("registry-not-symbol-group-bypass",NativeAdapter_RegistryReady() && !NativeAdapter_GroupReady(NG_CORE) && !NativeAdapter_Symbol(NSY_GAMESTATE));
        std::vector<BYTE> original;ReadFileBytes(profile,original,32768);
        for(const std::string extra:{"schema=1\n","unknown=1\n","heap.free=0x1:00\n"}) {
            std::vector<BYTE> data=original;data.insert(data.end(),extra.begin(),extra.end());std::map<std::string,std::string> fields;Check("strict-profile-keys",!ScriptFields(data,fields));
        }
        std::vector<BYTE> data=original;data.push_back(0);std::map<std::string,std::string> fields;Check("nul-refused",!ScriptFields(data,fields));
        for(const char* key:{"static_token_count","effect.map","heap.free"}) {
            std::string text((const char*)original.data(),original.size());std::string match=std::string(key)+"=";size_t begin=text.find(match),end=text.find('\n',begin);
            text.replace(begin,end-begin,match+(std::string(key)=="heap.free"?"0x1:00000000000000000000000000000000":"0"));
            HANDLE h=CreateFileW(profile.c_str(),GENERIC_WRITE,0,nullptr,CREATE_ALWAYS,0,nullptr);DWORD used;WriteFile(h,text.data(),(DWORD)text.size(),&used,nullptr);CloseHandle(h);
            Check("invalid-binding-refused",!InitializeScriptBindings());Check("atomic-binding-failure",!NativeAdapter_RegistryReady()&&!NativeAdapter_RegistryRva(NS_ADD_TOKEN)&&!NativeAdapter_StaticTokenCount());
        }
        CopyFileW(argv[2],profile.c_str(),FALSE);Check("cold-retry-after-profile-fix",InitializeScriptBindings());
        BYTE old=g_base[t[0].factory];g_base[t[0].factory]=0x90;NativeScriptTemplate bad[4]={};DWORD alloc=0;Check("patched-factory-refused",!BindScriptTemplates(bad,alloc,true));g_base[t[0].factory]=old;
        uintptr_t oldPointer=0;Ptr(g_base+t[1].entryVt+8,oldPointer);uintptr_t zero=0;memcpy(g_base+t[1].entryVt+8,&zero,8);Check("patched-entry-refused",!BindScriptTemplates(bad,alloc,true));memcpy(g_base+t[1].entryVt+8,&oldPointer,8);
        g_scriptReady=false;Check("no-partial-api",NativeAdapter_RegistryRva(NS_EFFECT_MAP)==0 && !NativeAdapter_ScriptTemplate(0,&bad[0]));
        DeleteFileW(profile.c_str());RemoveDirectoryW((g_root+L"\\hoi4plugins\\bindings").c_str());RemoveDirectoryW((g_root+L"\\hoi4plugins").c_str());RemoveDirectoryW(g_root.c_str());VirtualFree(g_base,0,MEM_RELEASE);g_base=nullptr;
    }
    printf("script-binding checks=%d failed=%d\n",checks,failed);return failed?1:0;
}
