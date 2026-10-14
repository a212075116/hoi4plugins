struct ScriptSpec {const char* key;unsigned id,bytes;bool function,readonly;};
static const ScriptSpec kScriptSpecs[]={
    {"effect.map",NS_EFFECT_MAP,8,false,false},{"effect.register",NS_EFFECT_REGISTER,16,true,false},
    {"token.add",NS_ADD_TOKEN,16,true,false},{"lexer.init",NS_LEXER_INIT,1,false,false},{"lexer.sync",NS_LEXER_SYNC,1,false,false},
    {"param.get",NS_PARAM_GET,16,true,false},{"param.ctor",NS_PARAM_CTOR,16,true,false},{"param.dtor",NS_PARAM_DTOR,16,true,false},
    {"param.tag",NS_PARAM_TAG,8,false,true},{"text.pack",NS_TEXT_PACK,16,true,false},{"text.format",NS_TEXT_FORMAT,16,true,false},
    {"text.append",NS_TEXT_APPEND,16,true,false},{"trigger.map",NS_TRIGGER_MAP,8,false,false},{"trigger.register",NS_TRIGGER_REGISTER,16,true,false},
    {"heap.free",NS_GAME_FREE,16,true,false},{"token.static",NS_STATIC_TOKENS,72,false,false},
    {"scope.mask",NS_SCOPE_MASK,16,true,false},{"param.temporary",NS_TEMPORARY,16,true,false},{"param.name",NS_PARAM_NAME,16,true,false},
    {"param.contains",NS_CONTAINS,16,true,false},{"param.container",NS_CONTAINER,16,true,false},{"string.ctor",NS_STRING_CTOR,16,true,false}
};
static const char* kScriptTypes[]={"CAddStabilityEffect","CAlwaysTrigger","CHasStabilityTrigger","CCheckVariable"};
static const char* kScriptEntries[]={"?$CEffectEntry@VCAddStabilityEffect@@","?$CTriggerEntry@VCAlwaysTrigger@@","?$CTriggerEntry@VCHasStabilityTrigger@@","?$CTriggerEntry@VCCheckVariable@@"};
static const unsigned kScriptSlots[]={25,23,26,23},kScriptSizes[]={296,96,304,544};
DWORD g_scriptValues[NS_SYMBOL_COUNT]={};
NativeScriptTemplate g_scriptTemplates[4]={};
unsigned g_staticTokenCount=0;
bool g_scriptReady=false;
std::string g_scriptReason="REGISTRY_NOT_INITIALIZED";

