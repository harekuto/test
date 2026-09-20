from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_mobile.py <GameMaker-Mobiler root>")

root=Path(sys.argv[1])
files=list(root.rglob("*"))

def one(name, contains=None):
    hits=[p for p in files if p.is_file() and p.name==name and (contains is None or contains in str(p).replace("\\","/"))]
    if len(hits)!=1:
        raise SystemExit(f"Expected one {name}, got {len(hits)}: {hits}")
    return hits[0]

mobile = one("gml_Object_mb_cont_mobile_Create_0.gml","mobilecont")
s=mobile.read_text(encoding="utf-8-sig")
s=s.replace("global.ui_state = 1;","global.ui_state = 4;")
s=s.replace("global.mobile_cn = 1;","global.mobile_cn = 0;")
s=s.replace("global.mobile_prioritize_display = 0;","global.mobile_prioritize_display = 1;")
s=s.replace("global.add_mobilekey = 1;","global.add_mobilekey = 0;")
s=s.replace('global.ui_state = ini_read_real("UI", "state", 1);','global.ui_state = 4;')
mobile.write_text(s,encoding="utf-8")

create=one("gml_Object_obj_mobilecontrols_button_Create_0.gml","TouchControls_data_button")
s=create.read_text(encoding="utf-8-sig")
repl={
"settx = -50;":"settx = -500;",
"zx = 404;":"zx = 1000;",
"zy = 338;":"zy = 585;",
"xx = 488;":"xx = 1100;",
"xy = 294;":"xy = 500;",
"cx = 573;":"cx = 1180;",
"cy = 253;":"cy = 610;",
"upx = 59;":"upx = 120;",
"upy = 194;":"upy = 520;",
"leftx = -22;":"leftx = 25;",
"lefty = 275;":"lefty = 615;",
"rightx = 140;":"rightx = 215;",
"righty = 275;":"righty = 615;",
"downx = 59;":"downx = 120;",
"downy = 356;":"downy = 685;",
"button_scale = 3;":"button_scale = 3.2;",
"analog_scale = 3.5;":"analog_scale = 3.5;",
"controls_opacity = 0.5;":"controls_opacity = 0.32;",
}
for a,b in repl.items(): s=s.replace(a,b)
s=s.replace('if (file_exists("touchconfig_button.ini"))','if (false && file_exists("touchconfig_button.ini"))')
s=s.replace('if (file_exists("touchconfig2.ini"))','if (false && file_exists("touchconfig2.ini"))')
marker="active_key = -1;"
extra=r'''
// Happy Heart Panic Android fixed action layout (1280x800 GUI).
hhp_ok_x = 870; hhp_ok_y = 615; hhp_ok_w = 115; hhp_ok_h = 72;
hhp_dash_x = 900; hhp_dash_y = 700; hhp_dash_w = 115; hhp_dash_h = 62;
hhp_item1_x = 900; hhp_item1_y = 530; hhp_item1_w = 86; hhp_item1_h = 54;
hhp_item2_x = 995; hhp_item2_y = 505; hhp_item2_w = 86; hhp_item2_h = 54;
hhp_extra_x = 1085; hhp_extra_y = 420; hhp_extra_w = 82; hhp_extra_h = 48;
hhp_retry_x = 1175; hhp_retry_y = 420; hhp_retry_w = 82; hhp_retry_h = 48;
hhp_back_x = 18; hhp_back_y = 18; hhp_back_w = 92; hhp_back_h = 46;
hhp_zoom_x = 490; hhp_zoom_y = 18; hhp_zoom_w = 78; hhp_zoom_h = 40;
hhp_mute_x = 578; hhp_mute_y = 18; hhp_mute_w = 78; hhp_mute_h = 40;
hhp_lock_x = 666; hhp_lock_y = 18; hhp_lock_w = 78; hhp_lock_h = 40;
'''
if "hhp_ok_x" not in s:
    s=s.replace(marker,marker+"\n"+extra)
create.write_text(s,encoding="utf-8")

