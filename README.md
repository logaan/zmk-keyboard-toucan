# ZMK config for beekeeb Toucan2 Keyboard

[The beekeeb Toucan2 Keyboard] is a wireless split 42-key column-stagger keyboard
with a display and a multi-touch trackpad. This config targets a V1 upgraded with
the **V2 thumb-aligned trackpad kit**, not the original round Cirque trackpad.

## Toucan2 hardware and gestures

Hardware and display support are based on [beekeeb's Toucan2 firmware] at
`6882c95bec5be89988e90feb621f78a7511e9ed7`. The keyboard matrix, all six personal
keymap layers, combos, and hold-taps are retained. Shield names remain
`toucan_left` / `toucan_right`, so the existing build matrix still applies.

The right half now uses the **Azoteq TPS43 over I2C**: SDA P1.13, SCL P1.15,
reset P1.14, ready P0.02, address `0x74`. The manifest replaces the V1 Cirque driver
with pinned versions of beekeeb's `zmk_driver_azoteq` and `zmk-input-zoom` modules.
The Azoteq pin is from **`main`**, which supports throttled three-finger swipes;
the repository's older default `master` branch does not.

Enabled trackpad features:

- One-finger pointer movement and tap-to-left-click.
- Two-finger horizontal/vertical scrolling and tap-to-right-click.
- Press and hold for dragging (500 ms).
- Pinch-to-zoom, mapped to macOS Command-minus / Command-equals.
- Three-finger directional swipes, mapped to Control-Command-arrow shortcuts
  using beekeeb's defaults, throttled to one action per 1.2 seconds. Adjust these
  bindings to match your host's Mission Control / Spaces shortcuts if needed.
- The existing TAP mouse-button layer while touching the pad, and NAV/SYM
  one-finger scrolling. Touch releases are processed even when layers change;
  Braille layer 5 still takes priority over TAP layer 4.

Tune gestures, sensitivity, natural-scroll direction, and thumb-aligned orientation
in `boards/shields/toucan/toucan_right.overlay`. Tune pointer/scroll scaling, zoom,
and swipe bindings in `boards/shields/toucan/toucan.dtsi`. Two-finger scrolling
works without holding NAV or SYM. These are mouse/keyboard events, **not a native
macOS multi-touch digitizer**; pinch uses application zoom shortcuts.

Both halves keep the 30-second idle / one-hour deep-sleep timeouts. The TPS43 uses
its own low-power modes while idle (640 ms LP2 report interval) and suspends for
deep sleep. `idle-sleep` is deliberately omitted so the pad remains usable while
ZMK is idle. The obsolete Cirque sleep/soft-off settings have been removed.

The display now includes the V2 status-screen options. Set
`CONFIG_TOUCAN_STATUS_SCREEN` in `boards/shields/toucan/toucan_left.conf` to
`0` (original), `1` (Toucan logo), or `2` (WPM graph, the V2 default).
Studio, smooth scrolling, battery reporting, and the RGB LED widget remain enabled.
Hardware defaults live in the shield `.conf` files; the redundant, broken
`config/toucan_{left,right}.conf` symlinks have been removed.

## Pinned Braille input

`config/west.yml` pins ZMK v0.3.0 and `zmk-braille-module` at
[`86a25867cf27f6d2d7b25e8ef17066d91c202e2a`](https://github.com/logaan/zmk-braille-module/commit/86a25867cf27f6d2d7b25e8ef17066d91c202e2a),
the latest pushed `main` snapshot when this pin was updated. West discovers the
module automatically. The central's shield config (`toucan_left.conf` for
standalone, `toucan_dongle.conf` for Prospector) enables processing; peripheral
halves keep forwarding physical positions.

The existing QWERTY, NAV, SYM, ADJ, and TAP layers remain at indices 0–4.
The left outer thumb (formerly a duplicate SYM key) is now `&bmode BRAILLE`:
hold for Braille chording, tap to stay on Braille layer 5. The right outer thumb
still reaches SYM. On BRL, physical `f d s` are dots 1 2 3, `j k l` are 4 5 6,
`a` is 7, `;` is 8, and the ordinary Space position becomes Braille space.
Navigation sits above these dots, with alternate Braille dot keys below:

| Row (physical keys) | Left, left to right | Right, left to right |
| --- | --- | --- |
| Above (`Q W E R` / `U I O P`) | Left, Esc, Up, Shift-Tab | Tab, Down, Enter, Right |
| Home (`A S D F` / `J K L ;`) | Dots 7, 3, 2, 1 | Dots 4, 5, 6, 8 |
| Below (`Z X C V` / `M , . /`) | Dots 8, 6, 5, 4 | Dots 1, 2, 3, 7 |

Shift-Tab uses `&kp LS(TAB)`: Shift is held with Tab and released when Tab is
released, without leaving a sticky modifier behind. Other layers are unchanged.
The left outer thumb or top-right key explicitly returns to BASE (`&to BASE`).
BASE-only number/bracket combos do not apply on BRL. Its named default character
mode is `ueb1`; the layer key does not select a character table.

The pinned module enters BRL through the mode key and captures each chord on its
final Braille-key release. Its `ueb1` table includes the 26 lowercase six-dot
alphabet letters, seven context-free punctuation signs, and 21 two-cell symbols.
It also includes the stateless `computer8` table covering all 94 printable
non-space ASCII characters; this keyboard still defaults to `ueb1`.
Braille space alone types a literal space; sourced factory commands provide
navigation, Tab/Return/Delete, and sticky modifiers. See the pinned module's
[factory command table](https://github.com/logaan/zmk-braille-module/blob/86a25867cf27f6d2d7b25e8ef17066d91c202e2a/src/braille_rules_nav.c)
for the exact chords; Globe is not Apple's Fn modifier. Contextual UEB input,
a settings UI, and persistence remain unimplemented in this published snapshot.
Conventional typing, Studio, display, and pointing remain configured. Software
verification does not replace physical keyboard/macOS/BLE acceptance, which is
still pending.

## Optional Prospector dongle

This follows the [official ZMK dongle guide] and the [Prospector module instructions].
It targets the original **XIAO nRF52840 Prospector**, using the module's pinned
ZMK v0.3 / Zephyr 3.5 branch, without upgrading this keyboard's ZMK version.

There are two **firmware profiles**, not an automatic runtime fallback:

| Profile | Central (keymap, Braille, trackpad processing, Studio) | Peripherals | Host connection |
| --- | --- | --- | --- |
| `standalone` (default, existing behavior) | Toucan left | Toucan right | Left USB or Bluetooth |
| `prospector` | Prospector | Toucan left and right | Prospector USB (or its Bluetooth profiles) |

**Unplugging the Prospector does not make the peripheral left become a central.**
ZMK v0.3 fixes split roles at build time. To go without the dongle again, reset
pairings and reflash the standalone profile below. Both profiles are built by CI;
all six layers, combos, Braille bindings, and TPS43 gestures share the same sources.
A third-party Prospector *scanner* firmware is a different architecture, not the
official dongle integration implemented here.

### Firmware and displays

- Standalone left: `toucan_left rgbled_adapter nice_view_gem` (unchanged filename
  and Studio USB snippet).
- Prospector left: `toucan_left_peripheral-zmk.uf2`, built with
  `toucan_left_peripheral rgbled_adapter nice_view_gem`. It keeps the Toucan's
  **144×168 panel definition**, with ZMK's built-in peripheral battery/connection
  screen instead of the central-only layer/WPM/host widgets. Do not substitute
  the stock `nice_view` shield: its 160×68 geometry causes display corruption.
  The standalone screen is unchanged.
- Prospector: `toucan_prospector-zmk.uf2`, built with
  `toucan_dongle prospector_adapter` and the Studio USB snippet. The LCD shows
  named layers (`BASE`, `NAV`, `SYM`, `ADJ`, `TAP`, `BRL`), both peripheral batteries
  and connection status. Open Studio against the **dongle**, not the left half.
- Right: the existing `toucan_right rgbled_adapter` image is shared by both
  profiles. Its firmware is identical, but its stored split bond must be reset
  when changing centrals.
- Settings reset: the existing XIAO `settings_reset` image works on all three
  devices. It is destructive: it clears bonds and saved settings/Studio edits.

The dongle uses a mock scanner and the exact same physical layout, matrix
transform and split-input listener as the standalone central. It has two split
peripheral slots plus five host profiles. Only the right half runs the TPS43
hardware driver; only the active central processes Braille and gestures.

Brightness defaults to a fixed 50%, with the optional ambient-light sensor
**disabled**, so kits without an APDS9960 also work. Change
`boards/shields/toucan/toucan_dongle.conf` to set
`CONFIG_PROSPECTOR_FIXED_BRIGHTNESS` (1–100), or set
`CONFIG_PROSPECTOR_USE_AMBIENT_LIGHT_SENSOR=y` and remove fixed brightness if the
sensor is installed.

### First setup / switching to Prospector

1. Push the config and wait for a successful CI build. Preview the selection with
   `scripts/build-and-load --profile prospector --dry-run` (no devices are flashed).
2. Turn **all three devices off**. With only one connected/powered at a time,
   flash `scripts/build-and-load reset`, then its normal Prospector-profile image:
   `scripts/build-and-load --profile prospector dongle` for the Prospector,
   `scripts/build-and-load --profile prospector left` for the left half, and
   `scripts/build-and-load --profile prospector right` for the right half.
   After each device, disconnect/power it off before proceeding to the next.
   **Reset every device**, not just the former central; a normal firmware update
   or `BT_CLR` does not reset all split bonds. Save any Studio edits first.
3. Connect the Prospector to the computer with a **USB data cable**. Power on
   **left first**, wait for it to connect, then power on right. The Prospector's
   battery-bar order follows pairing order, so do not pair the right first.
4. Check typing from both halves, Braille, all trackpad gestures and the LCD's
   layer/battery indicators. To use Studio, connect it to the Prospector and
   unlock with the existing ADJ Studio-unlock keys.

Use the physical reset buttons (double-tap) during conversion; the keymap's
bootloader bindings need a working split connection and target the originating
keyboard half, **not the dongle**. Mount only the device you intend to flash.

For routine updates *after pairing in Prospector mode*, no settings reset is
needed: `scripts/build-and-load --profile prospector` flashes dongle, left, right.
It never resets settings implicitly.

### Returning to standalone

Keep the Prospector disconnected. Reset both halves one at a time (as above),
then flash `scripts/build-and-load --profile standalone` (or just
`scripts/build-and-load`): left regains the central role, right pairs to left.
If connecting directly over Bluetooth, forget the old Toucan host pairing and
pair it again after the reset. Clear the Prospector's settings too before
reintroducing it on a later switch to dongle mode.

## Building and flashing

The CI matrix builds standalone left, shared right, Prospector peripheral left,
Prospector central, and settings reset using ZMK v0.3.0. Push these changes and
wait for the GitHub Actions build to succeed, then use `scripts/build-and-load`
to flash the desired profile. With no arguments it still flashes the original
standalone **left then right**. Both central images retain the
`studio-rpc-usb-uart` snippet. Settings reset is normally unnecessary for routine
same-profile updates; it **is required when changing split roles**, as above.

To reach the bootloader using this keymap, hold NAV (`F` or `;`) and SYM (the
right outer thumb), then press the left or right outer home-row key on ADJ for
that half. Alternatively, double-tap the reset button on the half being flashed.

For local builds, initialize/update a west workspace from `config/west.yml`,
then build from its root with this repo loaded as a keyboard module:

```sh
# Set REPO to the absolute path of this checkout, after west init / west update.
west zephyr-export
west build -p always -s zmk/app -d build/toucan-left -b seeeduino_xiao_ble \
  -S studio-rpc-usb-uart -- -DZMK_CONFIG="$REPO/config" \
  -DZMK_EXTRA_MODULES="$REPO" \
  -DSHIELD="toucan_left rgbled_adapter nice_view_gem" -DCONFIG_ZMK_STUDIO=y
west build -p always -s zmk/app -d build/toucan-right -b seeeduino_xiao_ble \
  -- -DZMK_CONFIG="$REPO/config" -DZMK_EXTRA_MODULES="$REPO" \
  -DSHIELD="toucan_right rgbled_adapter"
west build -p always -s zmk/app -d build/toucan-reset -b seeeduino_xiao_ble \
  -- -DZMK_CONFIG="$REPO/config" -DZMK_EXTRA_MODULES="$REPO" -DSHIELD=settings_reset

# Optional Prospector profile (the right image above is shared).
west build -p always -s zmk/app -d build/toucan-left-peripheral -b seeeduino_xiao_ble \
  -- -DZMK_CONFIG="$REPO/config" -DZMK_EXTRA_MODULES="$REPO" \
  -DSHIELD="toucan_left_peripheral rgbled_adapter nice_view_gem"
west build -p always -s zmk/app -d build/toucan-prospector -b seeeduino_xiao_ble \
  -S studio-rpc-usb-uart -- -DZMK_CONFIG="$REPO/config" \
  -DZMK_EXTRA_MODULES="$REPO" -DSHIELD="toucan_dongle prospector_adapter" \
  -DCONFIG_ZMK_STUDIO=y
python3 "$REPO/scripts/check-builds.py" build/toucan-left build/toucan-right \
  build/toucan-reset build/toucan-left-peripheral build/toucan-prospector
```

Use the ZMK 3.5 build environment for this pinned release. In the generated
`.config`, check `CONFIG_INPUT_TPS43=y` on the right and
`CONFIG_ZMK_FEATURE_BRAILLE=y`, Studio, and smooth scrolling on the **central**
(standalone left or Prospector), never the peripherals.
`scripts/check-builds.py` checks the compiled devices, roles, split-input routing,
gesture flags, six-layer keymap, shared layout, Perkins bindings, BASE-only combos,
linked Braille behaviors, display selection and panel dimensions, dongle connection
slots and UF2 output.
The checker also accepts `--braille-mode computer8` for test-only override builds;
normal firmware stays on `ueb1`. Run `python3 -m unittest discover -s tests -v`
for hardware-free flashing-script profile tests (also run by CI); the flasher's
`--dry-run` downloads/lists images without flashing.
The Braille module's older smoke checker expects a V1 Pinnacle driver on the
right and must not be used unchanged for V2.
Compilation does not verify physical trackpad orientation, gesture feel, BLE,
sleep/wake, or Braille typing; test these on the upgraded keyboard after flashing.

## License

The code in this repo is available under the MIT license.

The included shield nice_view_gem is modified from
<https://github.com/M165437/nice-view-gem> and beekeeb's Toucan2 firmware, licensed
under the MIT License. The linked Azoteq driver is based on
<https://github.com/geeksville/zmk_driver_azoteq>.

ZMK code snippets are taken from the ZMK documentation under the MIT license.

The embedded font QuinqueFive is designed by GGBotNet, licensed under under the
SIL Open Font License, Version 1.1.

  [The beekeeb Toucan2 Keyboard]: https://beekeeb.com/introducing-toucan2/
  [beekeeb's Toucan2 firmware]: https://github.com/beekeeb/zmk-keyboard-toucan2/tree/6882c95bec5be89988e90feb621f78a7511e9ed7
  [official ZMK dongle guide]: https://zmk.dev/docs/hardware-integration/dongle
  [Prospector module instructions]: https://github.com/carrefinho/prospector-zmk-module/tree/77a852293532879c992847e01db27abe4f94fa9f
