// SPDX-License-Identifier: MIT
#pragma once
#include <stdio.h>
#include <string.h>
/* Transport values match ZMK's stable endpoint representation: none=0, USB=1, BLE=2. */
static inline void dashboard_target(char *out, size_t size, int transport, int profile) {
    if (transport == 2) snprintf(out, size, "BT %u", (unsigned)(profile + 1));
    else snprintf(out, size, "%s", transport == 1 ? "USB" : "No target");
}
static inline void dashboard_endpoint(char *out, size_t size, int preferred, int preferred_profile,
                                      int active, int active_profile) {
    char target[24], actual[24];
    dashboard_target(target, sizeof(target), preferred, preferred_profile);
    dashboard_target(actual, sizeof(actual), active, active_profile);
    if (!active) snprintf(out, size, "%s / offline", target);
    else if (preferred == active && (active != 2 || preferred_profile == active_profile))
        snprintf(out, size, "%s connected", actual);
    else snprintf(out, size, "%s connected\nPrefer %s", actual, target);
}