bool ScriptFail(const char* reason) {g_scriptReason=reason;return false;}
bool ScriptNumber(const std::string& text,DWORD maximum,DWORD& value) {
    if(text.empty() || text[0]=='-' || text[0]=='+')return false;
    char* end=nullptr;errno=0;unsigned long long n=_strtoui64(text.c_str(),&end,0);
    if(errno || !end || *end || n>maximum)return false;
    value=(DWORD)n;return true;
}
bool ScriptLoadedCode(DWORD rva,unsigned count,bool loaded) {
    const BYTE* disk=FileAt(rva,count);if(!disk || !Execute(rva) || !Execute(rva+count-1))return false;
    BYTE bytes[32];if(count>sizeof(bytes))return false;
    return !loaded || (Read(g_base+rva,bytes,count) && !memcmp(bytes,disk,count));
}
bool BindScriptTemplates(NativeScriptTemplate* result,DWORD& allocation,bool loaded) {
    allocation=0;
    for(int kind=0;kind<4;++kind) {
        NativeScriptTemplate t={};
        DWORD vt=0,entry=0;
        if(!FindTable(kScriptTypes[kind],g_preferred,vt) || !FindTable(kScriptEntries[kind],g_preferred,entry,2))return ScriptFail(g_reason.c_str());
        t.vt=vt;t.entryVt=entry;
        t.slots=kScriptSlots[kind];t.allocation=kScriptSizes[kind];
        if(loaded && (!LoadedTable(t.vt) || !LoadedTable(t.entryVt)))return ScriptFail("TEMPLATE_LOADED_RTTI_CHANGED");
        for(unsigned slot=0;slot<t.slots;++slot) {
            const BYTE* raw=FileAt(t.vt+slot*8,8);ULONGLONG fn=0;uintptr_t actual=0;
            if(!raw)return ScriptFail("TEMPLATE_RANGE_INVALID");memcpy(&fn,raw,8);
            if(fn<g_preferred || fn-g_preferred>MAXDWORD || !ScriptLoadedCode((DWORD)(fn-g_preferred),16,loaded) ||
                (loaded && (!Ptr(g_base+t.vt+slot*8,actual) || actual!=(uintptr_t)(g_base+(DWORD)(fn-g_preferred)))))return ScriptFail("TEMPLATE_SLOT_INVALID");
            if(slot==4)t.parse=(DWORD)(fn-g_preferred);
            if(slot==(kind==0?13u:22u))t.eval=(DWORD)(fn-g_preferred);
        }
        for(unsigned slot=0;slot<2;++slot) {
            const BYTE* raw=FileAt(t.entryVt+slot*8,8);ULONGLONG fn=0;uintptr_t actual=0;
            if(!raw)return ScriptFail("ENTRY_RANGE_INVALID");memcpy(&fn,raw,8);
            if(fn<g_preferred || fn-g_preferred>MAXDWORD || !ScriptLoadedCode((DWORD)(fn-g_preferred),16,loaded) ||
                (loaded && (!Ptr(g_base+t.entryVt+slot*8,actual) || actual!=(uintptr_t)(g_base+(DWORD)(fn-g_preferred)))))return ScriptFail("ENTRY_SLOT_INVALID");
            if(!slot && !kind)t.parse=(DWORD)(fn-g_preferred);
            if(slot)t.factory=(DWORD)(fn-g_preferred);
        }
        const BYTE* code=FileAt(t.factory,192);if(!code)return ScriptFail("FACTORY_RANGE_INVALID");
        unsigned prefix=code[0]==0x40?1:0;static const BYTE prologue[]={0x53,0x48,0x83,0xec,0x20,0xb9};
        if(memcmp(code+prefix,prologue,6) || code[prefix+10]!=0xe8)return ScriptFail("FACTORY_ABI_UNRECOGNIZED");
        DWORD size=0;int relative=0;memcpy(&size,code+prefix+6,4);memcpy(&relative,code+prefix+11,4);
        long long target=(long long)t.factory+prefix+15+relative;
        if(size!=t.allocation || target<0 || target>MAXDWORD || !ScriptLoadedCode((DWORD)target,16,loaded))return ScriptFail("FACTORY_ALLOCATION_CONTRACT_CHANGED");
        if(allocation && allocation!=(DWORD)target)return ScriptFail("ALLOCATOR_DISAGREEMENT");allocation=(DWORD)target;
        bool stores=false;
        for(unsigned i=0;i+10<=192;++i) {
            if(code[i]!=0x48 || code[i+1]!=0x8d || code[i+2]!=0x05 || memcmp(code+i+7,"\x48\x89\x03",3))continue;
            memcpy(&relative,code+i+3,4);
            if((long long)t.factory+i+7+relative!=t.vt)continue;
            BYTE actual[10];if(!loaded || (Read(g_base+t.factory+i,actual,10) && !memcmp(actual,code+i,10)))stores=true;
        }
        if(!stores)return ScriptFail("FACTORY_DERIVED_VTABLE_STORE_MISSING");
        result[kind]=t;
    }
    return true;
}
bool ScriptFields(const std::vector<BYTE>& bytes,std::map<std::string,std::string>& fields) {
    if(bytes.empty() || bytes.size()>32768 || std::any_of(bytes.begin(),bytes.end(),[](BYTE c){return c==0 || c>127;}))return ScriptFail("REGISTRY_PROFILE_ENCODING_OR_SIZE");
    size_t start=0;
    while(start<bytes.size()) {
        size_t end=start;while(end<bytes.size() && bytes[end]!='\n')++end;
        std::string line=Trim(std::string((const char*)bytes.data()+start,end-start));start=end+1;if(line.empty())continue;
        size_t equal=line.find('=');if(equal==std::string::npos || !fields.emplace(Trim(line.substr(0,equal)),Trim(line.substr(equal+1))).second)return ScriptFail("REGISTRY_PROFILE_DUPLICATE_OR_SYNTAX");
    }
    if(fields.size()!=5+_countof(kScriptSpecs) || fields["schema"]!="1" || fields["image_sha256"]!=g_sha || fields["contract"]!="registry_v1" || (fields["runtime_registration"]!="1" && fields["runtime_registration"]!="0"))return ScriptFail("REGISTRY_PROFILE_IDENTITY_OR_SCHEMA");
    return true;
}
bool InitializeScriptBindings() {
    g_scriptReady=false;memset(g_scriptValues,0,sizeof(g_scriptValues));memset(g_scriptTemplates,0,sizeof(g_scriptTemplates));g_staticTokenCount=0;
    std::vector<BYTE> bytes;std::wstring sha(g_sha.begin(),g_sha.end());
    if(!ReadFileBytes(g_root+L"\\hoi4plugins\\bindings\\"+sha+L".registry",bytes,32768))return ScriptFail("REGISTRY_PROFILE_MISSING");
    std::map<std::string,std::string> fields;if(!ScriptFields(bytes,fields))return false;
    if(fields["runtime_registration"]!="1")return ScriptFail("REGISTRY_RUNTIME_NOT_APPROVED");
    DWORD values[NS_SYMBOL_COUNT]={},count=0;NativeScriptTemplate templates[4]={};
    if(!ScriptNumber(fields["static_token_count"],65536,count) || !count)return ScriptFail("STATIC_TOKEN_COUNT_INVALID");
    for(const auto& spec:kScriptSpecs) {
        auto it=fields.find(spec.key);if(it==fields.end())return ScriptFail("REGISTRY_PROFILE_KEY_MISSING");
        std::string text=it->second;size_t colon=text.find(':');DWORD rva=0;
        if(!ScriptNumber(text.substr(0,colon),g_imageSize,rva) || !rva)return ScriptFail("BINDING_RVA_INVALID");
        if(spec.function) {
            if(colon==std::string::npos || text.size()-colon-1!=32 || !ScriptLoadedCode(rva,16,true))return ScriptFail("BINDING_CODE_CHANGED");
            const BYTE* actual=FileAt(rva,16);
            for(unsigned i=0;i<16;++i) {
                const char* hex="0123456789abcdef";
                if(text[colon+1+i*2]!=hex[actual[i]>>4] || text[colon+2+i*2]!=hex[actual[i]&15])return ScriptFail("BINDING_FINGERPRINT_MISMATCH");
            }
        } else {
            if(colon!=std::string::npos)return ScriptFail("BINDING_DATA_FORMAT");
            size_t span=spec.id==NS_STATIC_TOKENS?(size_t)count*72:spec.bytes;
            bool valid=false;
            for(const auto& s:g_sections)if(rva>=s.rva && rva-s.rva<=s.mapped && span<=s.mapped-(rva-s.rva))
                valid=spec.readonly?!(s.flags&(IMAGE_SCN_MEM_WRITE|IMAGE_SCN_MEM_EXECUTE)):(s.flags&IMAGE_SCN_MEM_WRITE)!=0;
            if(!valid)return ScriptFail("BINDING_DATA_SECTION_INVALID");
        }
        values[spec.id]=rva;
    }
    if(!BindScriptTemplates(templates,values[NS_GAME_ALLOC],true))return false;
    memcpy(g_scriptValues,values,sizeof(values));memcpy(g_scriptTemplates,templates,sizeof(templates));g_staticTokenCount=count;
    g_scriptReady=true;g_scriptReason="READY_ADDRESS_AND_DECLARED_ABI_CONTRACT";return true;
}
