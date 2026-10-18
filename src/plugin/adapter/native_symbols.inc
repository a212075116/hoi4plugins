enum SymbolKind {SK_CODE,SK_DATA,SK_SLOT,SK_TABLE};
struct SymbolSpec {int id,group,kind;const char* key;const char* type;unsigned offset,index,bytes;};
struct GroupSpec {int id;const char* name;bool registry;int first,second;};
static const GroupSpec kGroupSpecs[]={
#define NATIVE_GROUP(id,name,registry,first,second) {id,name,(registry)!=0,first,second},
#define NATIVE_CODE(id,group,key)
#define NATIVE_DATA(id,group,key,bytes)
#define NATIVE_SLOT(id,group,key,type,offset,slot)
#define NATIVE_TABLE(id,group,key,type,offset,slots)
#define NATIVE_FIELD(id, group, key)
#include "symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
#undef NATIVE_FIELD
};
static const SymbolSpec kSymbolSpecs[]={
#define NATIVE_GROUP(id,name,registry,first,second)
#define NATIVE_CODE(id,group,key) {id,group,SK_CODE,key,nullptr,0,0,16},
#define NATIVE_DATA(id,group,key,bytes) {id,group,SK_DATA,key,nullptr,0,0,bytes},
#define NATIVE_SLOT(id,group,key,type,offset,slot) {id,group,SK_SLOT,key,type,offset,slot,0},
#define NATIVE_TABLE(id,group,key,type,offset,slots) {id,group,SK_TABLE,key,type,offset,slots,0},
#define NATIVE_FIELD(id, group, key)
#include "symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
#undef NATIVE_FIELD
};
struct FieldSpec {int id,group;const char* key;};
static const FieldSpec kFieldSpecs[]={
#define NATIVE_GROUP(id,name,registry,first,second)
#define NATIVE_CODE(id,group,key)
#define NATIVE_DATA(id,group,key,bytes)
#define NATIVE_SLOT(id,group,key,type,offset,slot)
#define NATIVE_TABLE(id,group,key,type,offset,slots)
#define NATIVE_FIELD(id,group,key) {id,group,key},
#include "symbol_catalog.h"
#undef NATIVE_GROUP
#undef NATIVE_CODE
#undef NATIVE_DATA
#undef NATIVE_SLOT
#undef NATIVE_TABLE
#undef NATIVE_FIELD
};
static_assert(sizeof(kGroupSpecs)/sizeof(kGroupSpecs[0])==NG_COUNT,"group catalog");
static_assert(sizeof(kSymbolSpecs)/sizeof(kSymbolSpecs[0])==NSY_COUNT,"symbol catalog");
static_assert(sizeof(kFieldSpecs)/sizeof(kFieldSpecs[0])==NFL_COUNT,"field catalog");
DWORD g_symbolValues[NSY_COUNT]={};
DWORD g_fieldValues[NFL_COUNT]={};
bool g_groupReady[NG_COUNT]={};
std::string g_groupReason[NG_COUNT];
std::map<std::pair<std::string,DWORD>,std::vector<DWORD>> g_rtti;
bool g_rttiBuilt=false;

