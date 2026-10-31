#!/usr/bin/env python3
"""Verify the actual linked dashboard firmware, without touching hardware."""
from pathlib import Path
import re
import sys

def check(build):
    config = (build / 'zephyr/.config').read_text()
    ninja = (build / 'build.ninja').read_text()
    for setting in ('SHIELD_TOUCAN_BRAILLE_UI', 'PROSPECTOR_STATUS_SCREEN_BRAILLE',
                    'ZMK_DISPLAY_STATUS_SCREEN_CUSTOM', 'ZMK_FEATURE_BRAILLE'):
        assert f'CONFIG_{setting}=y' in config, setting
    assert re.search(r'^build .*toucan_braille_ui.*screen\.c\.obj:', ninja, re.M)
    assert not re.search(r'^build .*prospector_adapter.*(?:custom_status_screen|layouts/).*\.obj:', ninja, re.M)
    for layout in ('CLASSIC','RADII','FIELD','OPERATOR'):
        assert f'CONFIG_PROSPECTOR_STATUS_SCREEN_{layout}=y' not in config
    assert (build / 'zephyr/zmk.uf2').stat().st_size > 0

if __name__ == '__main__':
    check(Path(sys.argv[1]))
    print('Original braille dashboard firmware verified.')
