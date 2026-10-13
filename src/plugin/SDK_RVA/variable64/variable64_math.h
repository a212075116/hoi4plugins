#pragma once
#include <intrin.h>

#define VAR64_SLOT_SCALE 100000LL
#define VAR64_FRAC_SCALE 100000LL
#define VAR64_FRAC_BIAS 100000LL
#define VAR64_TRUE_CLAMP 9223372036854775807LL
#define VAR64_INT32_MAX 2147483647LL
#define VAR64_INT32_MIN (-2147483648LL)
#define VAR64_OP_ADD 0
#define VAR64_OP_SUB 1
#define VAR64_OP_MUL 2
#define VAR64_OP_DIV 3

static int Var64_DecodeStoredParts(long long lo, long long hi, long long frac, long long* outRaw)
{
    if (frac <= 0 || frac >= 200000LL * VAR64_SLOT_SCALE || frac % VAR64_SLOT_SCALE != 0) return 0;
    if (!(lo % VAR64_SLOT_SCALE == 0 && hi % VAR64_SLOT_SCALE == 0
        && lo / VAR64_SLOT_SCALE >= (-2147483647LL - 1)
        && lo / VAR64_SLOT_SCALE <= 2147483647LL
        && hi / VAR64_SLOT_SCALE >= (-2147483647LL - 1)
        && hi / VAR64_SLOT_SCALE <= 2147483647LL)) return 0;
    if (outRaw != NULL) {
        long long integer = (long long)(((unsigned long long)(unsigned int)(hi / VAR64_SLOT_SCALE) << 32)
            | (unsigned int)(lo / VAR64_SLOT_SCALE));
        long long fraction = frac / VAR64_SLOT_SCALE - VAR64_FRAC_BIAS;
        long long raw;
        if (integer > 9223372036854775807LL / VAR64_FRAC_SCALE) {
            if (integer != 9223372036854775807LL / VAR64_FRAC_SCALE + 1 || fraction >= 0) return 0;
            --integer; fraction += VAR64_FRAC_SCALE;
        }
        if (integer < (-9223372036854775807LL - 1) / VAR64_FRAC_SCALE) {
            if (integer != (-9223372036854775807LL - 1) / VAR64_FRAC_SCALE - 1 || fraction <= 0) return 0;
            ++integer; fraction -= VAR64_FRAC_SCALE;
        }
        raw = integer * VAR64_FRAC_SCALE;
        if ((fraction > 0 && raw > 9223372036854775807LL - fraction)
            || (fraction < 0 && raw < (-9223372036854775807LL - 1) - fraction)) return 0;
        *outRaw = raw + fraction;
    }
    return 1;
}

static long long Var64_SaturatingAdd(long long a, long long b)
{
    if (b > 0 && a > VAR64_TRUE_CLAMP - b) return VAR64_TRUE_CLAMP;
    if (b < 0 && a < -VAR64_TRUE_CLAMP - b) return -VAR64_TRUE_CLAMP;
    return a + b < -VAR64_TRUE_CLAMP ? -VAR64_TRUE_CLAMP : a + b;
}

static long long Var64_SaturatingSub(long long a, long long b)
{
    if (b > 0 && a < -VAR64_TRUE_CLAMP + b) return -VAR64_TRUE_CLAMP;
    if (b < 0 && a > VAR64_TRUE_CLAMP + b) return VAR64_TRUE_CLAMP;
    return a - b < -VAR64_TRUE_CLAMP ? -VAR64_TRUE_CLAMP : a - b;
}

static int Var64_CalculateRaw(long long a, long long b, int op, long long* out)
{
    unsigned long long x, y, hi, lo, q, rem, divisor;
    int negative;
    if (op == VAR64_OP_ADD) { *out = Var64_SaturatingAdd(a, b); return 1; }
    if (op == VAR64_OP_SUB) { *out = Var64_SaturatingSub(a, b); return 1; }
    if (op == VAR64_OP_DIV && b == 0) return 0;
    x = a < 0 ? 0ULL - (unsigned long long)a : (unsigned long long)a;
    y = b < 0 ? 0ULL - (unsigned long long)b : (unsigned long long)b;
    negative = (a < 0) != (b < 0);
    lo = _umul128(x, op == VAR64_OP_MUL ? y : VAR64_FRAC_SCALE, &hi);
    divisor = op == VAR64_OP_MUL ? VAR64_FRAC_SCALE : y;
    if (hi >= divisor) q = (unsigned long long)VAR64_TRUE_CLAMP;
    else {
        q = _udiv128(hi, lo, divisor, &rem);
        if (q > (unsigned long long)VAR64_TRUE_CLAMP) q = (unsigned long long)VAR64_TRUE_CLAMP;
    }
    *out = negative ? -(long long)q : (long long)q;
    return 1;
}

