#pragma once

static inline unsigned long long ad_get(const unsigned char* p, int n)
{
    unsigned long long v = 0;
    int i;
    for (i = 0; i < n; ++i) v |= (unsigned long long)p[i] << (8*i);
    return v;
}

static inline void ad_put(unsigned char* p, unsigned long long v, int n)
{
    int i;
    for (i = 0; i < n; ++i) p[i] = (unsigned char)(v >> (8*i));
}

static inline unsigned long long ad_hash(const unsigned char* p, unsigned int n)
{
    unsigned long long h = 14695981039346656037ull;
    unsigned int i;
    for (i = 0; i < n; ++i) h = (h ^ p[i]) * 1099511628211ull;
    return h;
}

static inline long long ad_i64(const unsigned char* p)
{
    unsigned long long bits = ad_get(p, 8);
    return bits <= 9223372036854775807ull ? (long long)bits : -1 - (long long)(~bits);
}

static inline int ad_i32(const unsigned char* p)
{
    unsigned int bits = (unsigned int)ad_get(p, 4);
    return bits <= 2147483647u ? (int)bits : -1 - (int)(~bits);
}
