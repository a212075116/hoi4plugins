#pragma once

typedef struct {
    int session_ready;
    int single_player;
    int platform_ready;
    int remaining_possible;
    int ironman;
    int checksum_matches;
} AchievementEnvironment;

static int AchievementPolicy_Eligible(const AchievementEnvironment* env, int compatibility) {
    if (!env || !env->session_ready || !env->single_player || !env->platform_ready || !env->remaining_possible) return 0;
    return compatibility || (env->ironman && env->checksum_matches);
}

static int AchievementPolicy_Submit(const AchievementEnvironment* env, int compatibility, int happened, int already_unlocked) {
    return happened && !already_unlocked && AchievementPolicy_Eligible(env, compatibility);
}
