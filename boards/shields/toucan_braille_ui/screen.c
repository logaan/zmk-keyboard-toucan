// SPDX-License-Identifier: MIT
/* Original signal-panel dashboard, drawn with native LVGL objects. */
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
#include <braille_mode_labels.h>
#include <braille_engine.h>
#include <braille_tables.h>
#ifdef CONFIG_ZMK_BRAILLE_SETTINGS_UI
#include <braille_editor.h>
#endif
#ifdef CONFIG_ZMK_BRAILLE_STORAGE
#include <braille_storage.h>
#endif
#include "format.h"

struct dashboard_state {
    struct braille_display_snapshot braille;
#ifdef CONFIG_ZMK_BRAILLE_SETTINGS_UI
    struct braille_editor_snapshot editor;
#endif
    char endpoint[64];
    char notice[32];
    uint8_t mods;
    uint8_t battery[2];
    bool known[2], connected[2], braille_layer;
};
static struct dashboard_state state;
static struct k_spinlock state_lock;
static int64_t notice_until;
enum { INK = 0x101414, PAPER = 0xF1F0E6, ACID = 0xD6FF00,
       ORANGE = 0xFF6B00, MUTED = 0x737D79, TRACK = 0x303936 };
static lv_obj_t *battery_label[2], *battery_fill[2], *endpoint_label;
static lv_obj_t *mod_chip[4], *mod_label[4], *held_dot[8], *held_panel;
static lv_obj_t *buffer_panel, *buffer_heading, *activity_label;
static lv_obj_t *mode_label, *preview_label, *dots_label, *pending_label, *notice_label;

/* Input inspection runs on the system queue, alongside central behavior work;
 * LVGL only reads the copied snapshot on its own display queue. */
static void collect(struct k_work *work) {
    struct braille_display_snapshot braille;
    braille_display_snapshot(&braille);
#ifdef CONFIG_ZMK_BRAILLE_SETTINGS_UI
    struct braille_editor_snapshot editor;
    braille_editor_snapshot(&editor);
#endif
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
#ifdef CONFIG_ZMK_BRAILLE_SETTINGS_UI
    state.editor = editor;
#endif
    memcpy(state.endpoint, endpoint, sizeof(endpoint));
    state.mods = mods;
    state.braille_layer = active;
    if (k_uptime_get() >= notice_until) {
        state.notice[0] = 0;
#ifdef CONFIG_ZMK_BRAILLE_STORAGE
        if (braille_storage_last_error())
            snprintf(state.notice, sizeof(state.notice), "Storage error %d", braille_storage_last_error());
        else if (braille_storage_skipped_count())
            snprintf(state.notice, sizeof(state.notice), "%u saved rules skipped", braille_storage_skipped_count());
#endif
    }
    k_spin_unlock(&state_lock, key);
}
K_WORK_DEFINE(collect_work, collect);

