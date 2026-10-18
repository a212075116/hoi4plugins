#include "../../../src/plugin/adapter/native_adapter.cpp"
static int checks,failed;
static void Check(const char* name,bool ok){++checks;if(!ok){++failed;printf("FAIL %s\n",name);}}
#include "../../lib/native_symbols_values.h"
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
static std::wstring g_profilePath;
static std::string g_original;
static void WriteProfile(const std::string& text) {
    HANDLE h=CreateFileW(g_profilePath.c_str(),GENERIC_WRITE,0,nullptr,CREATE_ALWAYS,0,nullptr);DWORD used=0;
    WriteFile(h,text.data(),(DWORD)text.size(),&used,nullptr);CloseHandle(h);
}
static std::string Replace(std::string text,const std::string& key,const std::string& value) {
    size_t begin=text.find("\n"+key+"=");if(begin==std::string::npos)return text;begin+=1;size_t end=text.find('\n',begin);
    return text.replace(begin,end-begin,key+"="+value);
}
static bool AllReady() {for(int i=0;i<NG_COUNT;++i)if(!g_groupReady[i])return false;return true;}
static bool Matches() {for(int i=0;i<NSY_COUNT;++i)if(g_symbolValues[i]!=kNativeSymbolValues[i])return false;return true;}
static void Reload() {g_rttiBuilt=false;InitializeNativeSymbols();}
int wmain(int argc,wchar_t** argv) {
    if(argc<3 || !LoadImage(argv[1],false))return 2;
    MapImage();
    wchar_t temp[MAX_PATH],dir[MAX_PATH];GetTempPathW(MAX_PATH,temp);GetTempFileNameW(temp,L"h4s",0,dir);DeleteFileW(dir);CreateDirectoryW(dir,nullptr);
    g_root=dir;CreateDirectoryW((g_root+L"\\hoi4plugins").c_str(),nullptr);CreateDirectoryW((g_root+L"\\hoi4plugins\\bindings").c_str(),nullptr);
    std::wstring hash(g_sha.begin(),g_sha.end());g_profilePath=g_root+L"\\hoi4plugins\\bindings\\"+hash+L".symbols";
    std::vector<BYTE> bytes;if(!ReadFileBytes(argv[2],bytes,32768))return 3;g_original.assign(bytes.begin(),bytes.end());
    g_scriptReady=true;InterlockedExchange(&g_prepared,1);
    if(argc>=4 && !wcscmp(argv[3],L"--accept")) {
        std::string text=g_original;
        for(const auto& g:kGroupSpecs)text=Replace(text,std::string("approve.")+g.name,"1");
        WriteProfile(text);Reload();int ready=0;
        for(const auto& g:kGroupSpecs) {ready+=g_groupReady[g.id];printf("%-12s %s %s\n",g.name,g_groupReady[g.id]?"READY":"CLOSED",g_groupReason[g.id].c_str());}
        DeleteFileW(g_profilePath.c_str());RemoveDirectoryW((g_root+L"\\hoi4plugins\\bindings").c_str());RemoveDirectoryW((g_root+L"\\hoi4plugins").c_str());RemoveDirectoryW(g_root.c_str());
        printf("native-symbols accept ready=%d groups=%d\n",ready,(int)NG_COUNT);return ready==NG_COUNT?0:1;
    }
    Check("missing-profile-refused",(Reload(),!g_groupReady[NG_CORE] && g_groupReason[NG_CORE]=="SYMBOLS_PROFILE_MISSING"));
    WriteProfile(g_original);Reload();
    Check("all-groups-ready",AllReady());
    Check("values-equal-previous-constants",Matches());
    for(int i=0;i<NSY_COUNT;++i)if(g_symbolValues[i]!=kNativeSymbolValues[i])printf("  mismatch %s got=0x%X want=0x%X\n",kSymbolSpecs[i].key,g_symbolValues[i],kNativeSymbolValues[i]);
    Check("api-matches",NativeAdapter_Symbol(NSY_VAR_ADD_EXEC)==0x34C760 && NativeAdapter_GroupReady(NG_ACHIEVEMENT) && NativeAdapter_Symbol(NSY_COUNT)==0 && NativeAdapter_Symbol(-1)==0);
    {bool same=true;for(int i=0;i<NFL_COUNT;++i)if(g_fieldValues[i]!=kNativeFieldValues[i]) {same=false;printf("  field mismatch %s got=0x%X want=0x%X\n",kFieldSpecs[i].key,g_fieldValues[i],kNativeFieldValues[i]);}Check("fields-equal-previous-constants",same);}
    Check("field-api",NativeAdapter_Field(NFL_CAMERA_HEIGHT)==0x69C && NativeAdapter_Field(NFL_TRIGGER_COMPARE)==504 && NativeAdapter_Field(NFL_COUNT)==0 && NativeAdapter_Field(-1)==0);
    WriteProfile(Replace(g_original,"field.var64.name","0"));Reload();
    Check("zero-field-closes-own-group",!g_groupReady[NG_VAR64] && g_groupReason[NG_VAR64]=="SYMBOL_field.var64.name:FIELD_INVALID" && !g_groupReady[NG_ARRAY64] && g_groupReady[NG_SCRIPT] && g_groupReady[NG_CONSOLE] && NativeAdapter_Field(NFL_VAR64_NAME)==0 && NativeAdapter_Field(NFL_PARAM_TEXT)==0x70 && NativeAdapter_Symbol(NSY_VAR_LOOKUP)==0);
    WriteProfile(Replace(g_original,"field.console.network","0x10000"));Reload();
    Check("oversized-field-closes-dependents",!g_groupReady[NG_CONSOLE] && !g_groupReady[NG_ACHIEVEMENT] && !g_groupReady[NG_BRIDGE] && g_groupReady[NG_CORE] && g_groupReady[NG_VAR64] && g_groupReason[NG_CONSOLE]=="SYMBOL_field.console.network:FIELD_INVALID");
    for(const char* bad:{"abc","-4","0x","+8"}) {WriteProfile(Replace(g_original,"field.gamedate.raw",bad));Reload();Check("malformed-field-refused",!g_groupReady[NG_GAMEDATE] && g_groupReady[NG_CORE] && NativeAdapter_Field(NFL_GD_YEAR)==0);}
    WriteProfile(Replace(g_original,"field.param.text","0"));Reload();
    Check("script-field-closes-var64-chain",!g_groupReady[NG_SCRIPT] && !g_groupReady[NG_VAR64] && !g_groupReady[NG_ARRAY64] && g_groupReason[NG_VAR64]=="DEPENDENCY_script" && g_groupReady[NG_ACHIEVEMENT] && g_groupReady[NG_GAMEDATE]);
    WriteProfile(Replace(g_original,"approve.camera_write","0"));Reload();
    Check("unapproved-group-fields-zero",!g_groupReady[NG_CAMERA_WRITE] && NativeAdapter_Field(NFL_CAMERA_HEIGHT)==0 && g_fieldValues[NFL_CAMERA_OBJECT]==0 && g_groupReady[NG_CORE]);
    {std::string text=g_original;size_t at=text.find("field.camera.maximum=");text.erase(at,text.find('\n',at)-at+1);WriteProfile(text);Reload();Check("missing-field-key-refused",g_groupReason[NG_CORE]=="SYMBOLS_PROFILE_KEY_SET");}
    WriteProfile(g_original+"field.camera.interpolation=0x698\n");Reload();
    Check("unknown-field-key-refused",g_groupReason[NG_CORE]=="SYMBOLS_PROFILE_KEY_SET");
    WriteProfile(Replace(g_original,"contract","symbols_v1"));Reload();
    Check("v1-contract-refused",g_groupReason[NG_CORE]=="SYMBOLS_PROFILE_IDENTITY_OR_SCHEMA");
    WriteProfile(g_original);Reload();
    g_scriptReady=false;Reload();
    Check("registry-dependency",g_groupReady[NG_CORE] && !g_groupReady[NG_BRIDGE] && !g_groupReady[NG_VAR64] && !g_groupReady[NG_ARRAY64] && !g_groupReady[NG_SCRIPT] && g_groupReason[NG_SCRIPT]=="DEPENDENCY_SCRIPT_REGISTRY" && g_groupReason[NG_VAR64]=="DEPENDENCY_script" && g_symbolValues[NSY_VAR_LOOKUP]==0 && NativeAdapter_Field(NFL_PARAM_TEXT)==0 && g_groupReady[NG_ACHIEVEMENT]);
    g_scriptReady=true;
    WriteProfile(Replace(g_original,"approve.core","0"));Reload();
    Check("core-unapproved-propagates",!g_groupReady[NG_CORE] && !g_groupReady[NG_CONSOLE] && !g_groupReady[NG_ACHIEVEMENT] && !g_groupReady[NG_DIAG] && !g_groupReady[NG_SCRIPT] && !g_groupReady[NG_GAMEDATE] && g_groupReady[NG_IMPORTS] && g_groupReady[NG_CAMERA_WRITE] && g_groupReason[NG_CONSOLE]=="DEPENDENCY_core" && NativeAdapter_Symbol(NSY_GAMESTATE)==0 && NativeAdapter_Field(NFL_ACH_COUNT)==0);
    WriteProfile(Replace(g_original,"approve.var64","0"));Reload();
    Check("var64-unapproved-keeps-others",!g_groupReady[NG_VAR64] && !g_groupReady[NG_ARRAY64] && g_groupReady[NG_CONSOLE] && g_groupReady[NG_ACHIEVEMENT] && g_groupReason[NG_VAR64]=="GROUP_NOT_APPROVED");
    WriteProfile(Replace(g_original,"var64.lookup","0x542280:00000000000000000000000000000000"));Reload();
    Check("fingerprint-mismatch-closes-group",!g_groupReady[NG_VAR64] && g_groupReason[NG_VAR64]=="SYMBOL_var64.lookup:FINGERPRINT_MISMATCH" && !g_groupReady[NG_ARRAY64] && g_groupReady[NG_CONSOLE] && !g_symbolValues[NSY_VAR_ADD_EXEC]);
    WriteProfile(Replace(g_original,"core.gamestate","0x129ca0"));Reload();
    Check("data-in-code-refused",!g_groupReady[NG_CORE] && g_groupReason[NG_CORE]=="SYMBOL_core.gamestate:DATA_SECTION_INVALID");
    WriteProfile(Replace(g_original,"core.gamestate","0x332f260:48895c241048896c2418565741574883"));Reload();
    Check("data-format-refused",!g_groupReady[NG_CORE]);
    WriteProfile(Replace(g_original,"console.merge","0x24b4920"));Reload();
    Check("code-without-fingerprint-refused",!g_groupReady[NG_CONSOLE] && g_groupReady[NG_CORE]);
    WriteProfile(Replace(g_original,"approve.diag","2"));Reload();
    Check("approval-value-refused",!AllReady() && g_groupReason[NG_CORE]=="SYMBOLS_PROFILE_APPROVAL_VALUE");
    for(const std::string extra:{"schema=1\n","unknown=1\n","var64.add_exec=0x34c760\n"}) {WriteProfile(g_original+extra);Reload();Check("strict-key-set",!g_groupReady[NG_CORE]);}
    {std::string text=g_original;text.erase(text.find("achievement.flag_log="),text.find('\n',text.find("achievement.flag_log="))-text.find("achievement.flag_log=")+1);WriteProfile(text);Reload();Check("missing-key-refused",g_groupReason[NG_CORE]=="SYMBOLS_PROFILE_KEY_SET");}
    WriteProfile(Replace(g_original,"image_sha256",std::string(64,'0')));Reload();
    Check("identity-mismatch-refused",g_groupReason[NG_CORE]=="SYMBOLS_PROFILE_IDENTITY_OR_SCHEMA");
    {std::string text=g_original;text.push_back(0);WriteProfile(text);Reload();Check("nul-refused",g_groupReason[NG_CORE]=="SYMBOLS_PROFILE_ENCODING_OR_SIZE");}
    WriteProfile(g_original);
    {
        DWORD table=kNativeSymbolValues[NSY_VAR_ADD_EXEC];(void)table;
        DWORD addTable=0;BuildRttiIndex();auto it=g_rtti.find(std::make_pair(std::string(".?AVCAddToVariableEffect@@"),(DWORD)0));
        addTable=it==g_rtti.end()?0:it->second[0];
        uintptr_t saved=0;Ptr(g_base+addTable+13*8,saved);uintptr_t other=(uintptr_t)(g_base+0x129CA0);memcpy(g_base+addTable+13*8,&other,8);Reload();
        Check("patched-loaded-slot-refused",!g_groupReady[NG_VAR64] && g_groupReason[NG_VAR64]=="SYMBOL_var64.add_exec:RTTI_LOADED_SLOT_CHANGED" && g_groupReady[NG_CONSOLE]);
        memcpy(g_base+addTable+13*8,&saved,8);
        BYTE code=g_base[0xDD3A50];g_base[0xDD3A50]=0xCC;Reload();
        Check("patched-slot-code-refused",!g_groupReady[NG_BRIDGE] && g_groupReason[NG_BRIDGE]=="SYMBOL_bridge.frame:RTTI_SLOT_CODE_CHANGED" && g_groupReady[NG_CONSOLE]);
        g_base[0xDD3A50]=code;
        BYTE fp=g_base[0x24B4920];g_base[0x24B4920]=0xCC;Reload();
        Check("patched-code-refused",!g_groupReady[NG_CONSOLE] && !g_groupReady[NG_ACHIEVEMENT] && !g_groupReady[NG_BRIDGE] && g_groupReady[NG_VAR64]);
        g_base[0x24B4920]=fp;
        Reload();Check("recovered-after-restore",AllReady() && Matches());
    }
    g_prepared=0;Check("unpublished-api-closed",!NativeAdapter_GroupReady(NG_CORE) && NativeAdapter_Symbol(NSY_GAMESTATE)==0);
    DeleteFileW(g_profilePath.c_str());RemoveDirectoryW((g_root+L"\\hoi4plugins\\bindings").c_str());RemoveDirectoryW((g_root+L"\\hoi4plugins").c_str());RemoveDirectoryW(g_root.c_str());
    printf("native-symbols checks=%d failed=%d rtti_keys=%zu\n",checks,failed,g_rtti.size());return failed?1:0;
}