other=one("gml_Object_obj_mobilecontrols_button_Other_4.gml","TouchControls_data_button")
s=other.read_text(encoding="utf-8-sig")
s=s.replace('virtual_key_settings = virtual_key_add(-50, 5, 38, 50, 92);','virtual_key_settings = virtual_key_add(-500, 5, 38, 50, 92);')
anchor='virtual_key_c = virtual_key_add((global.dual_controls == 1) ? cx2 : cx, (global.dual_controls == 1) ? cy2 : cy, 27 * button_scale, 29 * button_scale, 67);'
custom=r'''
    // Core gameplay and menu actions from the game's real input map.
    virtual_key_hhp_interact = virtual_key_add(hhp_ok_x, hhp_ok_y, hhp_ok_w, hhp_ok_h, 69); // E
    virtual_key_hhp_enter = virtual_key_add(hhp_ok_x, hhp_ok_y, hhp_ok_w, hhp_ok_h, 13); // Enter
    virtual_key_hhp_dash = virtual_key_add(hhp_dash_x, hhp_dash_y, hhp_dash_w, hhp_dash_h, 32); // Space
    virtual_key_hhp_item1 = virtual_key_add(hhp_item1_x, hhp_item1_y, hhp_item1_w, hhp_item1_h, 65); // A
    virtual_key_hhp_item2 = virtual_key_add(hhp_item2_x, hhp_item2_y, hhp_item2_w, hhp_item2_h, 83); // S
    virtual_key_hhp_extra = virtual_key_add(hhp_extra_x, hhp_extra_y, hhp_extra_w, hhp_extra_h, 72); // H
    virtual_key_hhp_retry = virtual_key_add(hhp_retry_x, hhp_retry_y, hhp_retry_w, hhp_retry_h, 71); // G
    virtual_key_hhp_back = virtual_key_add(hhp_back_x, hhp_back_y, hhp_back_w, hhp_back_h, 27); // Esc
    virtual_key_hhp_zoom = virtual_key_add(hhp_zoom_x, hhp_zoom_y, hhp_zoom_w, hhp_zoom_h, 9); // Tab
    virtual_key_hhp_mute = virtual_key_add(hhp_mute_x, hhp_mute_y, hhp_mute_w, hhp_mute_h, 77); // M
    virtual_key_hhp_lock = virtual_key_add(hhp_lock_x, hhp_lock_y, hhp_lock_w, hhp_lock_h, 76); // L
'''
if "virtual_key_hhp_interact" not in s:
    s=s.replace(anchor,anchor+"\n"+custom)
other.write_text(s,encoding="utf-8")

cleanup=one("gml_Object_obj_mobilecontrols_button_CleanUp_0.gml","TouchControls_data_button")
s=cleanup.read_text(encoding="utf-8-sig")
delete=r'''
virtual_key_delete(virtual_key_hhp_interact);
virtual_key_delete(virtual_key_hhp_enter);
virtual_key_delete(virtual_key_hhp_dash);
virtual_key_delete(virtual_key_hhp_item1);
virtual_key_delete(virtual_key_hhp_item2);
virtual_key_delete(virtual_key_hhp_extra);
virtual_key_delete(virtual_key_hhp_retry);
virtual_key_delete(virtual_key_hhp_back);
virtual_key_delete(virtual_key_hhp_zoom);
virtual_key_delete(virtual_key_hhp_mute);
virtual_key_delete(virtual_key_hhp_lock);
'''
if "virtual_key_hhp_interact" not in s: s += "\n"+delete
cleanup.write_text(s,encoding="utf-8")

step=one("gml_Object_obj_mobilecontrols_button_Step_0.gml","TouchControls_data_button")
s=step.read_text(encoding="utf-8-sig")
s=s.replace("if (keyboard_check_pressed(92))","if (false && keyboard_check_pressed(92))")
step.write_text(s,encoding="utf-8")

