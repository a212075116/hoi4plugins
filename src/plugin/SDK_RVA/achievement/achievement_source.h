#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define ACH_SOURCE_NAME "common/achievements.txt"
#define ACH_SOURCE_MOUNT "__hoi4plugins_vanilla_achievement_v1"
#define ACH_SOURCE_PATH ACH_SOURCE_MOUNT "/" ACH_SOURCE_NAME
#define ACH_SOURCE_ARCHIVE "hoi4plugins_vanilla_achievement_v1.zip"
#define ACH_SOURCE_MAX_BYTES (16u * 1024u * 1024u)

static int AchievementSource_ShouldRedirect(int context, const char* name, size_t length) {
    return context > 0 && name && length == sizeof(ACH_SOURCE_NAME) - 1 &&
        memcmp(name, ACH_SOURCE_NAME, sizeof(ACH_SOURCE_NAME) - 1) == 0;
}

static void AchievementSource_Put16(unsigned char* p, uint16_t value) {
    p[0] = (unsigned char)value; p[1] = (unsigned char)(value >> 8);
}

static void AchievementSource_Put32(unsigned char* p, uint32_t value) {
    AchievementSource_Put16(p, (uint16_t)value);
    AchievementSource_Put16(p + 2, (uint16_t)(value >> 16));
}

static size_t AchievementSource_ZipSize(size_t length) {
    return length && length <= ACH_SOURCE_MAX_BYTES ? length + 98 + 2 * (sizeof(ACH_SOURCE_NAME) - 1) : 0;
}

static size_t AchievementSource_Pack(const unsigned char* data, size_t length, unsigned char* out, size_t capacity) {
    size_t total = AchievementSource_ZipSize(length), name = sizeof(ACH_SOURCE_NAME) - 1, central, i;
    uint32_t crc = 0xffffffffu;
    int bit;
    if (!data || !out || !total || capacity < total) return 0;
    for (i = 0; i < length; ++i) {
        crc ^= data[i];
        for (bit = 0; bit < 8; ++bit) crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
    }
    crc ^= 0xffffffffu;
    memset(out, 0, total);
    AchievementSource_Put32(out, 0x04034b50u);
    AchievementSource_Put16(out + 4, 20);
    AchievementSource_Put32(out + 14, crc);
    AchievementSource_Put32(out + 18, (uint32_t)length);
    AchievementSource_Put32(out + 22, (uint32_t)length);
    AchievementSource_Put16(out + 26, (uint16_t)name);
    memcpy(out + 30, ACH_SOURCE_NAME, name);
    memcpy(out + 30 + name, data, length);
    central = 30 + name + length;
    AchievementSource_Put32(out + central, 0x02014b50u);
    AchievementSource_Put16(out + central + 4, 20);
    AchievementSource_Put16(out + central + 6, 20);
    AchievementSource_Put32(out + central + 16, crc);
    AchievementSource_Put32(out + central + 20, (uint32_t)length);
    AchievementSource_Put32(out + central + 24, (uint32_t)length);
    AchievementSource_Put16(out + central + 28, (uint16_t)name);
    memcpy(out + central + 46, ACH_SOURCE_NAME, name);
    i = central + 46 + name;
    AchievementSource_Put32(out + i, 0x06054b50u);
    AchievementSource_Put16(out + i + 8, 1);
    AchievementSource_Put16(out + i + 10, 1);
    AchievementSource_Put32(out + i + 12, (uint32_t)(46 + name));
    AchievementSource_Put32(out + i + 16, (uint32_t)central);
    return total;
}
