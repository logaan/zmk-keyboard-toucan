#include <stdio.h>
#include <stdlib.h>
#include <lvgl.h>
#include "platform.h"
#include "../../boards/shields/toucan_braille_ui/screen.c"
static uint8_t pixels[240*280*3], draw[240*280*3];
static void flush(lv_display_t *d,const lv_area_t *a,uint8_t *p) {
 for(int y=a->y1;y<=a->y2;y++)for(int x=a->x1;x<=a->x2;x++){
  size_t n=(y*240+x)*3;pixels[n]=p[2];pixels[n+1]=p[1];pixels[n+2]=p[0];p+=3;
 }
 lv_display_flush_ready(d);
}
int main(int argc,char **argv) {
 if(argc!=3)return 2;
 lv_init();lv_display_t *d=lv_display_create(240,280);
 lv_display_set_color_format(d,LV_COLOR_FORMAT_RGB888);
 lv_display_set_buffers(d,draw,NULL,sizeof(draw),LV_DISPLAY_RENDER_MODE_FULL);
 lv_display_set_flush_cb(d,flush);
 lv_obj_t *screen=zmk_display_status_screen();
 memset(&state,0,sizeof(state));
 state.connected[0]=state.connected[1]=state.known[0]=state.known[1]=true;
 state.battery[0]=84;state.battery[1]=67;state.braille_layer=true;
 strcpy(state.endpoint,"BT 2 connected");strcpy(state.braille.mode,"ueb1");
 state.mods=2;state.braille.held=61;strcpy(state.braille.preview,"y");
 if(!strcmp(argv[1],"buffer")){
  strcpy(state.braille.mode,"ueb2");strcpy(state.braille.preview,"according");
  state.braille.held=9;state.braille.pending_count=1;state.braille.waiting=true;
  strcpy(state.braille.pending,"1");
 }
 if(!strcmp(argv[1],"shorthand")){
  strcpy(state.braille.mode,"computer8_short");strcpy(state.braille.preview,"about");
  state.braille.held=3;state.braille.pending_count=1;state.braille.waiting=true;
  strcpy(state.braille.pending,"1");
 }
 if(!strcmp(argv[1],"offline")){
  state.connected[0]=state.connected[1]=false;state.known[0]=state.known[1]=false;
  strcpy(state.endpoint,"USB offline");state.mods=0;strcpy(state.notice,"2 saved rules skipped");
 }
 if(!strcmp(argv[1],"settings")){
  state.editor.active=true;strcpy(state.editor.title,"Braille settings");
  strcpy(state.editor.body,"> Mode\n  New binding\n  Unbind\n  Reset overrides\n  Done");
 }
 if(!strcmp(argv[1],"confirm")){
  state.editor.active=true;strcpy(state.editor.title,"Save binding?");
  strcpy(state.editor.body,"Input: 123456 145\nPosition: anywhere\n1/16 key_press\nparam1: 458756\nparam2: 0\ns Save / c Cancel");
 }
 refresh(NULL);lv_screen_load(screen);lv_refr_now(d);
 FILE *f=fopen(argv[2],"wb");if(!f)return 3;
 fwrite(pixels,1,sizeof(pixels),f);fclose(f);return 0;
}
