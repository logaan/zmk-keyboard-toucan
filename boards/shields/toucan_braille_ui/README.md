# Toucan braille dashboard

An original 240×280 screen for the Toucan Prospector dongle. Add
`toucan_braille_ui` after `toucan_dongle prospector_adapter`; the build matrix
already does this. It uses Prospector's panel and backlight drivers but none
of its existing status screens or widgets. The companion shield removes the
vendor screen source at configure time and supplies its own screen.

The top row shows both half batteries; unknown readings display `--`, and
disconnected halves display `offline` instead of stale percentages. B1 and B2 correspond to split slots 0 and 1 (pairing order), not assumed physical sides.
The endpoint row shows the preferred Bluetooth channel (numbered 1–5) or USB,
connection state, and any active fallback transport. CTRL/SHIFT/ALT/CMD reflect
the effective HID modifier report, including sticky modifiers.

The middle shows the current keyboard/braille layer and translation mode.
While braille is active, the large text previews the **currently held** dots
using the actual active translation rules, pending cells, and UEB context.
Releasing one dot updates this preview even though chord capture retains that
dot for the eventual committed chord. Ambiguous translations are marked
`provisional`; prefixes and unmapped cells are explicit. Previewing never sends
host input or modifies the translation context.

BUFFER shows actual pending cell dot numbers, with `s` for braille space.
Long buffers scroll rather than disappearing. It clears when input is committed,
discarded, or reset. The bottom line briefly reports dropped incomplete input or
reserved Computer8 cells. Input snapshots are collected on the central system
work queue and copied under a spinlock; LVGL renders the copy on its display
queue, refreshed every 50 ms. The engine and preview stay on the input queue.

`CONFIG_TOUCAN_BRAILLE_UI_LAYER` defaults to 5, matching the Toucan keymap.
The middle/lower content region is available for the on-device settings flow;
the top battery/endpoint/modifier area should remain visible during settings.

Validate a real build with `python3 scripts/check-braille-dashboard.py BUILD`.
Physical panel readability, battery slot assignment and host connection changes
still require hardware acceptance; no keyboard is flashed by the checks.
