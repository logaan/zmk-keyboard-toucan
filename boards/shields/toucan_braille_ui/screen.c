// SPDX-License-Identifier: MIT
/* An original text-first 240x280 dashboard. No vendor widgets or layouts. */
#include <stdio.h>
#include <string.h>
#include <lvgl.h>
#include <zephyr/kernel.h>
#include <zmk/display.h>
#include <zmk/endpoints.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>
#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/split_central_status_changed.h>
#include <braille_display.h>
#include <braille_engine.h>
#include <braille_tables.h>
#include "format.h"

struct dashboard_state {
    struct braille_display_snapshot braille;
    char endpoint[64];
    char notice[32];
    uint8_t mods;
    uint8_t battery[2];
    bool known[2], connected[2], braille_layer;
};
static struct dashboard_state state;
static struct k_spinlock state_lock;
static int64_t notice_until;
static lv_obj_t *battery_label[2], *endpoint_label, *mods_label;
static lv_obj_t *mode_label, *preview_label, *dots_label, *pending_label, *notice_label;

/* Input inspection runs on the system queue, alongside central behavior work;
 * LVGL only reads the copied snapshot on its own display queue. */
static void collect(struct k_work *work) {
    struct braille_display_snapshot braille;
    braille_display_snapshot(&braille);
    struct zmk_endpoint_instance preferred = zmk_endpoint_get_preferred();
    struct zmk_endpoint_instance selected = zmk_endpoint_get_selected();
    char endpoint[64];
    dashboard_endpoint(endpoint, sizeof(endpoint), preferred.transport,
                       preferred.transport == ZMK_TRANSPORT_BLE ? preferred.ble.profile_index : 0,
                       selected.transport,
                       selected.transport == ZMK_TRANSPORT_BLE ? selected.ble.profile_index : 0);
    /* The report includes effective explicit, implicit and sticky modifiers. */
    uint8_t mods = zmk_hid_get_keyboard_report()->body.modifiers;
    bool active = zmk_keymap_layer_active(CONFIG_TOUCAN_BRAILLE_UI_LAYER);
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    state.braille = braille;
    memcpy(state.endpoint, endpoint, sizeof(endpoint));
    state.mods = mods;
    state.braille_layer = active;
    if (k_uptime_get() >= notice_until) state.notice[0] = 0;
    k_spin_unlock(&state_lock, key);
}
K_WORK_DEFINE(collect_work, collect);

/* The engine calls this only for real input, never previews. */
void braille_engine_notify_dropped_prefix(const uint16_t *cells, uint8_t count,
                                          struct zmk_behavior_binding_event event) {
    const char *mode = braille_tables_active();
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    snprintf(state.notice, sizeof(state.notice), "%s",
             mode && !strcmp(mode, "computer8") ? "Reserved cell" : "Incomplete input dropped");
    notice_until = k_uptime_get() + 1800;
    k_spin_unlock(&state_lock, key);
}

