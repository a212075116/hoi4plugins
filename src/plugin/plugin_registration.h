#pragma once

typedef struct PluginRegistrationStep {
    const char* name;
    int (*run)(void);
    int expected;
    int (*ready)(void);
    int complete;
    int last;
} PluginRegistrationStep;

static inline int PluginRegistration_Poll(PluginRegistrationStep* steps, int count)
{
    int i, complete = 1;
    for (i = 0; i < count; ++i) {
        if (!steps[i].complete) {
            steps[i].last = steps[i].run();
            steps[i].complete = steps[i].last == steps[i].expected
                && (steps[i].ready == 0 || steps[i].ready());
        }
        if (!steps[i].complete) complete = 0;
    }
    return complete;
}
