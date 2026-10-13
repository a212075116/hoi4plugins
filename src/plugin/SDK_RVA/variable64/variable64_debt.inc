#define VAR64_DEBT_INITIAL_CAPACITY 64

typedef struct {
    char      name[40];
    void*     container;
    long long debtInt;
    long long debtFrac;
    int       active;
} Var64DebtRecord;

static Var64DebtRecord* g_var64Debts = NULL;
static int g_var64DebtCapacity = 0;

static Var64DebtRecord* Var64_FindDebt(void* self, void* ctx, const char* name)
{
    int i;
    void* container;

    if (name == NULL || g_var64DebtCapacity == 0) return NULL;
    container = Var64_Container(self, ctx);
    if (container == NULL) return NULL;
    for (i = 0; i < g_var64DebtCapacity; ++i) {
        if (g_var64Debts[i].active && g_var64Debts[i].container == container
            && strcmp(g_var64Debts[i].name, name) == 0) {
            return &g_var64Debts[i];
        }
    }
    return NULL;
}

static Var64DebtRecord* Var64_NewDebt(void* self, void* ctx, const char* name)
{
    int i;
    void* container = Var64_Container(self, ctx);
    Var64DebtRecord* grown;
    int capacity;
    if (name == NULL || container == NULL) return NULL;
    for (i = 0; i < g_var64DebtCapacity; ++i) {
        if (!g_var64Debts[i].active) break;
    }
    if (i == g_var64DebtCapacity) {
        capacity = g_var64DebtCapacity == 0 ? VAR64_DEBT_INITIAL_CAPACITY : g_var64DebtCapacity * 2;
        grown = g_var64Debts == NULL
            ? (Var64DebtRecord*)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, capacity * sizeof(*grown))
            : (Var64DebtRecord*)HeapReAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, g_var64Debts, capacity * sizeof(*grown));
        if (grown == NULL) { Plugin_Log("[var64] cannot allocate debt record [%s]", name); return NULL; }
        g_var64Debts = grown;
        g_var64DebtCapacity = capacity;
    }
    g_var64Debts[i].active = 1;
    strcpy_s(g_var64Debts[i].name, sizeof(g_var64Debts[i].name), name);
    g_var64Debts[i].container = container;
    g_var64Debts[i].debtInt = 0;
    g_var64Debts[i].debtFrac = 0;
    return &g_var64Debts[i];
}

static void Var64_ClearDebt(Var64DebtRecord* rec)
{
    if (rec == NULL) return;
    rec->active = 0;
    rec->name[0] = 0;
    rec->debtInt = 0;
    rec->debtFrac = 0;
}

static void Var64_ResetDebtForSet(void* self, void* ctx, const char* name)
{
    Var64_ClearDebt(Var64_FindDebt(self, ctx, name));
}

