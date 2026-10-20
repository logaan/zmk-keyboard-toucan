#!/usr/bin/env python3
"""Check resolved Toucan2 builds (not a hardware/gesture runtime test).

Usage: python3 scripts/check-builds.py /west/build/{left,right,reset,left-peripheral,prospector}
Accepts standalone and Prospector targets. Use --braille-mode computer8 for a
test-only default-mode override build.
"""

import argparse
from pathlib import Path
import re


def check_display_geometry(values, dongle=False):
    """Both Toucan left roles must use the actual panel, not stock nice!view."""
    display = values["DT_CHOSEN_zephyr_display"]
    width, height = (240, 280) if dongle else (144, 168)
    for prop, expected in (("width", width), ("height", height)):
        key = display + "_P_" + prop
        assert values.get(key) == str(expected), (key, values.get(key), expected)


def check_prospector_memory(config):
    """Allow battery fade layers without exhausting the nRF52840's RAM."""
    values = dict(line.split("=", 1) for line in config if line.startswith("CONFIG_") and "=" in line)
    heap = int(values.get("CONFIG_LV_Z_MEM_POOL_SIZE", "0"))
    buffer = int(values.get("CONFIG_LV_Z_VDB_SIZE", "100"))
    stack = int(values.get("CONFIG_ZMK_DISPLAY_DEDICATED_THREAD_STACK_SIZE", "0"))
    assert heap >= 32768, ("Prospector LVGL heap too small for battery animations", heap)
    assert 1 <= buffer <= 50, ("Prospector draw buffer leaves too little RAM headroom", buffer)
    assert stack >= 4096, ("Prospector display stack below module recommendation", stack)
    assert "CONFIG_LV_Z_FULL_REFRESH=y" not in config, "Partial buffer cannot use full-refresh mode"