static int peripheral_event(const zmk_event_t *eh) {
    const struct zmk_peripheral_battery_state_changed *battery =
        as_zmk_peripheral_battery_state_changed(eh);
    const struct zmk_split_central_status_changed *connection =
        as_zmk_split_central_status_changed(eh);
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    if (battery && battery->source < 2) {
        state.battery[battery->source] = battery->state_of_charge;
        state.known[battery->source] = true;
    }
    if (connection && connection->slot < 2) {
        state.connected[connection->slot] = connection->connected;
        if (!connection->connected) state.known[connection->slot] = false;
    }
    k_spin_unlock(&state_lock, key);
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(toucan_dashboard, peripheral_event);
ZMK_SUBSCRIPTION(toucan_dashboard, zmk_peripheral_battery_state_changed);
ZMK_SUBSCRIPTION(toucan_dashboard, zmk_split_central_status_changed);

static void refresh(lv_timer_t *timer) {
    struct dashboard_state copy;
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    copy = state;
    k_spin_unlock(&state_lock, key);
    for (unsigned i = 0; i < 2; ++i) {
        if (copy.connected[i] && copy.known[i])
            lv_label_set_text_fmt(battery_label[i], "%s  %u%%", i ? "BOARD 2" : "BOARD 1", copy.battery[i]);
        else lv_label_set_text_fmt(battery_label[i], "%s  %s", i ? "BOARD 2" : "BOARD 1",
                                  copy.connected[i] ? "--" : "offline");
    }
    lv_label_set_text(endpoint_label, copy.endpoint);
    lv_label_set_text_fmt(mods_label, "%s  %s  %s  %s",
                         copy.mods & 0x11 ? "CTRL" : "----", copy.mods & 0x22 ? "SHIFT" : "-----",
                         copy.mods & 0x44 ? "ALT" : "---", copy.mods & 0x88 ? "CMD" : "---");
    lv_label_set_text_fmt(mode_label, "%s / %s", copy.braille_layer ? "BRAILLE" : "KEYBOARD",
                          copy.braille.mode);
    lv_label_set_text(preview_label, copy.braille_layer ?
                      (copy.braille.preview[0] ? copy.braille.preview : "...") : "Ready");
    char dots[12];
    braille_display_cells(&copy.braille.held, copy.braille.held ? 1 : 0, dots, sizeof(dots));
    lv_label_set_text_fmt(dots_label, "HELD %s%s", dots[0] ? dots : "--",
                          copy.braille.waiting ? " / provisional" : "");
    lv_label_set_text_fmt(pending_label, "BUFFER %u\n%s", copy.braille.pending_count,
                          copy.braille.pending[0] ? copy.braille.pending : "--");
    lv_label_set_text(notice_label, copy.notice);
    k_work_submit(&collect_work);
}

static lv_obj_t *label(lv_obj_t *screen, int x, int y, int width,
                       const lv_font_t *font, uint32_t color) {
    lv_obj_t *obj = lv_label_create(screen);
    lv_obj_set_pos(obj, x, y);
    lv_obj_set_width(obj, width);
    lv_obj_set_style_text_font(obj, font, 0);
    lv_obj_set_style_text_color(obj, lv_color_hex(color), 0);
    lv_label_set_long_mode(obj, LV_LABEL_LONG_WRAP);
    lv_label_set_text(obj, "");
    return obj;
}

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x101820), 0);
    lv_obj_set_style_pad_all(screen, 0, 0);
    lv_obj_set_style_border_width(screen, 0, 0);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    battery_label[0] = label(screen, 12, 12, 108, &lv_font_montserrat_14, 0xC4D8DE);
    battery_label[1] = label(screen, 122, 12, 108, &lv_font_montserrat_14, 0xC4D8DE);
    endpoint_label = label(screen, 12, 39, 216, &lv_font_montserrat_14, 0xFFFFFF);
    mods_label = label(screen, 12, 78, 216, &lv_font_montserrat_14, 0x8EDFCC);
    mode_label = label(screen, 12, 101, 216, &lv_font_montserrat_14, 0x8EDFCC);
    preview_label = label(screen, 12, 126, 216, &lv_font_montserrat_28, 0xFFFFFF);
    lv_obj_set_height(preview_label, 65);
    lv_label_set_long_mode(preview_label, LV_LABEL_LONG_DOT);
    dots_label = label(screen, 12, 192, 216, &lv_font_montserrat_14, 0xC4D8DE);
    pending_label = label(screen, 12, 214, 216, &lv_font_montserrat_14, 0xC4D8DE);
    lv_obj_set_height(pending_label, 42);
    lv_label_set_long_mode(pending_label, LV_LABEL_LONG_SCROLL_CIRCULAR);
    notice_label = label(screen, 12, 260, 216, &lv_font_montserrat_14, 0xFFD18D);
    refresh(NULL);
    lv_timer_create(refresh, 50, NULL);
    return screen;
}
