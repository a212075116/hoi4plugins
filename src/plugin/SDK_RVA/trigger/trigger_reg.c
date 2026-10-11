#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>
#include "console_cmd.h"
#include "trigger_reg.h"

#define RVA_TRIGGER_MAP 0x03330050u
#define RVA_REGISTER_TRIGGER 0x00550970u
#define RVA_ALWAYS_VT 0x0278A3A0u
#define RVA_ALWAYS_ENTRY_VT 0x027A14D8u
#define RVA_ALWAYS_FACTORY 0x003E32B0u
#define RVA_ALWAYS_PARSE 0x013A2430u
#define RVA_ALWAYS_EVAL 0x003CFD80u
#define RVA_GAME_ALLOC 0x021C9AF0u
#define RVA_GAME_FREE 0x021C9B00u
#define RVA_ADD_TOKEN 0x024BB460u
#define RVA_LEXER_INIT 0x035E1AB0u
#define RVA_LEXER_SYNC 0x035E1AB1u
#define RVA_STATIC_TOKENS 0x0338D170u
#define STATIC_TOKEN_COUNT 10765
#define RVA_DYNAMIC_TOKENS 0x035E1AC0u
#define RVA_DYNAMIC_COUNT 0x035E1ACCu
#define RVA_PACK_KEY 0x02245E60u
#define RVA_FORMAT_TEXT 0x010E48A0u
#define RVA_APPEND_TEXT 0x00129C10u

extern void Plugin_Log(const char* fmt, ...);
typedef void* (__fastcall *GameAllocFn)(size_t);
typedef void (__fastcall *GameFreeFn)(void*);
typedef void* (__fastcall *GameFactoryFn)(void);
typedef void* (__fastcall *AddTokenFn)(int*, void*, void*);
typedef void* (__fastcall *RegisterFn)(void*, int, void*);
typedef void* (__fastcall *PackFn)(void*, const char*, void*, int);
typedef void* (__fastcall *FormatFn)(void*, void*, void*);
typedef void* (__fastcall *AppendFn)(void*, const char*, size_t);
typedef char trigger_pointer_size_check[(sizeof(void*) == 8) ? 1 : -1];

static int g_triggerCount = 0;

static unsigned char* Trigger_Image(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

int Trigger_ValidName(const char* name)
{
    size_t i;
    if (name == NULL || name[0] == 0) return 0;
    if (!(name[0] == '_' || (name[0] >= 'a' && name[0] <= 'z'))) return 0;
    for (i = 0; name[i] != 0; ++i) {
        if (i >= 63) return 0;
        if (!(name[i] == '_' || (name[i] >= 'a' && name[i] <= 'z')
              || (name[i] >= '0' && name[i] <= '9'))) return 0;
    }
    return 1;
}

int Trigger_RegistryReady(void)
{
    unsigned char* img = Trigger_Image();
    unsigned char* map;
    void* head;
    if (img == NULL || !ConsoleCmd_IsReadable(img + RVA_LEXER_INIT, 2)) return 0;
    if (!img[RVA_LEXER_INIT] || !img[RVA_LEXER_SYNC]) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_TRIGGER_MAP, sizeof(void*))) return 0;
    map = *(unsigned char**)(img + RVA_TRIGGER_MAP);
    if (map == NULL || !ConsoleCmd_IsReadable(map + 24, 16)) return 0;
    head = *(void**)(map + 24);
    return head != NULL && ConsoleCmd_IsReadable(head, 48);
}

static void* Trigger_FindEntry(void* object, int id)
{
    unsigned char* head;
    unsigned char* node;
    int guard;
    if (object == NULL || !ConsoleCmd_IsReadable((unsigned char*)object + 24, 8)) return NULL;
    head = *(unsigned char**)((unsigned char*)object + 24);
    if (head == NULL || !ConsoleCmd_IsReadable(head, 48)) return NULL;
    node = *(unsigned char**)(head + 8);
    for (guard = 0; guard < 65536; ++guard) {
        int key;
        if (node == NULL || !ConsoleCmd_IsReadable(node, 48) || node[25] != 0) return NULL;
        key = *(int*)(node + 32);
        if (id == key) return *(void**)(node + 40);
        node = *(unsigned char**)(node + (id < key ? 0 : 16));
    }
    return NULL;
}

static int Trigger_StaticTokenId(int id)
{
    unsigned char* img = Trigger_Image();
    int i;
    if (img == NULL || id == 0) return 0;
    if (!ConsoleCmd_IsReadable(img + RVA_STATIC_TOKENS, (size_t)STATIC_TOKEN_COUNT * 72)) return 1;
    for (i = 0; i < STATIC_TOKEN_COUNT; ++i) {
        unsigned char* item = img + RVA_STATIC_TOKENS + (size_t)i * 72;
        if (*(int*)item == id) return 1;
    }
    return 0;
}

void* Trigger_NewInstance(void* vt)
{
    unsigned char* img = Trigger_Image();
    void* instance;
    if (img == NULL || vt == NULL || !ConsoleCmd_IsReadable(img + RVA_ALWAYS_FACTORY, 16)) return NULL;
    instance = ((GameFactoryFn)(img + RVA_ALWAYS_FACTORY))();
    if (instance != NULL) *(void**)instance = vt;
    return instance;
}

int Trigger_ParamBool(void* self)
{
    if (self == NULL || !ConsoleCmd_IsReadable((unsigned char*)self + TRG_PARAM_BOOL_OFFSET, 1)) return 0;
    return *((unsigned char*)self + TRG_PARAM_BOOL_OFFSET) != 0;
}

