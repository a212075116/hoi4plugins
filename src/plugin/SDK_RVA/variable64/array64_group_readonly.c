#include "native_array_readonly.c"

static int ag_name(const char* name, char keys[6][40])
{
    const char* suffix[6] = { "_ver", "_gen", "_len", "_lo", "_hi", "_kind" };
    unsigned int n = 0, i, j, k;
    if (!name || name[0] < 'a' || name[0] > 'z') return 0;
    while (name[n]) {
        char c = name[n];
        if (n >= 20 || !((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) return 0;
        ++n;
    }
    for (i = 0; i < 6; ++i) {
        const char* prefix = "__v64a_";
        for (j = 0; j < 7; ++j) keys[i][j] = prefix[j];
        for (k = 0; k < n; ++k) keys[i][j++] = name[k];
        for (k = 0; suffix[i][k]; ++k) keys[i][j++] = suffix[i][k];
        keys[i][j] = 0;
    }
    return 1;
}

static int ag_inventory(const void* container, char keys[6][40], int* owned)
{
    const unsigned char* c = (const unsigned char*)container;
    const unsigned char* table;
    unsigned int mask, offset, span, take, slot, i, j;
    unsigned char spill, block[1536];
    char text[128];
    *owned = 0;
    if (!container || !na_read_memory(c + 24, &table, 8) || !na_read_memory(c + 36, &mask, 4) ||
        !na_read_memory(c + 40, &spill, 1) || !table || mask > 1048575u || (mask & (mask + 1))) return 0;
    if (!mask) return na_empty_table(c, table);
    span = mask + 1 + spill;
    for (offset = 0; offset < span; offset += take) {
        take = span - offset; if (take > 32) take = 32;
        if (!na_read_memory(table + 48ull * offset, block, take * 48ull)) return 0;
        for (slot = 0; slot < take; ++slot) {
            unsigned char* node = block + slot * 48;
            NaSize size, capacity;
            if (!node[4]) continue;
            size = *(NaSize*)(node + 24); capacity = *(NaSize*)(node + 32);
            if (!size || size >= sizeof(text) || size > capacity || (capacity <= 15 && size > 15)) return 0;
            if (capacity <= 15) {
                for (j = 0; j < size; ++j) text[j] = (char)node[8 + j];
            } else if (!na_read_memory(*(const char**)(node + 8), text, size)) return 0;
            text[size] = 0;
            for (i = 0; i < 6; ++i) {
                for (j = 0; keys[i][j] && text[j] == keys[i][j]; ++j) {}
                if (!keys[i][j] && (!text[j] || text[j] == '^')) { ++*owned; break; }
            }
        }
    }
    return 1;
}

int Array64Group_Read(const void* container, const char* name, int index, int expected_generation,
    long long* output, int* count, int* generation)
{
    char keys[6][40];
    long long manifest[3], value[3], decoded = 0;
    int state[3], present = 0, owned, length, gen, i, j, observed;
    if (!output || !count || !generation || !ag_name(name, keys)) return -1;
    for (i = 0; i < 3; ++i) {
        state[i] = na_lookup(container, keys[i], &manifest[i]);
        if (state[i] < 0) return -1;
        present += state[i];
    }
    if (!ag_inventory(container, keys, &owned)) return -1;
    if (!present) return owned ? -3 : 0;
    if (present != 3) return -2;
    if (manifest[0] != 200000) return -4;
    if (manifest[1] < 0 || manifest[1] % 100000 || manifest[1] / 100000 > 2147483646LL ||
        (manifest[1] / 100000) % 2) return -5;
    gen = (int)(manifest[1] / 100000);
    if (expected_generation < -1 || (expected_generation != -1 && expected_generation != gen)) return -9;
    if (manifest[2] < 0 || manifest[2] % 100000 || manifest[2] / 100000 > 4096) return -6;
    length = (int)(manifest[2] / 100000);
    for (j = 0; j < 3; ++j) {
        long long raw_length;
        char length_key[48];
        unsigned int k = 0;
        while (keys[3+j][k]) { length_key[k] = keys[3+j][k]; ++k; }
        length_key[k++] = '^'; length_key[k++] = 'n'; length_key[k++] = 'u'; length_key[k++] = 'm'; length_key[k] = 0;
        state[0] = na_lookup(container, length_key, &raw_length);
        if (state[0] < 0) return -1;
        if (!state[0] || raw_length != manifest[2]) return -7;
    }
    if (owned != 6 + 3 * length) return -3;
    for (i = 0; i < length; ++i) {
        long long raw;
        for (j = 0; j < 3; ++j) {
            state[0] = NativeArray_Read(container, keys[3+j], i, &value[j], &observed);
            if (state[0] == -1) return -1;
            if (state[0] != 1 || observed != length) return -7;
        }
        if (!value[2]) {
            if (value[1] || value[0] <= -214748364800000LL || value[0] >= 214748364800000LL) return -8;
            raw = value[0];
        } else if (value[2] >= 100000 && value[2] <= 400000 && value[2] % 100000 == 0) {
            long long low, high;
            if (value[0] % 100000 || value[1] % 100000) return -8;
            low = value[0] / 100000; high = value[1] / 100000;
            if (low < -2147483647LL || low > 2147483647LL || high < -2147483647LL || high > 2147483647LL) return -8;
            if ((value[2] / 100000 - 1) & 1) { if (low) return -8; low = -2147483648LL; }
            if ((value[2] / 100000 - 1) & 2) { if (high) return -8; high = -2147483648LL; }
            raw = high * 4294967296LL + (low < 0 ? low + 4294967296LL : low);
        } else return -8;
        if (i == index) decoded = raw;
    }
    if (index < 0 || index >= length) { *count = length; *generation = gen; return 2; }
    *output = decoded; *count = length; *generation = gen;
    return 1;
}
