#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>
#include <stdio.h>
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
#define RVA_VALUE_VT 0x027915A0u
#define RVA_VALUE_ENTRY_VT 0x027A0BC0u
#define RVA_VALUE_FACTORY 0x003E6A70u
#define RVA_VARIABLE_VT 0x02799320u
#define RVA_VARIABLE_ENTRY_VT 0x0279FF90u
#define RVA_VARIABLE_FACTORY 0x003E3E10u

extern void Plugin_Log(const char* fmt, ...);
extern int Var64_ReadStoredContainerRaw(void* container, const char* name, long long* out);
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
static void Trigger_FreeString(unsigned char* value, unsigned char* img);

typedef struct TriggerTemplate {
    unsigned int vt, entryVt, factory, parse, eval;
    int slots;
} TriggerTemplate;

static int Trigger_Template(int kind, TriggerTemplate* out)
{
    static const TriggerTemplate templates[] = {
        {RVA_ALWAYS_VT, RVA_ALWAYS_ENTRY_VT, RVA_ALWAYS_FACTORY, RVA_ALWAYS_PARSE, RVA_ALWAYS_EVAL, 23},
        {RVA_VALUE_VT, RVA_VALUE_ENTRY_VT, RVA_VALUE_FACTORY, 0x013A2690u, 0x013A2180u, 26},
        {RVA_VARIABLE_VT, RVA_VARIABLE_ENTRY_VT, RVA_VARIABLE_FACTORY, 0x0054AE70u, 0x003D0BB0u, 23}
    };
    if (out == NULL || kind < 0 || kind > TRG_TEMPLATE_VARIABLE) return 0;
    *out = templates[kind];
    return 1;
}

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

void* Trigger_NewTypedInstance(TriggerDef* def)
{
    TriggerTemplate t;
    unsigned char* img = Trigger_Image();
    void* instance;
    if (img == NULL || def == NULL || !Trigger_Template(def->parameterTemplate, &t)
        || !ConsoleCmd_IsReadable(img + t.factory, 16)) return NULL;
    instance = ((GameFactoryFn)(img + t.factory))();
    if (instance != NULL) *(void**)instance = def->vtStorage + 1;
    return instance;
}

int Trigger_ScopeView(void* context, TriggerScopeView* out)
{
    unsigned char* img = Trigger_Image();
    typedef unsigned int (__fastcall *ScopeMaskFn)(void*);
    if (out == NULL) return 0;
    out->nativeContext = NULL; out->mask = 0;
    if (img == NULL || !ConsoleCmd_IsReadable(context, 176)
        || !ConsoleCmd_IsReadable(img + 0x00537D90u, 16)) return 0;
    out->nativeContext = context;
    out->mask = ((ScopeMaskFn)(img + 0x00537D90u))(context);
    return 1;
}

static int Trigger_HasTemporaryOperand(unsigned char* descriptor, void* context)
{
    unsigned char* img = Trigger_Image();
    unsigned char name[32] = {0};
    void* temporary;
    int found;
    struct NameView { const char* data; unsigned long long size; } view;
    typedef void* (__fastcall *TemporaryFn)(void);
    typedef void* (__fastcall *NameFn)(void*, void*, void*, void*);
    typedef unsigned char (__fastcall *ContainsFn)(void*, void*);
    if (descriptor[14]) return 1;
    if (*(int*)(descriptor + 100) != 0) return 0;
    temporary = ((TemporaryFn)(img + 0x0054F730u))();
    if (temporary == NULL) return 0;
    ((NameFn)(img + 0x005454A0u))(descriptor, name, context, *(void**)(descriptor + 160));
    view.data = *(unsigned long long*)(name + 24) <= 15 ? (const char*)name : *(const char**)name;
    view.size = *(unsigned long long*)(name + 16);
    found = ((ContainsFn)(img + 0x00BC8D20u))(temporary, &view) != 0;
    Trigger_FreeString(name, img);
    return found;
}

