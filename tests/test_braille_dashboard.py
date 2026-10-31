"""Verify endpoint presentation, including disconnected and fallback states."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
class Dashboard(unittest.TestCase):
    def test_endpoint_states(self):
        source = '''#include <assert.h>
#include "format.h"
int main(void) {
 char text[64];
 dashboard_endpoint(text,sizeof(text),2,0,2,0); assert(!strcmp(text,"BT 1 connected"));
 dashboard_endpoint(text,sizeof(text),2,4,0,0); assert(!strcmp(text,"BT 5 / offline"));
 dashboard_endpoint(text,sizeof(text),1,0,1,0); assert(!strcmp(text,"USB connected"));
 dashboard_endpoint(text,sizeof(text),1,0,0,0); assert(!strcmp(text,"USB / offline"));
 dashboard_endpoint(text,sizeof(text),1,0,2,2); assert(!strcmp(text,"BT 3 connected\\nPrefer USB"));
 dashboard_endpoint(text,sizeof(text),2,2,1,0); assert(!strcmp(text,"USB connected\\nPrefer BT 3"));
 dashboard_endpoint(text,sizeof(text),0,0,0,0); assert(!strcmp(text,"No target / offline"));
 char tiny[4]; dashboard_endpoint(tiny,sizeof(tiny),1,0,2,2); assert(tiny[3]==0);
}'''
        with tempfile.TemporaryDirectory() as temp:
            src=Path(temp)/'test.c'; src.write_text(source)
            exe=Path(temp)/'test'
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'boards/shields/toucan_braille_ui'),str(src),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
