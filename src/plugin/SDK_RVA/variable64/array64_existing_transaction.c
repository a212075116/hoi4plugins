#include "array64_group_readonly.c"

extern int tx_write_existing(void* container, const char* key, long long raw);

static void tx_element_key(char* output, const char* base, int index)
{
    char reverse[12];
    unsigned int n = 0, digits = 0, i;
    while (base[n]) { output[n] = base[n]; ++n; }
    output[n++] = '^';
    do { reverse[digits++] = (char)('0' + index % 10); index /= 10; } while (index);
    for (i = 0; i < digits; ++i) output[n++] = reverse[digits - 1 - i];
    output[n] = 0;
}

static int tx_put(void* container, const char* key, long long raw)
{
    long long current;
    if (na_lookup(container, key, &current) != 1) return 0;
    if (!tx_write_existing(container, key, raw)) return 0;
    return na_lookup(container, key, &current) == 1 && current == raw;
}

int Array64_SetExisting(void* container, const char* name, int index, int expected_generation,
    long long raw, int wide, int fail_stage, int fail_rollback)
{
    char roots[6][40], keys[3][48];
    long long baseline[3], next[3], original, observed;
    int count, gen, i, stage, status, restored = 1;
    if ((wide != 0 && wide != 1) || fail_stage < 0 || fail_stage > 5 || fail_rollback < 0 || fail_rollback > 4) return -1;
    status = Array64Group_Read(container, name, index, expected_generation, &original, &count, &gen);
    if (status != 1 || gen > 2147483644) return -1;
    if (!ag_name(name, roots)) return -1;
    for (i = 0; i < 3; ++i) {
        tx_element_key(keys[i], roots[3+i], index);
        if (na_lookup(container, keys[i], &baseline[i]) != 1) return -1;
    }
    if (wide) {
        unsigned long long bits = (unsigned long long)raw;
        long long lo = (long long)(bits & 4294967295ull), hi = (long long)(bits >> 32);
        int flags = 0;
        if (lo >= 2147483648LL) lo -= 4294967296LL;
        if (hi >= 2147483648LL) hi -= 4294967296LL;
        if (lo == -2147483648LL) { lo = 0; flags |= 1; }
        if (hi == -2147483648LL) { hi = 0; flags |= 2; }
        next[0] = lo * 100000; next[1] = hi * 100000; next[2] = (1 + flags) * 100000;
    } else {
        if (raw <= -214748364800000LL || raw >= 214748364800000LL) return -1;
        next[0] = raw; next[1] = 0; next[2] = 0;
    }
    for (stage = 1; stage <= 5; ++stage) {
        if (stage == fail_stage) goto compensate;
        if (stage == 1) status = tx_put(container, roots[1], (gen + 1LL) * 100000);
        else if (stage == 5) status = tx_put(container, roots[1], (gen + 2LL) * 100000);
        else status = tx_put(container, keys[stage-2], next[stage-2]);
        if (!status) goto compensate;
    }
    status = Array64Group_Read(container, name, index, gen+2, &observed, &count, &i);
    if (status == 1 && observed == raw) return 1;

compensate:
    if (na_lookup(container, roots[1], &observed) != 1) return -4;
    if (observed == gen * 100000LL) {
        int pristine = 1;
        for (i = 0; i < 3; ++i) {
            if (na_lookup(container, keys[i], &observed) != 1 || observed != baseline[i]) pristine = 0;
        }
        if (pristine) return 2;
    }
    if (!tx_put(container, roots[1], (gen+1LL)*100000)) return -4;
    for (i = 0; i < 3; ++i) {
        if (fail_rollback == i+1 || !tx_put(container, keys[i], baseline[i])) restored = 0;
    }
    if (!restored || fail_rollback == 4) return -3;
    if (!tx_put(container, roots[1], gen*100000LL)) return -4;
    status = Array64Group_Read(container, name, index, gen, &observed, &count, &i);
    if (status == 1 && observed == original) return 2;
    if (!tx_put(container, roots[1], (gen+1LL)*100000)) return -4;
    return -3;
}