static int Trigger_HasDynamicBinding(void* container, const char* name, size_t length)
{
    unsigned char* map;
    unsigned char* buckets;
    unsigned char* node;
    void* sentinel;
    void* last;
    unsigned long long mask;
    unsigned int hash = 2166136261u;
    size_t i;
    if (!ConsoleCmd_IsReadable(container, 56)) return 1;
    map = *(unsigned char**)((unsigned char*)container + 48);
    if (map == NULL) return 0;
    if (!ConsoleCmd_IsReadable(map, 56)) return 1;
    sentinel = *(void**)(map + 8);
    buckets = *(unsigned char**)(map + 24);
    mask = *(unsigned long long*)(map + 48);
    if (buckets == NULL || mask > 0x100000) return 1;
    for (i = 0; i < length; ++i) hash = (hash ^ (unsigned char)name[i]) * 16777619u;
    buckets += 16 * (hash & mask);
    if (!ConsoleCmd_IsReadable(buckets, 16)) return 1;
    last = *(void**)buckets; node = *(unsigned char**)(buckets + 8);
    for (i = 0; i < 65536; ++i) {
        unsigned char* text;
        unsigned long long size, cap;
        if (node == sentinel) return 0;
        if (!ConsoleCmd_IsReadable(node, 112)) return 1;
        size = *(unsigned long long*)(node + 32); cap = *(unsigned long long*)(node + 40);
        text = cap <= 15 ? node + 16 : *(unsigned char**)(node + 16);
        if (size == length && ConsoleCmd_IsReadable(text, length) && memcmp(text, name, length) == 0) return 1;
        if (node == last) return 0;
        node = *(unsigned char**)(node + 8);
    }
    return 1;
}

int Trigger_ReadRawParameter(void* self, const TriggerScopeView* scope, unsigned int offset, long long* out)
{
    unsigned char* img = Trigger_Image();
    unsigned char* descriptor;
    typedef long long* (__fastcall *ParamFn)(void*, long long*, void*, void*, unsigned char);
    typedef void* (__fastcall *ContainerFn)(void*, void*, int*, int*, void**, void**, void**, void**, void**, void**);
    if (img == NULL || self == NULL || scope == NULL || scope->nativeContext == NULL || out == NULL) return 0;
    if (offset != 88u && offset != 96u && offset != 296u) return 0;
    descriptor = (unsigned char*)self + offset;
    if (!ConsoleCmd_IsReadable(descriptor, 208) || !descriptor[8]) return 0;
    if (!descriptor[9] && !descriptor[10] && !descriptor[11] && *(void**)(descriptor + 144) == NULL
        && *(void**)(descriptor + 160) == NULL && *(void**)(descriptor + 168) == NULL
        && !Trigger_HasTemporaryOperand(descriptor, scope->nativeContext)) {
        unsigned char* text = descriptor + 112;
        unsigned long long size = *(unsigned long long*)(text + 16);
        unsigned long long cap = *(unsigned long long*)(text + 24);
        const char* name = cap <= 15 ? (const char*)text : *(const char**)text;
        if (size > 0 && size <= 33 && size <= cap && ConsoleCmd_IsReadable(name, (size_t)size + 1)
            && name[size] == 0 && memchr(name, 0, (size_t)size) == NULL) {
            int a = 0, b = 0;
            void* extra[6] = {0};
            void* container = ((ContainerFn)(img + 0x00542500u))(descriptor, scope->nativeContext,
                &a, &b, &extra[0], &extra[1], &extra[2], &extra[3], &extra[4], &extra[5]);
            if (!Trigger_HasDynamicBinding(container, name, (size_t)size)
                && Var64_ReadStoredContainerRaw(container, name, out)) return 1;
        }
    }
    *out = 0;
    ((ParamFn)(img + 0x00544C90u))(descriptor, out, scope->nativeContext, NULL, 0);
    return 1;
}

int Trigger_CompareRaw(long long left, long long right, int token)
{
    switch (token) {
        case 467: return left > right;
        case 468: return left < right;
        case 14578: return left != right;
        case 14579: return left <= right;
        case 14580: return left == right;
        case 14581: return left >= right;
        default: return 0;
    }
}

unsigned char Trigger_EvaluateValue(void* self, void* scope, TriggerValueFn value)
{
    TriggerScopeView view;
    long long rhs;
    int token;
    if (value == NULL || !ConsoleCmd_IsReadable(self, 304) || !Trigger_ScopeView(scope, &view)
        || !Trigger_ReadRawParameter(self, &view, 96u, &rhs)) return 0;
    token = *(int*)((unsigned char*)self + 88);
    if (token != 467 && token != 468) return 0;
    return (unsigned char)Trigger_CompareRaw(value(self, &view), rhs, token);
}