def check(build, braille_mode):
    config = set((build / "zephyr/.config").read_text().splitlines())
    ninja = (build / "build.ninja").read_text()
    header = (build / "zephyr/include/generated/devicetree_generated.h").read_text()
    values = dict(re.findall(r"^#define (\S+)[ \t]+(.+)$", header, re.MULTILINE))
    left = "CONFIG_SHIELD_TOUCAN_LEFT=y" in config
    left_peripheral = "CONFIG_SHIELD_TOUCAN_LEFT_PERIPHERAL=y" in config
    right = "CONFIG_SHIELD_TOUCAN_RIGHT=y" in config
    dongle = "CONFIG_SHIELD_TOUCAN_DONGLE=y" in config
    reset = "CONFIG_SHIELD_SETTINGS_RESET=y" in config
    assert sum((left, left_peripheral, right, dongle, reset)) == 1, "Not a Toucan/reset build"
    central = left or dongle
    assert (build / "zephyr/zmk.uf2").stat().st_size > 0, "Missing UF2"
    assert "input_pinnacle.c.obj" not in ninja, "V1 driver is still present"

    def expect(key, expected):
        assert values.get(key) == str(expected), (key, values.get(key), expected)

    def node(label):
        return values[f"DT_N_NODELABEL_{label}"]

    def binding(layer, position, behavior, param=None):
        prefix = f"DT_N_S_keymap_S_{layer}_P_bindings_IDX_{position}"
        expect(prefix + "_PH", "DT_N_S_behaviors_S_" + behavior)
        if param is not None:
            expect(prefix + "_VAL_param1", param)

    assert ("CONFIG_ZMK_FEATURE_BRAILLE=y" in config) == central
    assert ("src/behavior_braille.c.obj:" in ninja) == central
    assert ("CONFIG_ZMK_STUDIO=y" in config) == central
    assert ("CONFIG_ZMK_POINTING_SMOOTH_SCROLLING=y" in config) == central
    assert ("CONFIG_INPUT_TPS43=y" in config) == right
    assert ("tps43.c.obj:" in ninja) == right
    if reset:
        print(f"{build}: settings reset, no trackpad/Braille processing: PASS")
        return

    assert "CONFIG_ZMK_POINTING=y" in config
    assert "CONFIG_ZMK_SPLIT=y" in config
    assert "CONFIG_INPUT_THREAD_STACK_SIZE=2048" in config
    assert ("CONFIG_ZMK_SPLIT_ROLE_CENTRAL=y" in config) == central
    assert ("CONFIG_ZMK_DISPLAY=y" in config) == (not right)
    if not right:
        check_display_geometry(values, dongle)
    transform = node("default_transform")
    expect("DT_CHOSEN_zmk_physical_layout", node("default_layout"))
    expect(node("default_layout") + "_P_transform_IDX_0_PH", transform)
    expect(node("default_layout") + "_P_keys_LEN", 42)
    expect(transform + "_P_map_LEN", 42)
    expect(transform + "_P_col_offset", 6 if right else 0)
    if dongle:
        check_prospector_memory(config)
        assert "CONFIG_ZMK_SPLIT_BLE_CENTRAL_PERIPHERALS=2" in config
        assert "CONFIG_BT_MAX_CONN=7" in config and "CONFIG_BT_MAX_PAIRED=7" in config
        assert "CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y" in config
        assert "CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_PROXY=y" in config
        assert "CONFIG_PROSPECTOR_USE_AMBIENT_LIGHT_SENSOR=y" not in config
        assert "CONFIG_PROSPECTOR_FIXED_BRIGHTNESS=50" in config
        expect("DT_CHOSEN_zmk_kscan", node("mock_kscan"))
        expect(node("mock_kscan") + "_P_rows", 0)
        expect(node("mock_kscan") + "_P_columns", 0)
        assert "kscan_gpio_matrix.c.obj:" not in ninja, "Dongle must not scan the keyboard GPIOs"
        assert "kscan_mock.c.obj:" in ninja
        assert re.search(r"^build .*prospector_adapter.*custom_status_screen\.c\.obj:", ninja, re.MULTILINE)
        assert "nice_view_gem/custom_status_screen.c.obj:" not in ninja
    else:
        expect("DT_CHOSEN_zmk_kscan", node("kscan0"))
        assert "CONFIG_ZMK_SLEEP=y" in config
        assert "CONFIG_ZMK_IDLE_TIMEOUT=30000" in config
        assert "CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=3600000" in config
    if left_peripheral:
        assert "CONFIG_SHIELD_NICE_VIEW_GEM=y" in config
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN=y" in config
        assert "CONFIG_NICE_VIEW_WIDGET_STATUS=y" not in config
        assert "CONFIG_ZMK_WPM=y" not in config
        assert "CONFIG_ZMK_WIDGET_BATTERY_STATUS=y" in config
        assert "CONFIG_ZMK_WIDGET_PERIPHERAL_STATUS=y" in config
        assert "nice_view/widgets/peripheral_status.c.obj:" not in ninja
        assert "nice_view_gem/custom_status_screen.c.obj:" not in ninja, "Central-only screen on a peripheral"
    for index, layer in enumerate(("base", "nav", "sym", "adj", "tap", "braille")):
        expect(f"DT_N_S_keymap_S_{layer}_CHILD_IDX", index)
        expect(f"DT_N_S_keymap_S_{layer}_P_bindings_LEN", 42)
    expect("DT_N_S_braille_P_default_mode", f'"{braille_mode}"')
    binding("base", 36, "braille_mode", 5)
    binding("base", 41, "momentary_layer", 2)
    for position, dot in ((13, 7), (14, 3), (15, 2), (16, 1),
                          (19, 4), (20, 5), (21, 6), (22, 8),
                          (25, 8), (26, 6), (27, 5), (28, 4),
                          (31, 1), (32, 2), (33, 3), (34, 7)):
        binding("braille", position, "braille_dot", dot)
    # Independent HID usages: Left, Esc, Up / Tab, Down, Enter, Right.
    for position, usage in ((1, 0x50), (2, 0x29), (3, 0x52),
                            (7, 0x2B), (8, 0x51), (9, 0x28), (10, 0x4F)):
        binding("braille", position, "key_press", (0x07 << 16) | usage)
    # Implicit left Shift on Tab, not a sticky or separately held modifier.
    binding("braille", 4, "key_press", (0x02 << 24) | (0x07 << 16) | 0x2B)
    binding("braille", 39, "braille_space")
    for position in (11, 36):
        binding("braille", position, "to_layer", 0)
    combo_layers = [value for key, value in values.items()
                    if re.fullmatch(r"DT_N_S_combos_S_combo_.*_P_layers_IDX_0", key)]
    assert combo_layers == ["0"] * 16, "Personal combos must remain BASE-only"

    split = node("trackpad_split")
    expect(split + ("_STATUS_disabled" if left_peripheral else "_STATUS_okay"), 1)
    listener = node("trackpad_listener")
    expect(listener + ("_STATUS_okay" if central else "_STATUS_disabled"), 1)
    expect(listener + "_P_device_IDX_0_PH", split)
    if right:
        trackpad = node("tps43_trackpad")
        expect(split + "_P_device_IDX_0_PH", trackpad)
        expect(trackpad + "_STATUS_okay", 1)
        assert int(values[trackpad + "_REG_IDX_0_VAL_ADDRESS"].split()[0], 0) == 0x74
        for prop in ("scroll", "zoom", "single_tap", "two_finger_tap", "press_and_hold",
                     "three_finger_swipe", "switch_xy", "invert_scroll_y",
                     "enable_power_management"):
            expect(trackpad + "_P_" + prop, 1)
        expect(trackpad + "_P_idle_sleep", 0)
        expect(trackpad + "_P_three_finger_swipe_throttle_ms", 1200)
        expect(trackpad + "_P_report_rate_lp2", 640)
        expect(trackpad + "_P_rst_gpios_IDX_0_PH", "DT_N_S_soc_S_gpio_50000300")
        expect(trackpad + "_P_rst_gpios_IDX_0_VAL_pin", 14)
        expect(trackpad + "_P_rdy_gpios_IDX_0_PH", "DT_N_S_soc_S_gpio_50000000")
        expect(trackpad + "_P_rdy_gpios_IDX_0_VAL_pin", 2)
    if central:
        assert split + "_P_device_IDX_0_PH" not in values, "Central must receive split input, not own a TPS43"
        processors = ("zip_xy_scaler", "zip_scroll_scaler", "zip_zoom_mapper",
                      "touch_processor", "swipe_button_mapper")
        expect(listener + "_P_input_processors_LEN", len(processors))
        for index, label in enumerate(processors):
            expect(f"{listener}_P_input_processors_IDX_{index}_PH", node(label))
        # Keep touch release processing after a NAV/SYM override, without
        # scaling native scrolling twice or forwarding TOUCH as a left click.
        expect(listener + "_S_scroller_P_process_next", 1)
        expect(listener + "_S_scroller_P_input_processors_LEN", 2)
        expect(listener + "_S_scroller_P_input_processors_IDX_0_PH", node("zip_xy_transform"))
        expect(listener + "_S_scroller_P_input_processors_IDX_1_PH", node("zip_xy_to_scroll_mapper"))
        expect(node("touch_processor") + "_P_bindings_IDX_0_VAL_param1", 4)
        expect(node("zip_zoom_mapper") + "_P_event_code", 9)  # INPUT_REL_MISC
        expect(node("swipe_button_mapper") + "_P_bindings_LEN", 4)
        assert "CONFIG_ZMK_DISPLAY=y" in config
        assert "zmk-input-zoom" in ninja
        if left:
            assert "CONFIG_ZMK_WPM=y" in config
            assert "nice_view_gem/custom_status_screen.c.obj:" in ninja
        link_map = (build / "zephyr/zmk.map").read_text()
        for symbol in ("braille_input_dispatch", "braille_chord_discard",
                       "braille_rules_ueb1_characters", "braille_rules_computer8_characters",
                       "braille_tables_select"):
            assert symbol in link_map, f"Braille symbol not linked: {symbol}"
        for behavior in ("braille_dot", "braille_space", "braille_mode", "key_press", "sticky_key"):
            ordinal = values[f"DT_N_S_behaviors_S_{behavior}_ORD"]
            assert f"._zmk_behavior_ref.static.zmk_behavior___device_dts_ord_{ordinal}_" in link_map
    role = "Prospector central" if dongle else "standalone central" if left else "peripheral"
    print(f"{build}: Toucan2 {role}, devices, split input, personal keymap and Braille: PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--braille-mode", default="ueb1")
    parser.add_argument("builds", type=Path, nargs="+")
    args = parser.parse_args()
    for build in args.builds:
        check(build, args.braille_mode)


if __name__ == "__main__":
    main()
