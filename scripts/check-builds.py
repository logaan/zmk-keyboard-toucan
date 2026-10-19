#!/usr/bin/env python3
"""Check resolved Toucan2 builds (not a hardware/gesture runtime test).

Usage: python3 scripts/check-builds.py /west/build/left /west/build/right /west/build/reset
Use --braille-mode computer8 for a test-only default-mode override build.
"""

import argparse
from pathlib import Path
import re


def check(build, braille_mode):
    config = set((build / "zephyr/.config").read_text().splitlines())
    ninja = (build / "build.ninja").read_text()
    header = (build / "zephyr/include/generated/devicetree_generated.h").read_text()
    values = dict(re.findall(r"^#define (\S+)[ \t]+(.+)$", header, re.MULTILINE))
    central = "CONFIG_SHIELD_TOUCAN_LEFT=y" in config
    peripheral = "CONFIG_SHIELD_TOUCAN_RIGHT=y" in config
    reset = "CONFIG_SHIELD_SETTINGS_RESET=y" in config
    assert sum((central, peripheral, reset)) == 1, "Not a Toucan half or settings-reset build"
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
    assert ("CONFIG_INPUT_TPS43=y" in config) == peripheral
    assert ("tps43.c.obj:" in ninja) == peripheral
    if reset:
        print(f"{build}: settings reset, no trackpad/Braille processing: PASS")
        return

    assert "CONFIG_ZMK_POINTING=y" in config
    assert "CONFIG_ZMK_SPLIT=y" in config
    assert "CONFIG_INPUT_THREAD_STACK_SIZE=2048" in config
    assert ("CONFIG_ZMK_SPLIT_ROLE_CENTRAL=y" in config) == central
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
    if peripheral:
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
    else:
        listener = node("trackpad_listener")
        expect(listener + "_STATUS_okay", 1)
        expect(listener + "_P_device_IDX_0_PH", split)
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
        assert "zmk-input-zoom" in ninja and "nice_view_gem" in ninja
        link_map = (build / "zephyr/zmk.map").read_text()
        for symbol in ("braille_input_dispatch", "braille_chord_discard",
                       "braille_rules_ueb1_characters", "braille_rules_computer8_characters",
                       "braille_tables_select"):
            assert symbol in link_map, f"Braille symbol not linked: {symbol}"
        for behavior in ("braille_dot", "braille_space", "braille_mode", "key_press", "sticky_key"):
            ordinal = values[f"DT_N_S_behaviors_S_{behavior}_ORD"]
            assert f"._zmk_behavior_ref.static.zmk_behavior___device_dts_ord_{ordinal}_" in link_map
    print(f"{build}: Toucan2 devices, split input, personal keymap and Braille: PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--braille-mode", default="ueb1")
    parser.add_argument("builds", type=Path, nargs="+")
    args = parser.parse_args()
    for build in args.builds:
        check(build, args.braille_mode)


if __name__ == "__main__":
    main()