unsigned char __fastcall Trigger_EvaluateVariable(void* self, void* scope)
{
    TriggerScopeView view;
    long long lhs, rhs;
    if (!ConsoleCmd_IsReadable(self, 544) || !Trigger_ScopeView(scope, &view)
        || !Trigger_ReadRawParameter(self, &view, 88u, &lhs)
        || !Trigger_ReadRawParameter(self, &view, 296u, &rhs)) return 0;
    return (unsigned char)Trigger_CompareRaw(lhs, rhs, *(int*)((unsigned char*)self + 504));
}

void* Trigger_TypedTooltip(TriggerDef* def, void* self, void* out, void* ctx, unsigned char invert, int indent)
{
    unsigned char* img = Trigger_Image();
    TriggerScopeView view;
    long long left = 0, right = 0;
    int token = 0, valid = 0, actual = 0, i;
    unsigned int lhsOffset = 88u, rhsOffset = 296u;
    char lhs[48] = "?", rhs[48] = "?";
    unsigned char params[4][104], packed[32] = {0}, resultPacked[32] = {0}, resultText[32] = {0};
    const char* op = "?";
    const char* names[] = {"LEFT", "COMPARISON", "RIGHT", "RESULT"};
    const char* texts[4];
    typedef void (__fastcall *ParamLifeFn)(void*);
    typedef void* (__fastcall *StringCtorFn)(void*, const void*, size_t);
    typedef long long* (__fastcall *ValueGetterFn)(void*, long long*, void*);
    (void)indent;
    if (img == NULL || def == NULL || out == NULL || ctx == NULL || def->locKey == NULL) return out;
    if (def->parameterTemplate != TRG_TEMPLATE_VALUE && def->parameterTemplate != TRG_TEMPLATE_VARIABLE) return out;
    if (def->parameterTemplate == TRG_TEMPLATE_VALUE) { lhsOffset = 96u; rhsOffset = 96u; }
    if (ConsoleCmd_IsReadable(self, def->parameterTemplate == TRG_TEMPLATE_VALUE ? 304 : 544))
        token = *(int*)((unsigned char*)self + (def->parameterTemplate == TRG_TEMPLATE_VALUE ? 88 : 504));
    if (ConsoleCmd_IsReadable(self, def->parameterTemplate == TRG_TEMPLATE_VALUE ? 304 : 544)
        && Trigger_ScopeView(ctx, &view)
        && !*((unsigned char*)self + lhsOffset + 11) && !*((unsigned char*)self + rhsOffset + 11)) {
        if (def->parameterTemplate == TRG_TEMPLATE_VALUE) {
            token = *(int*)((unsigned char*)self + 88);
            if (def->valueGetter != NULL && (token == 467 || token == 468)
                && Trigger_ReadRawParameter(self, &view, 96u, &right)) {
                ((ValueGetterFn)def->valueGetter)(self, &left, ctx);
                valid = 1;
            }
        } else {
            token = *(int*)((unsigned char*)self + 504);
            if(def->operandReader!=NULL)valid=def->operandReader(self,&view,88u,&left)&&def->operandReader(self,&view,296u,&right);
            else valid = Trigger_ReadRawParameter(self, &view, 88u, &left)
                && Trigger_ReadRawParameter(self, &view, 296u, &right);
        }
    }
    switch (token) {
        case 467: op = invert ? "<=" : ">"; break;
        case 468: op = invert ? ">=" : "<"; break;
        case 14578: op = invert ? "==" : "!="; break;
        case 14579: op = invert ? ">" : "<="; break;
        case 14580: op = invert ? "!=" : "=="; break;
        case 14581: op = invert ? "<" : ">="; break;
        default: valid = 0; break;
    }
    if (valid) {
        Trigger_FormatRaw(left, lhs, sizeof(lhs));
        Trigger_FormatRaw(right, rhs, sizeof(rhs));
        actual = Trigger_CompareRaw(left, right, token) != (invert != 0);
    }
    ((PackFn)(img + RVA_PACK_KEY))(resultPacked,
        valid ? (actual ? "PLUGIN_TRIGGER_RESULT_TRUE" : "PLUGIN_TRIGGER_RESULT_FALSE") : "PLUGIN_TRIGGER_RESULT_UNAVAILABLE", NULL, 0);
    ((FormatFn)(img + RVA_FORMAT_TEXT))(resultText, ctx, resultPacked);
    texts[0] = lhs; texts[1] = op; texts[2] = rhs;
    texts[3] = *(unsigned long long*)(resultText + 24) <= 15 ? (const char*)resultText : *(const char**)resultText;
    for (i = 0; i < 4; ++i) {
        ((ParamLifeFn)(img + 0x0029DAD0u))(params[i]);
        *(int*)params[i] = 1;
        *(const char**)(params[i] + 8) = names[i];
        ((StringCtorFn)(img + 0x0011D970u))(params[i] + 48, texts[i], strlen(texts[i]));
    }
    ((PackFn)(img + RVA_PACK_KEY))(packed, def->locKey, params, 4);
    for (i = 0; i < 4; ++i) ((ParamLifeFn)(img + 0x0029DFE0u))(params[i]);
    ((FormatFn)(img + RVA_FORMAT_TEXT))(out, ctx, packed);
    ((AppendFn)(img + RVA_APPEND_TEXT))(out, "\n", 1);
    Trigger_FreeString(packed, img);
    Trigger_FreeString(resultText, img);
    Trigger_FreeString(resultPacked, img);
    return out;
}

