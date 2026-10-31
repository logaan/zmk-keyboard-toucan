#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
struct k_work { int unused; };
struct k_spinlock { int unused; };
typedef int k_spinlock_key_t;
static inline int k_spin_lock(struct k_spinlock *s) {(void)s;return 0;}
static inline void k_spin_unlock(struct k_spinlock *s,int k) {(void)s;(void)k;}
static inline int64_t k_uptime_get(void) {return 0;}
static inline void k_work_submit(struct k_work *w) {(void)w;}
#define K_WORK_DEFINE(name,cb) struct k_work name
#define ZMK_LISTENER(...)
#define ZMK_SUBSCRIPTION(...)
#define ZMK_EV_EVENT_BUBBLE 0
#define CONFIG_TOUCAN_BRAILLE_UI_LAYER 5
#define CONFIG_ZMK_BRAILLE_SETTINGS_UI 1
#define CONFIG_ZMK_BRAILLE_STORAGE 1
typedef void zmk_event_t;
struct zmk_peripheral_battery_state_changed {unsigned source,state_of_charge;};
struct zmk_split_central_status_changed {unsigned slot;bool connected;};
static inline const struct zmk_peripheral_battery_state_changed *as_zmk_peripheral_battery_state_changed(const void *e) {(void)e;return NULL;}
static inline const struct zmk_split_central_status_changed *as_zmk_split_central_status_changed(const void *e) {(void)e;return NULL;}
#define ZMK_TRANSPORT_NONE 0
#define ZMK_TRANSPORT_USB 1
#define ZMK_TRANSPORT_BLE 2
struct zmk_endpoint_instance {int transport;struct {int profile_index;} ble;};
static inline struct zmk_endpoint_instance zmk_endpoint_get_preferred(void) {return (struct zmk_endpoint_instance){0};}
static inline struct zmk_endpoint_instance zmk_endpoint_get_selected(void) {return (struct zmk_endpoint_instance){0};}
struct report {struct {uint8_t modifiers;} body;};
static inline struct report *zmk_hid_get_keyboard_report(void) {static struct report r;return &r;}
static inline bool zmk_keymap_layer_active(int l) {(void)l;return true;}
struct zmk_behavior_binding_event {int position;};
struct braille_display_snapshot {uint16_t held;uint8_t pending_count;bool waiting;char mode[16],preview[96],pending[321];};
static inline void braille_display_snapshot(struct braille_display_snapshot *s) {memset(s,0,sizeof(*s));}
static inline void braille_display_cells(const uint16_t *c,size_t n,char *s,size_t z) {size_t i=0;if(n)for(unsigned d=0;d<8&&i+1<z;d++)if(*c&(1<<d))s[i++]='1'+d;s[i]=0;}
static inline const char *braille_tables_active(void) {return "ueb1";}
static inline int braille_storage_last_error(void) {return 0;}
static inline unsigned braille_storage_skipped_count(void) {return 0;}
struct braille_editor_snapshot {bool active;int screen;char title[40],body[320],footer[80],query[32];int error;};
static inline void braille_editor_snapshot(struct braille_editor_snapshot *e) {memset(e,0,sizeof(*e));}