unsigned char Trigger_EvaluateBool(void* self, void* scope, TriggerPredicateFn predicate)
{
    if (self == NULL || predicate == NULL) return 0;
    return (unsigned char)((predicate(self, scope) != 0) == Trigger_ParamBool(self));
}

static void Trigger_FreeString(unsigned char* value, unsigned char* img)
{
    unsigned long long cap = *(unsigned long long*)(value + 24);
    unsigned char* p;
    if (cap <= 15) return;
    p = *(unsigned char**)value;
    if (p == NULL) return;
    if (cap + 1 >= 0x1000) {
        unsigned char* base;
        if (!ConsoleCmd_IsReadable(p - 8, 8)) return;
        base = *(unsigned char**)(p - 8);
        if (base == NULL || p < base + 8 || (size_t)(p - base - 8) > 0x1F) return;
        p = base;
    }
    ((GameFreeFn)(img + RVA_GAME_FREE))(p);
}

void* Trigger_BuildTooltip(void* self, void* out, void* ctx,
                          unsigned char inverted, const char* locKey)
{
    unsigned char* img = Trigger_Image();
    unsigned char packed[32];
    const char* suffix;
    if (img == NULL || out == NULL || ctx == NULL || locKey == NULL) return out;
    if (!ConsoleCmd_IsReadable(img + RVA_FORMAT_TEXT, 16)) return out;
    memset(packed, 0, sizeof(packed));
    ((PackFn)(img + RVA_PACK_KEY))(packed, locKey, NULL, 0);
    ((FormatFn)(img + RVA_FORMAT_TEXT))(out, ctx, packed);
    suffix = Trigger_ParamBool(self) != (inverted != 0) ? " = yes\n" : " = no\n";
    ((AppendFn)(img + RVA_APPEND_TEXT))(out, suffix, strlen(suffix));
    Trigger_FreeString(packed, img);
    return out;
}

int Trigger_RegistryRegister(TriggerDef* def)
{
    unsigned char* img;
    void* map;
    int id;
    int i;
    struct NameView { const char* data; unsigned long long size; } view;
    unsigned char* entry;
    if (def == NULL) return 0;
    if (!Trigger_ValidName(def->name) || def->desc == NULL || def->locKey == NULL
        || def->eval == NULL || def->factory == NULL || def->tooltip == NULL) {
        def->state = TRG_STATE_FAILED;
        return 0;
    }
    if (!Trigger_RegistryReady()) return 0;
    img = Trigger_Image();
    map = *(void**)(img + RVA_TRIGGER_MAP);
    if (def->state == TRG_STATE_OK)
        return Trigger_FindEntry(map, def->tokenId) == def->entry;
    if (*(void**)(img + RVA_ALWAYS_VT + 4 * 8) != img + RVA_ALWAYS_PARSE
        || *(void**)(img + RVA_ALWAYS_VT + TRG_VT_EVAL * 8) != img + RVA_ALWAYS_EVAL
        || *(void**)(img + RVA_ALWAYS_ENTRY_VT + 8) != img + RVA_ALWAYS_FACTORY) {
        def->state = TRG_STATE_FAILED;
        return 0;
    }
    id = 0;
    view.data = def->name;
    view.size = strlen(def->name);
    ((AddTokenFn)(img + RVA_ADD_TOKEN))(&id, &view, NULL);
    if (id != 0 && (Trigger_StaticTokenId(id) || Trigger_FindEntry(map, id) != NULL)) {
        def->state = TRG_STATE_FAILED;
        Plugin_Log("[trg] collision rejected: %s", def->name);
        return 0;
    }
    if (id == 0) { def->state = TRG_STATE_FAILED; return 0; }
    for (i = 0; i < TRG_VT_SLOTS + 1; ++i)
        def->vtStorage[i] = *(void**)(img + RVA_ALWAYS_VT - 8 + (size_t)i * 8);
    def->vtStorage[1 + TRG_VT_EVAL] = (void*)def->eval;
    def->vtStorage[1 + TRG_VT_TOOLTIP] = (void*)def->tooltip;
    def->entryVtStorage[0] = *(void**)(img + RVA_ALWAYS_ENTRY_VT - 8);
    def->entryVtStorage[1] = *(void**)(img + RVA_ALWAYS_ENTRY_VT);
    def->entryVtStorage[2] = (void*)def->factory;
    entry = (unsigned char*)((GameAllocFn)(img + RVA_GAME_ALLOC))(24);
    if (entry == NULL) { def->state = TRG_STATE_FAILED; return 0; }
    memset(entry, 0, 24);
    *(void**)entry = def->entryVtStorage + 1;
    *(const char**)(entry + 8) = def->desc;
    entry[16] = 1;
    ((RegisterFn)(img + RVA_REGISTER_TRIGGER))(map, id, entry);
    if (Trigger_FindEntry(map, id) != entry) {
        def->state = TRG_STATE_FAILED;
        return 0;
    }
    def->entry = entry;
    def->tokenId = id;
    def->state = TRG_STATE_OK;
    ++g_triggerCount;
    Plugin_Log("[trg] + %s tokenId=%d entry=%p eval=%p", def->name, id, entry, (void*)def->eval);
    return 1;
}

int Trigger_RegistryRegisterAll(TriggerDef** defs, int count)
{
    int i, registered = 0;
    if (defs == NULL || count <= 0 || !Trigger_RegistryReady()) return 0;
    for (i = 0; i < count; ++i) if (Trigger_RegistryRegister(defs[i])) ++registered;
    return registered;
}

int Trigger_RegistryRegisteredCount(void)
{
    return g_triggerCount;
}