draw=one("gml_Object_obj_mobilecontrols_button_Draw_75.gml","TouchControls_data_button")
s=draw.read_text(encoding="utf-8-sig")
s=s.replace('draw_sprite_ext(spr_settings_mobile, keyboard_check(92), settx, setty, 2, 2, 0, button_colour, 0.5);','// Settings editor intentionally hidden for the fixed HHP layout.')
append=r'''
// Happy Heart Panic action labels and compact utility strip.
var _hhp_old_colour = draw_get_color();
var _hhp_old_alpha = draw_get_alpha();
var _hhp_old_font = draw_get_font();
var _hhp_old_halign = draw_get_halign();
var _hhp_old_valign = draw_get_valign();

draw_set_font(settings_font);
draw_set_halign(fa_center);
draw_set_valign(fa_middle);

draw_set_alpha(0.34 * image_alpha);
draw_set_color(c_black);
draw_rectangle(hhp_ok_x, hhp_ok_y, hhp_ok_x + hhp_ok_w, hhp_ok_y + hhp_ok_h, false);
draw_rectangle(hhp_dash_x, hhp_dash_y, hhp_dash_x + hhp_dash_w, hhp_dash_y + hhp_dash_h, false);
draw_rectangle(hhp_item1_x, hhp_item1_y, hhp_item1_x + hhp_item1_w, hhp_item1_y + hhp_item1_h, false);
draw_rectangle(hhp_item2_x, hhp_item2_y, hhp_item2_x + hhp_item2_w, hhp_item2_y + hhp_item2_h, false);
draw_rectangle(hhp_extra_x, hhp_extra_y, hhp_extra_x + hhp_extra_w, hhp_extra_y + hhp_extra_h, false);
draw_rectangle(hhp_retry_x, hhp_retry_y, hhp_retry_x + hhp_retry_w, hhp_retry_y + hhp_retry_h, false);
draw_rectangle(hhp_back_x, hhp_back_y, hhp_back_x + hhp_back_w, hhp_back_y + hhp_back_h, false);

draw_set_alpha(0.24 * image_alpha);
draw_rectangle(hhp_zoom_x, hhp_zoom_y, hhp_zoom_x + hhp_zoom_w, hhp_zoom_y + hhp_zoom_h, false);
draw_rectangle(hhp_mute_x, hhp_mute_y, hhp_mute_x + hhp_mute_w, hhp_mute_y + hhp_mute_h, false);
draw_rectangle(hhp_lock_x, hhp_lock_y, hhp_lock_x + hhp_lock_w, hhp_lock_y + hhp_lock_h, false);

draw_set_alpha(0.72 * image_alpha);
draw_set_color(c_white);
draw_text_transformed(hhp_ok_x + hhp_ok_w * 0.5, hhp_ok_y + hhp_ok_h * 0.5, "E / OK", 0.72, 0.72, 0);
draw_text_transformed(hhp_dash_x + hhp_dash_w * 0.5, hhp_dash_y + hhp_dash_h * 0.5, "DASH", 0.70, 0.70, 0);
draw_text_transformed(hhp_item1_x + hhp_item1_w * 0.5, hhp_item1_y + hhp_item1_h * 0.5, "ITEM 1", 0.60, 0.60, 0);
draw_text_transformed(hhp_item2_x + hhp_item2_w * 0.5, hhp_item2_y + hhp_item2_h * 0.5, "ITEM 2", 0.60, 0.60, 0);
draw_text_transformed(hhp_extra_x + hhp_extra_w * 0.5, hhp_extra_y + hhp_extra_h * 0.5, "EXTRA", 0.56, 0.56, 0);
draw_text_transformed(hhp_retry_x + hhp_retry_w * 0.5, hhp_retry_y + hhp_retry_h * 0.5, "RETRY", 0.56, 0.56, 0);
draw_text_transformed(hhp_back_x + hhp_back_w * 0.5, hhp_back_y + hhp_back_h * 0.5, "BACK", 0.58, 0.58, 0);
draw_text_transformed(hhp_zoom_x + hhp_zoom_w * 0.5, hhp_zoom_y + hhp_zoom_h * 0.5, "ZOOM", 0.50, 0.50, 0);
draw_text_transformed(hhp_mute_x + hhp_mute_w * 0.5, hhp_mute_y + hhp_mute_h * 0.5, "MUTE", 0.50, 0.50, 0);
draw_text_transformed(hhp_lock_x + hhp_lock_w * 0.5, hhp_lock_y + hhp_lock_h * 0.5, "LOCK", 0.50, 0.50, 0);

// Clarify the imported Z/X/C sprites for this game's semantics.
draw_text_transformed(zx + 42, zy - 13, "LIGHT", 0.52, 0.52, 0);
draw_text_transformed(xx + 42, xy - 13, "HEAVY", 0.52, 0.52, 0);
draw_text_transformed(cx + 42, cy - 13, "TAUNT", 0.52, 0.52, 0);

draw_set_font(_hhp_old_font);
draw_set_halign(_hhp_old_halign);
draw_set_valign(_hhp_old_valign);
draw_set_alpha(_hhp_old_alpha);
draw_set_color(_hhp_old_colour);
'''
if "Happy Heart Panic action labels" not in s: s += "\n"+append
draw.write_text(s,encoding="utf-8")

checks={
mobile:["global.ui_state = 4;","global.mobile_prioritize_display = 1;"],
create:["hhp_ok_x","zx = 1000;","downy = 685;","button_scale = 3.2;"],
other:["virtual_key_hhp_interact","virtual_key_hhp_enter","virtual_key_hhp_dash","virtual_key_hhp_lock"],
cleanup:["virtual_key_hhp_interact"],
draw:['"E / OK"','"DASH"','"ITEM 1"','"LIGHT"','"HEAVY"'],
}
for p,needles in checks.items():
    t=p.read_text(encoding="utf-8")
    for n in needles:
        if n not in t: raise SystemExit(f"Patch validation failed: {p} missing {n}")
    print("PATCHED",p)
