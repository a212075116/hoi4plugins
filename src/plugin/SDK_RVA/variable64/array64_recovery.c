#include "array64_existing_transaction.c"

typedef struct {
    unsigned long long magic, owner, checksum;
    void* container;
    int length, generation, consumed;
    char name[21];
    long long parts[4096][3];
} Array64Snapshot;

unsigned int Array64_SnapshotBytes(void) { return (unsigned int)sizeof(Array64Snapshot); }

static unsigned long long ar_hash(const Array64Snapshot* s)
{
    unsigned long long h = 14695981039346656037ull, values[4];
    unsigned int i, j;
    values[0] = s->owner; values[1] = (unsigned long long)s->container;
    values[2] = (unsigned int)s->length; values[3] = (unsigned int)s->generation;
    for (i = 0; i < 4; ++i) for (j = 0; j < 8; ++j) h = (h ^ ((values[i] >> (8*j)) & 255)) * 1099511628211ull;
    for (i = 0; i < 21; ++i) h = (h ^ (unsigned char)s->name[i]) * 1099511628211ull;
    for (i = 0; i < (unsigned int)s->length; ++i) for (j = 0; j < 3; ++j) {
        unsigned long long v = (unsigned long long)s->parts[i][j];
        unsigned int k;
        for (k = 0; k < 8; ++k) h = (h ^ ((v >> (k*8)) & 255)) * 1099511628211ull;
    }
    return h;
}

static int ar_valid_parts(const long long* p)
{
    long long low, high, flags;
    if (!p[2]) return p[1] == 0 && p[0] > -214748364800000LL && p[0] < 214748364800000LL;
    if (p[2] < 100000 || p[2] > 400000 || p[2] % 100000 || p[0] % 100000 || p[1] % 100000) return 0;
    low = p[0]/100000; high = p[1]/100000; flags = p[2]/100000-1;
    return low >= -2147483647LL && low <= 2147483647LL && high >= -2147483647LL && high <= 2147483647LL &&
        (!(flags & 1) || low == 0) && (!(flags & 2) || high == 0);
}

int Array64_Capture(void* container, const char* name, int expected_generation,
    unsigned long long owner, Array64Snapshot* snapshot)
{
    char roots[6][40], key[48];
    long long value;
    int length, gen, status, i, j;
    if (!snapshot) return -1;
    snapshot->magic = 0;
    if (!owner || !ag_name(name, roots)) return -1;
    status = Array64Group_Read(container, name, -1, expected_generation, &value, &length, &gen);
    if (status != 2 || gen > 2147483644) return -1;
    snapshot->container = container; snapshot->owner = owner; snapshot->length = length;
    snapshot->generation = gen; snapshot->consumed = 0;
    for (i = 0; i < 21; ++i) snapshot->name[i] = 0;
    for (i = 0; name[i]; ++i) snapshot->name[i] = name[i];
    for (i = 0; i < length; ++i) for (j = 0; j < 3; ++j) {
        tx_element_key(key, roots[3+j], i);
        if (na_lookup(container, key, &snapshot->parts[i][j]) != 1) return -1;
    }
    snapshot->checksum = ar_hash(snapshot); snapshot->magic = 0x3250414e53343641ull;
    return 1;
}

int Array64_InspectQuarantine(void* container, const char* name, int* length, int* odd_generation)
{
    char roots[6][40], key[48];
    long long ver, gen, len, count;
    int owned, i;
    if (!length || !odd_generation || !ag_name(name, roots)) return -1;
    if (na_lookup(container, roots[0], &ver) != 1 || ver != 200000 ||
        na_lookup(container, roots[1], &gen) != 1 || gen < 100000 || gen % 100000 || gen/100000 > 2147483645LL ||
        !(gen/100000 % 2) || na_lookup(container, roots[2], &len) != 1 || len < 0 || len % 100000 || len/100000 > 4096) return -1;
    if (!ag_inventory(container, roots, &owned) || owned != 6 + 3*(int)(len/100000)) return -2;
    for (i = 0; i < 3; ++i) {
        unsigned int k = 0;
        while (roots[3+i][k]) { key[k] = roots[3+i][k]; ++k; }
        key[k++] = '^'; key[k++] = 'n'; key[k++] = 'u'; key[k++] = 'm'; key[k] = 0;
        if (na_lookup(container, key, &count) != 1 || count != len) return -2;
    }
    for (i = 0; i < (int)(len/100000); ++i) for (int j = 0; j < 3; ++j) {
        tx_element_key(key, roots[3+j], i);
        if (na_lookup(container, key, &count) != 1) return -2;
    }
    *length = (int)(len/100000); *odd_generation = (int)(gen/100000);
    return 1;
}

int Array64_Recover(void* container, const char* name, unsigned long long owner,
    Array64Snapshot* snapshot, int fail_stage)
{
    char roots[6][40], key[48];
    int length, odd, stage = 0, i, j, status;
    long long raw;
    if (!snapshot || snapshot->magic != 0x3250414e53343641ull || snapshot->consumed || !owner ||
        snapshot->owner != owner || snapshot->container != container || snapshot->length < 0 || snapshot->length > 4096 ||
        snapshot->generation < 0 || snapshot->generation > 2147483644 || snapshot->generation % 2 ||
        snapshot->name[20] != 0 || !ag_name(name, roots) || fail_stage < 0 || fail_stage > 3*snapshot->length+1) return -1;
    for (i = 0; i < 21; ++i) {
        if (snapshot->name[i] != name[i]) return -1;
        if (!name[i]) break;
    }
    if (snapshot->checksum != ar_hash(snapshot)) return -1;
    for (i = 0; i < snapshot->length; ++i) if (!ar_valid_parts(snapshot->parts[i])) return -1;
    status = Array64_InspectQuarantine(container, name, &length, &odd);
    if (status != 1 || length != snapshot->length || odd != snapshot->generation+1) return -2;
    for (i = 0; i < length; ++i) for (j = 0; j < 3; ++j) {
        if (++stage == fail_stage) return -3;
        tx_element_key(key, roots[3+j], i);
        if (!tx_put(container, key, snapshot->parts[i][j])) return -3;
    }
    if (++stage == fail_stage) return -3;
    if (!tx_put(container, roots[1], (odd+1LL)*100000)) {
        if (!tx_put(container, roots[1], odd*100000LL)) return -4;
        return -3;
    }
    status = Array64Group_Read(container, name, -1, odd+1, &raw, &length, &i);
    if (status != 2 || length != snapshot->length) {
        if (!tx_put(container, roots[1], odd*100000LL)) return -4;
        return -3;
    }
    snapshot->consumed = 1;
    return 1;
}
