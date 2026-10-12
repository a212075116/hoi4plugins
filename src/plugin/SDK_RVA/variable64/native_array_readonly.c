typedef unsigned long long NaSize;
extern int na_read_memory(const void* source, void* output, NaSize bytes);

static int na_lookup(const void* container, const char* name, long long* raw)
{
    const unsigned char* c = (const unsigned char*)container;
    const unsigned char* buckets;
    unsigned int mask, hash = 2166136261u, i, length = 0;
    unsigned char node[48], distance;
    NaSize size, capacity;
    const char* text;
    char found[128];
    if (!container || !name || !raw) return -1;
    while (name[length]) {
        if (length >= 127) return -1;
        hash = (hash ^ (unsigned char)name[length++]) * 16777619u;
    }
    if (!length || !na_read_memory(c + 24, &buckets, 8) ||
        !na_read_memory(c + 36, &mask, 4)) return -1;
    if (!buckets || mask < 1 || mask > 1048575u || (mask & (mask + 1))) return -1;
    for (i = 0; i < 255; ++i) {
        const unsigned char* p = buckets + 48ull * ((hash & mask) + (NaSize)i);
        if (!na_read_memory(p, node, 48)) return -1;
        distance = node[4];
        if (distance <= i) return 0;
        if (*(unsigned int*)node != hash) continue;
        size = *(NaSize*)(node + 24);
        capacity = *(NaSize*)(node + 32);
        if (size != length) continue;
        if (size > capacity || size >= sizeof(found) || (capacity <= 15 && size > 15)) return -1;
        if (capacity <= 15) {
            unsigned int j;
            for (j = 0; j < size; ++j) found[j] = (char)node[8 + j];
        } else {
            text = *(const char**)(node + 8);
            if (!na_read_memory(text, found, size)) return -1;
        }
        {
            unsigned int j;
            for (j = 0; j < length && found[j] == name[j]; ++j) {}
            if (j == length) { *raw = *(long long*)(node + 40); return 1; }
        }
    }
    return -1;
}

int NativeArray_Read(const void* container, const char* name, int index, long long* output, int* count)
{
    char key[128];
    unsigned int n = 0, i, digits = 0;
    long long length_raw, value;
    int state, length, number;
    char reversed[12];
    if (!name || !output || !count) return -1;
    while (name[n]) {
        unsigned char ch = (unsigned char)name[n];
        if (n >= 100 || !((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
            (ch >= '0' && ch <= '9') || ch == '_')) return -1;
        key[n] = name[n]; ++n;
    }
    if (!n) return -1;
    key[n] = '^'; key[n+1] = 'n'; key[n+2] = 'u'; key[n+3] = 'm'; key[n+4] = 0;
    state = na_lookup(container, key, &length_raw);
    if (state <= 0) return state;
    if (length_raw < 0 || length_raw % 100000 || length_raw / 100000 > 4096) return -2;
    length = (int)(length_raw / 100000);
    if (index < 0 || index >= length) { *count = length; return 2; }
    number = index;
    do { reversed[digits++] = (char)('0' + number % 10); number /= 10; } while (number);
    for (i = 0; i < digits; ++i) key[n + 1 + i] = reversed[digits - 1 - i];
    key[n + 1 + digits] = 0;
    state = na_lookup(container, key, &value);
    if (state < 0) return -1;
    if (!state) return -3;
    *output = value; *count = length;
    return 1;
}
