#pragma once
#include "variable64_decimal.h"

#define VAR64_FMT_DECIMALS_MAX 5
#define VAR64_FMT_TEXT_MAX     96
#define VAR64_SECTION_SIGN     0x11

typedef struct {
    int  decimals;
    int  useSiUnits;
    int  percentMode;
    int  signedPrefix;
    char dynamicColour;
    char staticColour;
} Var64TextFormat;

static void Var64_ParseTextFormat(const char* spec, const char* specEnd, Var64TextFormat* out)
{
    const char* p;

    if (out == NULL) return;
    memset(out, 0, sizeof(*out));
    out->decimals = -1;
    if (spec == NULL || specEnd == NULL) return;

    for (p = spec; p < specEnd && *p != 0; ++p) {
        char c = *p;
        if (c >= '0' && c <= '9') {
            out->decimals = (int)(c - '0');
            if (out->decimals > VAR64_FMT_DECIMALS_MAX) out->decimals = VAR64_FMT_DECIMALS_MAX;
        } else if (c == '*' || c == '^') {
            out->useSiUnits = 1;
        } else if (c == '%') {
            out->percentMode = (out->percentMode == 0) ? 1 : 2;
        } else if (c == '=') {
            out->signedPrefix = 1;
        } else if (c == '+') {
            out->dynamicColour = '+';
        } else if (c == '-') {
            out->dynamicColour = '-';
        } else if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')) {
            out->staticColour = c;
        }
    }
}

static void Var64_BuildFormattedText(const Var64TextFormat* fmt,
                                     long long vInt, long long vFrac,
                                     char* dst, int dstSize)
{
    int isNeg;
    int isZero;
    Var64DecNumber n;
    char body[64];
    const char* suffix = "";
    char colour = 0;
    int k = 0;
    int i;

    if (fmt == NULL || dst == NULL || dstSize < 16) return;
    isNeg = (vInt < 0) || (vFrac < 0);
    isZero = (vInt == 0 && vFrac == 0);
    Var64_DecFromParts(vInt, vFrac, &n);
    Var64_DecTrimZeros(&n);

    if (fmt->percentMode == 1) Var64_DecShiftDecimals(&n, -2);

    if (fmt->useSiUnits) {
        int intLen = n.len - n.decimals;
        if (intLen >= 7) {
            Var64_DecShiftDecimals(&n, 6);
            suffix = "M";
        } else if (intLen >= 4) {
            Var64_DecShiftDecimals(&n, 3);
            suffix = "K";
        }
        if (fmt->decimals >= 0) Var64_DecSetDecimals(&n, fmt->decimals);
        else Var64_DecSetDecimals(&n, 2);
    } else if (fmt->decimals >= 0) {
        Var64_DecSetDecimals(&n, fmt->decimals);
    }

    if (fmt->dynamicColour != 0) {
        if (isZero) colour = 'Y';
        else if (isNeg) colour = (fmt->dynamicColour == '+') ? 'R' : 'G';
        else colour = (fmt->dynamicColour == '+') ? 'G' : 'R';
    } else if (fmt->staticColour != 0) {
        colour = fmt->staticColour;
    }

    if (colour != 0 && k + 2 < dstSize) {
        dst[k++] = (char)VAR64_SECTION_SIGN;
        dst[k++] = colour;
    }
    if (fmt->signedPrefix && !isNeg && k + 1 < dstSize) dst[k++] = '+';
    Var64_DecRender(&n, body, (int)sizeof(body));
    for (i = 0; body[i] != 0 && k + 1 < dstSize; ++i) dst[k++] = body[i];
    for (i = 0; suffix[i] != 0 && k + 1 < dstSize; ++i) dst[k++] = suffix[i];
    if (fmt->percentMode != 0 && k + 1 < dstSize) dst[k++] = '%';
    if (colour != 0 && k + 2 < dstSize) {
        dst[k++] = (char)VAR64_SECTION_SIGN;
        dst[k++] = '!';
    }
    dst[k] = 0;
}