void BuildRttiIndex() {
    if(g_rttiBuilt)return;
    g_rttiBuilt=true;g_rtti.clear();
    std::map<DWORD,std::pair<std::string,DWORD>> locators;
    for(const auto& s:g_sections) {
        if(s.flags&(IMAGE_SCN_MEM_WRITE|IMAGE_SCN_MEM_EXECUTE))continue;
        for(size_t i=0;i+24<=s.bytes;i+=4) {
            DWORD col[6];memcpy(col,g_file.data()+s.raw+i,24);
            if(col[0]!=1 || col[2] || col[5]!=s.rva+(DWORD)i || !FileAt(col[4],16) || col[3]>MAXDWORD-16)continue;
            std::string name;
            for(DWORD k=0;k<512;++k) {const BYTE* c=FileAt(col[3]+16+k,1);if(!c){name.clear();break;}if(!*c)break;name.push_back((char)*c);}
            if(name.size()<5 || name.compare(0,3,".?A"))continue;
            locators[col[5]]=std::make_pair(name,col[1]);
        }
    }
    for(const auto& s:g_sections) {
        if(s.flags&(IMAGE_SCN_MEM_WRITE|IMAGE_SCN_MEM_EXECUTE))continue;
        for(size_t i=0;i+16<=s.bytes;i+=8) {
            ULONGLONG col=0,fn=0;memcpy(&col,g_file.data()+s.raw+i,8);
            if(col<g_preferred || col-g_preferred>MAXDWORD)continue;
            auto it=locators.find((DWORD)(col-g_preferred));if(it==locators.end())continue;
            memcpy(&fn,g_file.data()+s.raw+i+8,8);
            if(fn<g_preferred || fn-g_preferred>MAXDWORD || !Execute((DWORD)(fn-g_preferred)))continue;
            g_rtti[it->second].push_back(s.rva+(DWORD)i+8);
        }
    }
}
const char* ResolveRttiTable(const SymbolSpec& spec,DWORD& table) {
    BuildRttiIndex();
    auto it=g_rtti.find(std::make_pair(std::string(spec.type),(DWORD)spec.offset));
    if(it==g_rtti.end() || it->second.empty())return "RTTI_TABLE_MISSING";
    if(it->second.size()!=1)return "RTTI_TABLE_AMBIGUOUS";
    table=it->second[0];
    unsigned count=spec.kind==SK_SLOT?spec.index+1:spec.index;
    for(unsigned slot=0;slot<count;++slot) {
        const BYTE* raw=FileAt(table+slot*8,8);ULONGLONG fn=0;
        if(!raw)return "RTTI_TABLE_RANGE";
        memcpy(&fn,raw,8);
        if(fn<g_preferred || fn-g_preferred>MAXDWORD || !Execute((DWORD)(fn-g_preferred)))return "RTTI_TABLE_TOO_SHORT";
    }
    if(!LoadedTable(table))return "RTTI_LOADED_TABLE_CHANGED";
    return nullptr;
}
const char* ResolveSymbol(const SymbolSpec& spec,const std::map<std::string,std::string>& fields,DWORD& value) {
    value=0;
    if(spec.kind==SK_TABLE || spec.kind==SK_SLOT) {
        DWORD table=0;const char* failure=ResolveRttiTable(spec,table);
        if(failure)return failure;
        if(spec.kind==SK_TABLE) {value=table;return nullptr;}
        ULONGLONG fn=0;uintptr_t loaded=0;memcpy(&fn,FileAt(table+spec.index*8,8),8);
        DWORD rva=(DWORD)(fn-g_preferred);
        if(!Ptr(g_base+table+spec.index*8,loaded) || loaded!=(uintptr_t)(g_base+rva))return "RTTI_LOADED_SLOT_CHANGED";
        if(!ScriptLoadedCode(rva,16,true))return "RTTI_SLOT_CODE_CHANGED";
        value=rva;return nullptr;
    }
    auto it=fields.find(spec.key);
    if(it==fields.end())return "PROFILE_KEY_MISSING";
    const std::string& text=it->second;size_t colon=text.find(':');DWORD rva=0;
    if(!ScriptNumber(text.substr(0,colon),g_imageSize,rva) || !rva)return "RVA_INVALID";
    if(spec.kind==SK_CODE) {
        if(colon==std::string::npos || text.size()-colon-1!=32 || !ScriptLoadedCode(rva,16,true))return "CODE_CHANGED";
        const BYTE* actual=FileAt(rva,16);const char* hex="0123456789abcdef";
        for(unsigned i=0;i<16;++i)if(text[colon+1+i*2]!=hex[actual[i]>>4] || text[colon+2+i*2]!=hex[actual[i]&15])return "FINGERPRINT_MISMATCH";
        value=rva;return nullptr;
    }
    if(colon!=std::string::npos)return "DATA_FORMAT";
    for(const auto& s:g_sections)if(rva>=s.rva && rva-s.rva<s.mapped && spec.bytes<=s.mapped-(rva-s.rva) && (s.flags&IMAGE_SCN_MEM_WRITE)) {value=rva;return nullptr;}
    return "DATA_SECTION_INVALID";
}
bool SymbolFields(const std::vector<BYTE>& bytes,std::map<std::string,std::string>& fields,std::string& reason) {
    if(bytes.empty() || bytes.size()>32768 || std::any_of(bytes.begin(),bytes.end(),[](BYTE c){return c==0 || c>127;})) {reason="SYMBOLS_PROFILE_ENCODING_OR_SIZE";return false;}
    size_t start=0;
    while(start<bytes.size()) {
        size_t end=start;while(end<bytes.size() && bytes[end]!='\n')++end;
        std::string line=Trim(std::string((const char*)bytes.data()+start,end-start));start=end+1;if(line.empty())continue;
        size_t equal=line.find('=');
        if(equal==std::string::npos || !fields.emplace(Trim(line.substr(0,equal)),Trim(line.substr(equal+1))).second) {reason="SYMBOLS_PROFILE_DUPLICATE_OR_SYNTAX";return false;}
    }
    std::set<std::string> expected={"schema","image_sha256","contract"};
    for(const auto& g:kGroupSpecs)expected.insert(std::string("approve.")+g.name);
    for(const auto& s:kSymbolSpecs)if(s.kind==SK_CODE || s.kind==SK_DATA)expected.insert(s.key);
    for(const auto& f:kFieldSpecs)expected.insert(std::string("field.")+f.key);
    if(fields.size()!=expected.size()) {reason="SYMBOLS_PROFILE_KEY_SET";return false;}
    for(const auto& key:expected)if(!fields.count(key)) {reason="SYMBOLS_PROFILE_KEY_SET";return false;}
    if(fields["schema"]!="1" || fields["image_sha256"]!=g_sha || fields["contract"]!="symbols_v2") {reason="SYMBOLS_PROFILE_IDENTITY_OR_SCHEMA";return false;}
    for(const auto& g:kGroupSpecs) {const std::string& v=fields[std::string("approve.")+g.name];if(v!="0" && v!="1") {reason="SYMBOLS_PROFILE_APPROVAL_VALUE";return false;}}
    return true;
}
void InitializeNativeSymbols() {
    memset(g_symbolValues,0,sizeof(g_symbolValues));memset(g_fieldValues,0,sizeof(g_fieldValues));
    for(int i=0;i<NG_COUNT;++i) {g_groupReady[i]=false;g_groupReason[i]="SYMBOLS_NOT_INITIALIZED";}
    std::vector<BYTE> bytes;std::wstring sha(g_sha.begin(),g_sha.end());std::string common;
    std::map<std::string,std::string> fields;
    if(!ReadFileBytes(g_root+L"\\hoi4plugins\\bindings\\"+sha+L".symbols",bytes,32768))common="SYMBOLS_PROFILE_MISSING";
    else SymbolFields(bytes,fields,common);
    if(!common.empty()) {for(int i=0;i<NG_COUNT;++i)g_groupReason[i]=common;return;}
    DWORD values[NSY_COUNT]={};std::string failure[NG_COUNT];
    for(const auto& spec:kSymbolSpecs) {
        if(fields[std::string("approve.")+kGroupSpecs[spec.group].name]!="1" || !failure[spec.group].empty())continue;
        const char* why=ResolveSymbol(spec,fields,values[spec.id]);
        if(why) {failure[spec.group]=std::string(spec.key)+":"+why;values[spec.id]=0;}
    }
    DWORD offsets[NFL_COUNT]={};
    for(const auto& spec:kFieldSpecs) {
        if(fields[std::string("approve.")+kGroupSpecs[spec.group].name]!="1" || !failure[spec.group].empty())continue;
        if(!ScriptNumber(fields[std::string("field.")+spec.key],NATIVE_FIELD_MAX,offsets[spec.id]) || !offsets[spec.id]) {
            failure[spec.group]=std::string("field.")+spec.key+":FIELD_INVALID";offsets[spec.id]=0;
        }
    }
    for(const auto& g:kGroupSpecs) {
        bool ready=false;std::string reason;
        if(fields[std::string("approve.")+g.name]!="1")reason="GROUP_NOT_APPROVED";
        else if(!failure[g.id].empty())reason="SYMBOL_"+failure[g.id];
        else if(g.first!=NG_NONE && !g_groupReady[g.first])reason=std::string("DEPENDENCY_")+kGroupSpecs[g.first].name;
        else if(g.second!=NG_NONE && !g_groupReady[g.second])reason=std::string("DEPENDENCY_")+kGroupSpecs[g.second].name;
        else if(g.registry && !g_scriptReady)reason="DEPENDENCY_SCRIPT_REGISTRY";
        else {ready=true;reason="READY_ADDRESS_AND_DECLARED_ABI_CONTRACT";}
        g_groupReady[g.id]=ready;g_groupReason[g.id]=reason;
    }
    for(const auto& spec:kSymbolSpecs)if(g_groupReady[spec.group])g_symbolValues[spec.id]=values[spec.id];
    for(const auto& spec:kFieldSpecs)if(g_groupReady[spec.group])g_fieldValues[spec.id]=offsets[spec.id];
}