int Trigger_FormatRaw(long long raw, char* out, size_t capacity)
{
    unsigned long long magnitude = raw < 0 ? 0ULL - (unsigned long long)raw : (unsigned long long)raw;
    unsigned long long fraction = magnitude % 100000ULL;
    size_t n;
    if (out == NULL || capacity < 24) return 0;
    if (fraction == 0) _snprintf_s(out, capacity, _TRUNCATE, "%s%llu", raw < 0 ? "-" : "", magnitude / 100000ULL);
    else {
        _snprintf_s(out, capacity, _TRUNCATE, "%s%llu.%05llu", raw < 0 ? "-" : "", magnitude / 100000ULL, fraction);
        n = strlen(out);
        while (n > 0 && out[n - 1] == '0') out[--n] = 0;
    }
    return 1;
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
    TriggerTemplate t;
    unsigned char* img;
    void* map;
    int id;
    int i;
    struct NameView { const char* data; unsigned long long size; } view;
    unsigned char* entry;
    if (def == NULL) return 0;
    if (!Trigger_ValidName(def->name) || def->desc == NULL || def->locKey == NULL
        || def->eval == NULL || def->factory == NULL || def->tooltip == NULL
        || !Trigger_Template(def->parameterTemplate, &t)
        || (def->parameterTemplate == TRG_TEMPLATE_VALUE && def->valueGetter == NULL)) {
        def->state = TRG_STATE_FAILED;
        return 0;
    }
    if (!Trigger_RegistryReady()) return 0;
    img = Trigger_Image();
    map = *(void**)(img + RVA_TRIGGER_MAP);
    if (def->state == TRG_STATE_OK)
        return Trigger_FindEntry(map, def->tokenId) == def->entry;
    if (!ConsoleCmd_IsReadable(img + t.vt - 8, (size_t)(t.slots + 1) * 8)
        || !ConsoleCmd_IsReadable(img + t.entryVt - 8, 24)
        || *(void**)(img + t.vt + 4 * 8) != img + t.parse
        || *(void**)(img + t.vt + TRG_VT_EVAL * 8) != img + t.eval
        || *(void**)(img + t.entryVt + 8) != img + t.factory) {
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
    for (i = 0; i < t.slots + 1; ++i)
        def->vtStorage[i] = *(void**)(img + t.vt - 8 + (size_t)i * 8);
    def->vtStorage[1 + TRG_VT_EVAL] = (void*)def->eval;
    def->vtStorage[1 + TRG_VT_TOOLTIP] = (void*)def->tooltip;
    if (def->parameterTemplate == TRG_TEMPLATE_VALUE) def->vtStorage[1 + 23] = def->valueGetter;
    def->entryVtStorage[0] = *(void**)(img + t.entryVt - 8);
    def->entryVtStorage[1] = *(void**)(img + t.entryVt);
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