/* The engine calls this only for real input, never previews. */
void braille_engine_notify_dropped_prefix(const uint16_t *cells, uint8_t count,
                                          struct zmk_behavior_binding_event event) {
    const char *mode = braille_tables_active();
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    snprintf(state.notice, sizeof(state.notice), "%s",
             braille_display_computer8_mode(mode) ? "Reserved cell" : "Incomplete input dropped");
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

static void visible(lv_obj_t *obj, bool show) {
    if (show) lv_obj_clear_flag(obj, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(obj, LV_OBJ_FLAG_HIDDEN);
}

/* Avoid restarting scrolling translations/buffers on every 50 ms snapshot. */
static void text_if_changed(lv_obj_t *obj, const char *text) {
    if (strcmp(lv_label_get_text(obj), text)) lv_label_set_text(obj, text);
}

/* LVGL restarts label animations when long mode is assigned, even if the
 * value is unchanged. Font changes also trigger a text layout refresh. */
static void scrolling_font(lv_obj_t *obj, const lv_font_t *font) {
    if (lv_obj_get_style_text_font(obj, 0) != font)
        lv_obj_set_style_text_font(obj, font, 0);
    if (lv_label_get_long_mode(obj) != LV_LABEL_LONG_SCROLL_CIRCULAR)
        lv_label_set_long_mode(obj, LV_LABEL_LONG_SCROLL_CIRCULAR);
}

static void refresh(lv_timer_t *timer) {
    struct dashboard_state copy;
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    copy = state;
    k_spin_unlock(&state_lock, key);
    for (unsigned i = 0; i < 2; ++i) {
        bool valid = copy.connected[i] && copy.known[i];
        if (valid)
            lv_label_set_text_fmt(battery_label[i], "%u%%", copy.battery[i]);
        else lv_label_set_text(battery_label[i], copy.connected[i] ? "--" : "offline");
        lv_obj_set_style_text_font(battery_label[i], valid ? &lv_font_montserrat_20 : &lv_font_montserrat_14, 0);
        unsigned charge = copy.battery[i] > 100 ? 100 : copy.battery[i];
        lv_obj_set_width(battery_fill[i], valid ? (100 * charge / 100) : 0);
        lv_obj_set_style_bg_color(battery_fill[i], lv_color_hex(charge <= 20 ? ORANGE : INK), 0);
        visible(battery_fill[i], valid && charge);
    }
    lv_label_set_text(endpoint_label, copy.endpoint);
    lv_obj_set_style_text_color(endpoint_label,
        lv_color_hex(strstr(copy.endpoint, "connected") ? ACID : ORANGE), 0);
    for (unsigned i = 0; i < 4; ++i) {
        bool active = copy.mods & (0x11 << i);
        lv_obj_set_style_bg_color(mod_chip[i], lv_color_hex(active ? ORANGE : TRACK), 0);
        lv_obj_set_style_text_color(mod_label[i], lv_color_hex(active ? INK : PAPER), 0);
    }
    bool editing = false;
#ifdef CONFIG_ZMK_BRAILLE_SETTINGS_UI
    editing = copy.editor.active;
#endif
    visible(held_panel, !editing);
    visible(buffer_panel, !editing);
    visible(activity_label, !editing);
    visible(dots_label, !editing);
#ifdef CONFIG_ZMK_BRAILLE_SETTINGS_UI
    if (editing) {
        lv_label_set_text(mode_label, copy.editor.title);
        lv_obj_set_pos(preview_label, 10, 141);
        lv_obj_set_size(preview_label, 220, 116);
        scrolling_font(preview_label, &lv_font_montserrat_14);
        text_if_changed(preview_label, copy.editor.body);
        text_if_changed(notice_label, copy.editor.error ? "Failed: retry / Sp12 back" :
                          "Sp1/4 move; Sp15 enter");
        k_work_submit(&collect_work);
        return;
    }
#endif
    lv_obj_set_pos(preview_label, 10, 156);
    lv_obj_set_size(preview_label, 168, 36);
    /* Long translations scroll instead of silently losing their suffix. */
    scrolling_font(preview_label, &lv_font_montserrat_28);
    lv_label_set_text(mode_label, braille_display_mode_label(copy.braille.mode));
    lv_label_set_text(activity_label, copy.braille_layer ?
                      (copy.braille.waiting ? "BRAILLE / PENDING" : "BRAILLE / PREVIEW") : "KEYBOARD");
    text_if_changed(preview_label, copy.braille_layer ?
                      (copy.braille.preview[0] ? copy.braille.preview : "...") : "Ready");
    for (unsigned i = 0; i < 8; ++i)
        lv_obj_set_style_bg_color(held_dot[i],
            lv_color_hex(copy.braille.held & (1u << i) ? ORANGE : TRACK), 0);
    char dots[12];
    braille_display_cells(&copy.braille.held, copy.braille.held ? 1 : 0, dots, sizeof(dots));
    lv_label_set_text_fmt(dots_label, "HELD %s", dots[0] ? dots : "--");
    lv_label_set_text_fmt(buffer_heading, "BUFFER / %02u", copy.braille.pending_count);
    text_if_changed(pending_label, copy.braille.pending[0] ? copy.braille.pending : "--");
    text_if_changed(notice_label, copy.notice);
    k_work_submit(&collect_work);
}

static lv_obj_t *panel(lv_obj_t *parent, int x, int y, int width, int height,
                        uint32_t color) {
    lv_obj_t *obj = lv_obj_create(parent);
    lv_obj_remove_style_all(obj);
    lv_obj_set_pos(obj, x, y);
    lv_obj_set_size(obj, width, height);
    lv_obj_set_style_bg_color(obj, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
    lv_obj_clear_flag(obj, LV_OBJ_FLAG_SCROLLABLE);
    return obj;
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
    lv_obj_set_style_bg_color(screen, lv_color_hex(INK), 0);
    lv_obj_set_style_pad_all(screen, 0, 0);
    lv_obj_set_style_border_width(screen, 0, 0);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    for (unsigned i = 0; i < 2; ++i) {
        lv_obj_t *battery = panel(screen, i * 122, 0, 118, 39, i ? PAPER : ACID);
        lv_obj_t *name = label(battery, 9, 6, 27, &lv_font_montserrat_14, INK);
        lv_label_set_text(name, i ? "B2" : "B1");
        battery_label[i] = label(battery, 38, 2, 76, &lv_font_montserrat_20, INK);
        panel(battery, 9, 26, 100, 5, MUTED);
        battery_fill[i] = panel(battery, 9, 26, 100, 5, INK);
    }
    panel(screen, 0, 45, 3, 31, ACID);
    endpoint_label = label(screen, 10, 43, 222, &lv_font_montserrat_14, ACID);
    lv_obj_set_height(endpoint_label, 34);
    static const char *const names[] = { "CTRL", "SHIFT", "ALT", "CMD" };
    for (unsigned i = 0; i < 4; ++i) {
        mod_chip[i] = panel(screen, 6 + i * 59, 81, 54, 21, TRACK);
        mod_label[i] = label(mod_chip[i], 0, 2, 54, &lv_font_montserrat_14, PAPER);
        lv_obj_set_style_text_align(mod_label[i], LV_TEXT_ALIGN_CENTER, 0);
        lv_label_set_text(mod_label[i], names[i]);
    }
    lv_obj_t *mode = panel(screen, 0, 108, 240, 26, ACID);
    mode_label = label(mode, 10, 4, 220, &lv_font_montserrat_14, INK);
    panel(mode, 221, 0, 7, 26, PAPER);
    panel(mode, 232, 0, 8, 26, ORANGE);
    activity_label = label(screen, 10, 140, 170, &lv_font_montserrat_14, MUTED);
    preview_label = label(screen, 10, 156, 168, &lv_font_montserrat_28, PAPER);
    held_panel = panel(screen, 187, 143, 45, 68, INK);
    /* Physical braille order, not sequential row order. */
    static const uint8_t dot_x[] = {0, 0, 0, 24, 24, 24, 0, 24};
    static const uint8_t dot_y[] = {0, 18, 36, 0, 18, 36, 54, 54};
    for (unsigned i = 0; i < 8; ++i) {
        held_dot[i] = panel(held_panel, dot_x[i], dot_y[i], 13, 13, TRACK);
        lv_obj_set_style_radius(held_dot[i], LV_RADIUS_CIRCLE, 0);
    }
    dots_label = label(screen, 10, 201, 172, &lv_font_montserrat_14, MUTED);
    buffer_panel = panel(screen, 0, 221, 240, 38, PAPER);
    buffer_heading = label(buffer_panel, 10, 2, 220, &lv_font_montserrat_14, INK);
    pending_label = label(buffer_panel, 10, 19, 220, &lv_font_montserrat_14, INK);
    lv_obj_set_height(pending_label, 17);
    lv_label_set_long_mode(pending_label, LV_LABEL_LONG_SCROLL_CIRCULAR);
    notice_label = label(screen, 6, 263, 228, &lv_font_montserrat_14, ORANGE);
    lv_obj_set_height(notice_label, 17);
    lv_label_set_long_mode(notice_label, LV_LABEL_LONG_SCROLL_CIRCULAR);
    refresh(NULL);
    lv_timer_create(refresh, 50, NULL);
    return screen;
}
