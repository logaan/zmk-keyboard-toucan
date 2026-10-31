#!/usr/bin/env python3
"""Render production screen.c with the pinned LVGL source and fixture state.

Usage: scripts/preview-braille-dashboard.py --lvgl /path/to/lvgl --output DIR
Uses a C compiler/CMake, no keyboard, display driver or manually copied layout.
The harness stubs platform data acquisition only; LVGL paints the real screen.
"""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
ROOT=Path(__file__).resolve().parents[1]
STATES=('held','buffer','offline','settings','confirm','shorthand',
        'low-battery','usb-fallback','all-modifiers','eight-dot','long-buffer','editor-error')
def png(data):
    assert len(data)==240*280*3
    def chunk(kind,value):
        return struct.pack('>I',len(value))+kind+value+struct.pack('>I',zlib.crc32(kind+value))
    rows=b''.join(b'\0'+data[y*720:(y+1)*720] for y in range(280))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',240,280,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lvgl',required=True,type=Path)
    parser.add_argument('--braille-module',type=Path,default=ROOT.parent/'braille-module')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/braille-dashboard')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='braille-dashboard-') as temp:
        build=Path(temp)
        subprocess.run(['cmake','-S',str(ROOT/'tests/dashboard_preview'),'-B',str(build),
                        '-DLVGL_SOURCE='+str(args.lvgl.resolve()),
                        '-DBRAILLE_SOURCE='+str(args.braille_module.resolve())],check=True)
        subprocess.run(['cmake','--build',str(build),'-j4'],check=True)
        for state in STATES:
            raw=build/(state+'.rgb')
            subprocess.run([str(build/'dashboard-preview'),state,str(raw)],check=True)
            dest=args.output/(state+'.png');dest.write_bytes(png(raw.read_bytes()));print(dest)
if __name__=='__main__':main()
