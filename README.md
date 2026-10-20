# ZMK config for beekeeb Toucan2 Keyboard

[The beekeeb Toucan2 Keyboard] is a wireless split 42-key column-stagger keyboard
with a display and a multi-touch trackpad. This config targets a V1 upgraded with
the **V2 thumb-aligned trackpad kit**, not the original round Cirque trackpad.

## Firmware versions

`config/west.yml` pins a ZMK `main` snapshot
[`4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85`](https://github.com/zmkfirmware/zmk/commit/4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85)
using **Zephyr 4.1** and LVGL 9.3. The CI reusable workflow uses the same ZMK
revision and its `zmkfirmware/zmk-build-arm:stable` environment. “4.1” is the
**Zephyr version**, not a ZMK release number; this replaces ZMK v0.3.0 / Zephyr 3.5.
All five build targets now use **`xiao_ble//zmk`**, replacing `seeeduino_xiao_ble`.

Prospector is pinned to the supplied `feat/new-status-screens` checkout at
[`ed98221f3b52b7066dbb10ba3af8a29150b93a5a`](https://github.com/carrefinho/prospector-zmk-module/commit/ed98221f3b52b7066dbb10ba3af8a29150b93a5a).
This upstream branch is a work in progress; both development snapshots are pinned
instead of silently following branch updates. The RGB LED module is also updated to a
Zephyr 4.1-compatible snapshot for the new board name and endpoint API.
Toucan's own display keeps its layouts and 144×168 geometry, with LVGL 9 canvas
helpers, image descriptors, and an explicit one-byte-per-pixel canvas buffer.
The halves also explicitly enable P0.09/P0.10 as GPIOs in devicetree, replacing
the old board's NFC-pin Kconfig default.

Rebuild and reflash **every device in the selected profile** when upgrading from
the older Zephyr 3.5 firmware; do not mix old and new split firmware. Hardware
acceptance (BLE, displays, gestures, sleep/wake) is still required after flashing.

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

`config/west.yml` also pins `zmk-braille-module` at
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
It targets the original **XIAO nRF52840 Prospector**, using the pinned
`feat/new-status-screens` branch snapshot and Zephyr 4.1 ZMK described above.

There are two **firmware profiles**, not an automatic runtime fallback:

| Profile | Central (keymap, Braille, trackpad processing, Studio) | Peripherals | Host connection |
| --- | --- | --- | --- |
| `standalone` (default, existing behavior) | Toucan left | Toucan right | Left USB or Bluetooth |
| `prospector` | Prospector | Toucan left and right | Prospector USB (or its Bluetooth profiles) |

**Unplugging the Prospector does not make the peripheral left become a central.**
ZMK fixes split roles at build time. To go without the dongle again, reset
pairings and reflash the standalone profile below. Both profiles are built by CI;
all six layers, combos, Braille bindings, and TPS43 gestures share the same sources.
A third-party Prospector *scanner* firmware is a different architecture, not the
official dongle integration implemented here.

### Firmware and displays

- Standalone left: `toucan_left rgbled_adapter nice_view_gem`, retaining the
  Studio USB snippet. Default CI artifact names now contain `xiao_ble__zmk`;
  `scripts/build-and-load` accepts both new and legacy board-qualified names.
- Prospector left: `toucan_left_peripheral-zmk.uf2`, built with
  `toucan_left_peripheral rgbled_adapter nice_view_gem`. It keeps the Toucan's
  **144×168 panel definition**, with ZMK's built-in peripheral battery/connection
  screen instead of the central-only layer/WPM/host widgets. Do not substitute
  the stock `nice_view` shield: its 160×68 geometry causes display corruption.
  The standalone screen retains its existing layout.
- Prospector: `toucan_prospector-zmk.uf2`, built with
  `toucan_dongle prospector_adapter` and the Studio USB snippet. The LCD shows
  named layers (`BASE`, `NAV`, `SYM`, `ADJ`, `TAP`, `BRL`), both peripheral batteries
  and connection status. Open Studio against the **dongle**, not the left half.
- Right: the `toucan_right rgbled_adapter` image is shared by both
  profiles. Its firmware is identical, but its stored split bond must be reset
  when changing centrals.
- Settings reset: the XIAO `settings_reset` image works on all three
  devices. It is destructive: it clears bonds and saved settings/Studio edits.

The dongle uses a mock scanner and the exact same physical layout, matrix
transform and split-input listener as the standalone central. It has two split
peripheral slots plus five host profiles. Only the right half runs the TPS43
hardware driver; only the active central processes Braille and gestures.

The dongle declares **500 ppm LF-clock accuracy** in `toucan_dongle.conf`.
On the tested XIAO Prospector, the original 50 ppm declaration understated the
measured clock drift; changing only this declaration fixed the recurring split
connection timeouts and restored typing from both halves. It changes BLE timing
allowances, not the clock source, PHY, peripheral latency, or stored pairings.

The new branch provides four screen layouts. **Operator** is selected in
`boards/shields/toucan/toucan_dongle.conf`. To choose another, replace
`CONFIG_PROSPECTOR_STATUS_SCREEN_OPERATOR=y` with exactly one of:

```ini
CONFIG_PROSPECTOR_STATUS_SCREEN_CLASSIC=y
CONFIG_PROSPECTOR_STATUS_SCREEN_RADII=y
CONFIG_PROSPECTOR_STATUS_SCREEN_FIELD=y
```

Do not enable multiple layouts at once. The branch also adds modifier and caps-word
indicators; see the [Prospector module instructions] for layout-specific options.

The Prospector reserves a **32 KiB LVGL heap**, **two quarter-screen draw
buffers** (half a screen combined), and an **8 KiB display stack**. The heap
budget is retained from the earlier firmware: hardware testing found allocation
failures during battery-bar fades with its default 10 KB heap, matching
[this upstream report](https://github.com/carrefinho/prospector-zmk-module/issues/7#issuecomment-3535137446).
The new branch defaults to double buffering; using two half-screen buffers would
exhaust RAM with this heap. These memory settings apply only to the dongle and do
not change either panel's geometry. Toucan's LVGL 9 display uses the updated
upstream heap defaults (8 KiB custom screen / 5 KiB built-in peripheral screen).

On the peripheral left's screen, the waves + tick mean a low-level split Bluetooth
connection, **not** successful encryption or working input to the host. A tick can
therefore appear during a connection attempt that subsequently fails. The dongle
also clears a peripheral's reported battery to zero on disconnect; a brief 0%
reading is not necessarily a discharged battery.

Brightness defaults to a fixed 50%, with the optional ambient-light sensor
**disabled**, so kits without an APDS9960 also work. Change
`boards/shields/toucan/toucan_dongle.conf` to set
`CONFIG_PROSPECTOR_FIXED_BRIGHTNESS` (1–100), or set
`CONFIG_PROSPECTOR_USE_AMBIENT_LIGHT_SENSOR=y` and remove fixed brightness if the
sensor is installed.

### Guided local Operator flasher (macOS)

Run **`scripts/flash-prospector`** for the terminal wizard. Its prepared local
bundle lives in `.firmware/prospector-operator/` (ignored by Git), so it can flash
these uncommitted changes without waiting for CI. It validates the Operator
layout, compiled roles, matching ZMK/Zephyr versions, UF2 structure, checksums, and
source fingerprint before using the bundle. `--dry-run` validates/lists it without
accessing any USB devices.

Choose **1 — clean setup** when switching centrals, clearing broken bonds, or
starting fresh. This explicitly asks you to type `ERASE`, then guides you through
settings-reset + normal firmware on **dongle, left, right**, one device at a time.
It erases split/host bonds and Studio edits on all three. Choose **2 — update**
only for an already-paired Prospector set; this never resets settings.

Keep the other two devices **off**, use a USB **data** cable, and double-tap the
physical reset button when prompted. Before each write, the wizard checks that
exactly one XIAO nRF52840 bootloader is mounted and asks you to confirm the device
name. It cannot distinguish these identical controllers electrically, so check
which physical device is connected. Use your Mac/another keyboard while flashing.
Afterwards it walks you through powering the dongle, then **left first**, then
right. `q` at a prompt or Ctrl-C cancels; completed resets/writes are not undone.

**Resume / skip steps:** enter **`s`** (or `skip`) at any settings-reset or firmware
prompt, including the device-name confirmation, to skip **only that write**.
Skipped steps never copy firmware or erase settings; skip at the first prompt
to avoid waiting for a drive too. They are listed in the final summary rather
than marked as verified. Rerun the wizard in the **same mode** and skip work
already completed with this exact bundle. For example, if the dongle's reset and
firmware writes are already done, choose **1 — clean setup**, confirm `ERASE`, and
enter `s` at both dongle steps to resume at the left half's settings reset. Do not
switch to update mode if either half still needs its settings reset. Keep skipped
devices off/disconnected too.

The controllers reboot and disconnect immediately after accepting UF2 data,
**without a clean eject**. This is expected, including macOS's “Disk Not Ejected
Properly” notification. The wizard tolerates copy/sync errors when the bootloader
disappears during the write; errors with the drive still mounted remain fatal.
A disconnect is not proof of working runtime firmware: check displays and input
afterwards.

To refresh the bundle after firmware-source changes, first rebuild all four
Prospector-profile targets with west (as below), then package them:

```sh
scripts/flash-prospector --prepare-from /absolute/path/to/west/build
scripts/flash-prospector --dry-run
scripts/flash-prospector
```

The preparer accepts `toucan-prospector`, `toucan-left-peripheral`, `toucan-right`,
and `toucan-reset` build directories, or the short names `prospector`,
`left-peripheral`, `right`, and `reset`. Build directories must be up to date.
Use `--firmware-dir PATH` to prepare/use a different bundle directory. The wizard
refuses an old bundle after keymap, manifest, shield, or display-source edits.

### First setup / switching to Prospector (CI artifacts)

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
Prospector central, and settings reset using the pinned Zephyr 4.1 ZMK snapshot.
Push these changes and wait for the GitHub Actions build to succeed, then use
`scripts/build-and-load`
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
west build -p always -s zmk/app -d build/toucan-left -b xiao_ble//zmk \
  -S studio-rpc-usb-uart -- -DZMK_CONFIG="$REPO/config" \
  -DZMK_EXTRA_MODULES="$REPO" \
  -DSHIELD="toucan_left rgbled_adapter nice_view_gem" -DCONFIG_ZMK_STUDIO=y
west build -p always -s zmk/app -d build/toucan-right -b xiao_ble//zmk \
  -- -DZMK_CONFIG="$REPO/config" -DZMK_EXTRA_MODULES="$REPO" \
  -DSHIELD="toucan_right rgbled_adapter"
west build -p always -s zmk/app -d build/toucan-reset -b xiao_ble//zmk \
  -- -DZMK_CONFIG="$REPO/config" -DZMK_EXTRA_MODULES="$REPO" -DSHIELD=settings_reset

# Optional Prospector profile (the right image above is shared).
west build -p always -s zmk/app -d build/toucan-left-peripheral -b xiao_ble//zmk \
  -- -DZMK_CONFIG="$REPO/config" -DZMK_EXTRA_MODULES="$REPO" \
  -DSHIELD="toucan_left_peripheral rgbled_adapter nice_view_gem"
west build -p always -s zmk/app -d build/toucan-prospector -b xiao_ble//zmk \
  -S studio-rpc-usb-uart -- -DZMK_CONFIG="$REPO/config" \
  -DZMK_EXTRA_MODULES="$REPO" -DSHIELD="toucan_dongle prospector_adapter" \
  -DCONFIG_ZMK_STUDIO=y
python3 "$REPO/scripts/check-builds.py" build/toucan-left build/toucan-right \
  build/toucan-reset build/toucan-left-peripheral build/toucan-prospector
```

Use the Zephyr 4.1-compatible ZMK build environment (the pinned workflow's
`zmkfirmware/zmk-build-arm:stable` image), not the old `:3.5` image. In the generated
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
  [Prospector module instructions]: https://github.com/carrefinho/prospector-zmk-module/tree/ed98221f3b52b7066dbb10ba3af8a29150b93a5a
