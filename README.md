# ZMK config for beekeeb Toucan Keyboard

[The beekeeb Toucan Keyboard] is a wireless split 42-key column‑stagger keyboard
that a display and a trackpad, with an aggressive stagger on the pinky columns.

## Pinned Braille input

`config/west.yml` pins ZMK v0.3.0 and a published `zmk-braille-module` commit.
West discovers the module automatically. Only `toucan_left.conf` in the shield
enables processing; the right half keeps forwarding physical positions.

The existing QWERTY, NAV, SYM, ADJ, and TAP layers remain at indices 0–4.
The left outer thumb (formerly a duplicate SYM key) is now `&bmode BRAILLE`:
hold for Braille chording, tap to stay on Braille layer 5. The right outer thumb
still reaches SYM. On BRL, physical `f d s` are dots 1 2 3, `j k l` are 4 5 6,
`a` is 7, `;` is 8, and the ordinary Space position becomes Braille space.
The left outer thumb or top-right key explicitly returns to BASE (`&to BASE`).
BASE-only number/bracket combos do not apply on BRL. Its named default character
mode is `ueb1`; the layer key does not select a character table.

The pinned module enters BRL through the mode key, captures each chord on its
final Braille-key release, and types the 26 lowercase six-dot alphabet letters
in `ueb1`. Braille space alone types a literal space; sourced factory commands
provide navigation, Tab/Return/Delete, and sticky modifiers. See the pinned
module's [factory command table](https://github.com/logaan/zmk-braille-module/blob/66c72c23bb98fce08ec993d3797c7711533c2879/src/braille_rules_nav.c)
for the exact chords; Globe is not Apple's Fn modifier. Literary signs, a settings UI, and
persistence are not implemented yet. Conventional typing, Studio, display, and
pointing remain configured. Software verification does not replace physical
keyboard/macOS/BLE acceptance, which is still pending.

The existing CI firmware matrix includes both halves and settings reset. For
repeatable local Docker 3.5 builds on the shared pinned workspace, see
`scripts/smoke-build` in the Braille module repository. It checks generated
configuration, Perkins bindings, linked devices, and a test-only `computer8`
`default-mode` override without changing this keyboard's `ueb1` default.

## License

The code in this repo is available under the MIT license.

The included shield nice_view_gem is modified from
<https://github.com/M165437/nice-view-gem> licensed under the MIT License.

ZMK code snippets are taken from the ZMK documentation under the MIT license.

The embedded font QuinqueFive is designed by GGBotNet, licensed under under the
SIL Open Font License, Version 1.1.

  [The beekeeb Toucan Keyboard]: https://beekeeb.com/toucan-keyboard/
