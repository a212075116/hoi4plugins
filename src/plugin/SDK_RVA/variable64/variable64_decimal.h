#pragma once
#include <string.h>

#define VAR64_DEC_DIGITS 24

typedef struct {
    char digits[VAR64_DEC_DIGITS];
    int  len;
    int  decimals;
    int  neg;
} Var64DecNumber;

static void Var64_DecFromParts(long long vInt, long long vFrac, Var64DecNumber* out)
{
    unsigned long long a;
    unsigned long long f;
    char tmp[VAR64_DEC_DIGITS];
    char fb[5];
    int n = 0;
    int k;
    int i;

    if (out == NULL) return;
    memset(out, 0, sizeof(*out));
    out->neg = (vInt < 0) || (vFrac < 0);
    a = (unsigned long long)(vInt < 0 ? -vInt : vInt);
    f = (unsigned long long)(vFrac < 0 ? -vFrac : vFrac);

    if (a == 0) tmp[n++] = '0';
    while (a > 0 && n < VAR64_DEC_DIGITS - 6) {
        tmp[n++] = (char)('0' + (int)(a % 10ULL));
        a /= 10ULL;
    }
    for (i = 0; i < n; ++i) out->digits[i] = tmp[n - 1 - i];
    out->len = n;

    for (k = 4; k >= 0; --k) {
        fb[k] = (char)('0' + (int)(f % 10ULL));
        f /= 10ULL;
    }
    for (k = 0; k < 5 && out->len < VAR64_DEC_DIGITS - 1; ++k) {
        out->digits[out->len++] = fb[k];
    }
    out->decimals = 5;
}

static void Var64_DecTrimZeros(Var64DecNumber* n)
{
    if (n == NULL) return;
    while (n->decimals > 0 && n->len >= 1 && n->digits[n->len - 1] == '0') {
        --n->len;
        --n->decimals;
        if (n->len == 0) {
            n->len = 1;
            n->digits[0] = '0';
            n->decimals = 0;
            break;
        }
    }
}

static void Var64_DecSetDecimals(Var64DecNumber* n, int decimals)
{
    if (n == NULL) return;
    if (decimals < 0) decimals = 0;
    if (decimals > 5) decimals = 5;
    if (decimals < n->decimals) {
        int drop = n->decimals - decimals;
        if (drop >= n->len) {
            n->len = 1;
            n->digits[0] = '0';
        } else {
            n->len -= drop;
        }
        n->decimals = decimals;
    }
    if (n->len <= 0) {
        n->len = 1;
        n->digits[0] = '0';
    }
}

static void Var64_DecShiftDecimals(Var64DecNumber* n, int delta)
{
    if (n == NULL) return;
    n->decimals += delta;
    if (n->decimals < 0) {
        int pad = -n->decimals;
        while (pad > 0 && n->len < VAR64_DEC_DIGITS - 1) {
            int i;
            for (i = n->len; i > 0; --i) n->digits[i] = n->digits[i - 1];
            n->digits[0] = '0';
            ++n->len;
            --pad;
        }
        n->decimals = 0;
    }
}

static int Var64_DecRender(const Var64DecNumber* n, char* dst, int dstSize)
{
    int k = 0;
    int i;
    int intLen;

    if (n == NULL || dst == NULL || dstSize < 8) return 0;
    if (n->neg && k + 1 < dstSize) dst[k++] = '-';
    intLen = n->len - n->decimals;
    if (intLen <= 0) {
        if (k + 1 < dstSize) dst[k++] = '0';
    } else {
        for (i = 0; i < intLen && k + 1 < dstSize; ++i) dst[k++] = n->digits[i];
    }
    if (n->decimals > 0 && k + 1 < dstSize) {
        dst[k++] = '.';
        for (i = 0; i < -intLen && k + 1 < dstSize; ++i) dst[k++] = '0';
        for (i = (intLen > 0 ? intLen : 0); i < n->len && k + 1 < dstSize; ++i) {
            dst[k++] = n->digits[i];
        }
    }
    dst[k] = 0;
    return k;
}

static void Var64_FormatPartsToText(long long vInt, long long vFrac, char* dst, int dstSize)
{
    Var64DecNumber n;

    Var64_DecFromParts(vInt, vFrac, &n);
    Var64_DecTrimZeros(&n);
    Var64_DecRender(&n, dst, dstSize);
}

