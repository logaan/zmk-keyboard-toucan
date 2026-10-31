#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <lvgl.h>
/* The real pinned LVGL offset makes scroll progress observable without OCR. */
#include "src/widgets/label/lv_label_private.h"
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
  dashboard_endpoint(state.endpoint,sizeof(state.endpoint),1,0,0,0);state.mods=0;strcpy(state.notice,"2 saved rules skipped");
 }
 if(!strcmp(argv[1],"settings")){
  state.editor.active=true;strcpy(state.editor.title,"Braille settings");
  strcpy(state.editor.body,"> Mode\n  New binding\n  Unbind\n  Reset overrides\n  Done");
 }
 if(!strcmp(argv[1],"confirm")){
  state.editor.active=true;strcpy(state.editor.title,"Save binding?");
  strcpy(state.editor.body,"Input: 123456 145\nPosition: anywhere\n1/16 key_press\nparam1: 458756\nparam2: 0\ns Save / c Cancel");
 }
 if(!strcmp(argv[1],"low-battery")){
  state.battery[0]=9;state.known[1]=false;
  state.braille.held=0;state.mods=0;state.braille.preview[0]=0;
 }
 if(!strcmp(argv[1],"usb-fallback")){
  dashboard_endpoint(state.endpoint,sizeof(state.endpoint),2,4,1,0);
  state.braille_layer=false;state.braille.held=0;state.mods=0;
  state.braille.preview[0]=0;
 }
 if(!strcmp(argv[1],"all-modifiers")){
  state.mods=0xff;
 }
 if(!strcmp(argv[1],"eight-dot")){
  strcpy(state.braille.mode,"computer8");
  state.braille.held=0xc0;strcpy(state.braille.preview,"[Backspace]");
 }
 if(!strcmp(argv[1],"long-buffer")){
  strcpy(state.braille.mode,"computer8_short");
  strcpy(state.braille.preview,"characteristically");
  state.braille.held=0xff;state.braille.pending_count=32;state.braille.waiting=true;
  for(unsigned i=0;i<32;i++){
   size_t used=strlen(state.braille.pending);
   snprintf(state.braille.pending+used,sizeof(state.braille.pending)-used,
            "%s12345678",i?" ":"");
  }
 }
 if(!strcmp(argv[1],"editor-error")){
  state.editor.active=true;state.editor.error=-5;
  strcpy(state.editor.title,"Save binding?");
  strcpy(state.editor.body,"Input: 12345678 12345678\nPosition: anywhere\n16/16 key_press\nparam1: 458756\nparam2: 0\ns Save / c Cancel");
 }
 refresh(NULL);lv_screen_load(screen);lv_refr_now(d);
 /* Exercise a second refresh: widgets must update safely without rebuilding the screen. */
 refresh(NULL);lv_refr_now(d);
 assert(lv_obj_get_width(screen)==240 && lv_obj_get_height(screen)==280);
 FILE *f=fopen(argv[2],"wb");if(!f)return 3;
 fwrite(pixels,1,sizeof(pixels),f);fclose(f);
 /* Validate observable state after rendering, including stale battery readings. */
 for(unsigned i=0;i<2;i++){
  bool shown=state.connected[i] && state.known[i] && state.battery[i];
  assert(lv_obj_has_flag(battery_fill[i],LV_OBJ_FLAG_HIDDEN)==!shown);
 }
 if(!strcmp(argv[1],"eight-dot")){
  assert(lv_obj_get_x(held_dot[6])<lv_obj_get_x(held_dot[7]));
  assert(lv_obj_get_y(held_dot[6])==lv_obj_get_y(held_dot[7]));
  assert(lv_obj_get_y(held_dot[6])>lv_obj_get_y(held_dot[2]));
  for(unsigned i=0;i<8;i++)
   assert(lv_color_eq(lv_obj_get_style_bg_color(held_dot[i],0),
                     lv_color_hex(i>=6?0xff6b00:0x303936)));
 }
 /* Editor exit must restore the normal widgets, hero font and fresh input. */
 state.editor.active=true;strcpy(state.editor.title,"Braille settings");
 strcpy(state.editor.body,"Mode\nNew binding\nDone");refresh(NULL);lv_refr_now(d);
 assert(lv_obj_has_flag(held_panel,LV_OBJ_FLAG_HIDDEN));
 assert(lv_obj_has_flag(buffer_panel,LV_OBJ_FLAG_HIDDEN));
 state.editor.active=false;strcpy(state.braille.preview,"a");
 state.braille_layer=true;state.braille.held=1;state.mods=0x20;
 refresh(NULL);lv_refr_now(d);
 assert(!lv_obj_has_flag(held_panel,LV_OBJ_FLAG_HIDDEN));
 assert(!lv_obj_has_flag(buffer_panel,LV_OBJ_FLAG_HIDDEN));
 assert(lv_obj_get_style_text_font(preview_label,0)==&lv_font_montserrat_28);
 assert(!strcmp(lv_label_get_text(preview_label),"a"));
 /* Right Shift shares the visual Shift chip; other modifier chips clear. */
 for(unsigned i=0;i<4;i++)
  assert(lv_color_eq(lv_obj_get_style_bg_color(mod_chip[i],0),
                    lv_color_hex(i==1?0xff6b00:0x303936)));
 /* Refresh runs at50ms on hardware. Unchanged input must not restart scrolling. */
 strcpy(state.braille.preview,"characteristically");
 strcpy(state.braille.pending,"12345678 12345678 12345678 12345678 12345678");
 state.braille.pending_count=5;refresh(NULL);lv_refr_now(d);
 int preview_travel=0,buffer_travel=0;
 for(unsigned i=0;i<60;i++){
  lv_tick_inc(50);lv_timer_handler();refresh(NULL);lv_refr_now(d);
  int x=((lv_label_t *)preview_label)->offset.x;
  int b=((lv_label_t *)pending_label)->offset.x;
  if(-x>preview_travel)preview_travel=-x;
  if(-b>buffer_travel)buffer_travel=-b;
 }
 assert(preview_travel>10);assert(buffer_travel>10);
 state.editor.active=true;
 strcpy(state.editor.body,"Input: 12345678\nPosition: anywhere\n1/16 key_press\nparam1: 458756\nparam2: 0\nSecond action\nThird action\nFourth action\nFifth action\nSixth action\ns Save / c Cancel");
 refresh(NULL);lv_refr_now(d);
 int editor_travel=0;
 for(unsigned i=0;i<60;i++){
  lv_tick_inc(50);lv_timer_handler();refresh(NULL);lv_refr_now(d);
  int y=((lv_label_t *)preview_label)->offset.y;
  if(-y>editor_travel)editor_travel=-y;
 }
 assert(editor_travel>10);
 return 0;
}
