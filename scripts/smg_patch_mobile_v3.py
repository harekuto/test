from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: smg_patch_mobile_v3.py <GameMaker-Mobiler root>")

root = Path(sys.argv[1])
files = list(root.rglob("*"))

def one(name: str, contains: str | None = None) -> Path:
    matches = [
        p for p in files
        if p.is_file()
        and p.name == name
        and (contains is None or contains in str(p).replace("\\", "/"))
    ]
    if len(matches) != 1:
        raise SystemExit(f"Expected one {name}, got {len(matches)}: {matches}")
    return matches[0]

# The game renders its GUI in 640x360. The upstream mobile overlay assumes 640x480.
# These defaults are therefore intentionally designed around 640x360.
layout = {
    "settx = -50;": "settx = 8;",
    "setty = 5;": "setty = 10;",

    # Attack / jump cluster, diagonal in the safe right-hand area.
    "zx = 404;": "zx = 506;",
    "zy = 338;": "zy = 255;",
    "xx = 488;": "xx = 548;",
    "xy = 294;": "xy = 200;",
    "cx = 573;": "cx = 590;",
    "cy = 253;": "cy = 145;",

    # D-pad, entirely inside the 360px logical height.
    "upx = 59;": "upx = 52;",
    "upy = 194;": "upy = 190;",
    "leftx = -22;": "leftx = 8;",
    "lefty = 275;": "lefty = 235;",
    "rightx = 140;": "rightx = 96;",
    "righty = 275;": "righty = 235;",
    "downx = 59;": "downx = 52;",
    "downy = 356;": "downy = 280;",

    # ~75-90 physical px on a 707px-high 640x360-scaled display.
    "button_scale = 3;": "button_scale = 1.45;",
    "analog_scale = 3.5;": "analog_scale = 1.55;",
    "controls_opacity = 0.5;": "controls_opacity = 0.34;",
}

mb = one("gml_Object_mb_cont_mobile_Create_0.gml", "mobilecont")
s = mb.read_text(encoding="utf-8-sig")
s = s.replace("global.mobile_cn = 1;", "global.mobile_cn = 0;")
s = s.replace("global.mobile_prioritize_display = 0;", "global.mobile_prioritize_display = 1;")
s = s.replace("global.add_mobilekey = 1;", "global.add_mobilekey = 0;")
s = s.replace(
    'global.ui_state = ini_read_real("UI", "state", 1);',
    'global.ui_state = ini_read_real("UI", "state", 4);',
)
mb.write_text(s, encoding="utf-8")

create = one("gml_Object_obj_mobilecontrols_button_Create_0.gml", "TouchControls_data_button")
s = create.read_text(encoding="utf-8-sig")
for old, new in layout.items():
    s = s.replace(old, new)

marker = "active_key = -1;"
menu_defs = r'''
// SMG Android v3: compact controls for the actual 640x360 GUI.
smg_enter_w = 54;
smg_enter_h = 22;
smg_enter_x = 568;
smg_enter_y = 10;
smg_escape_w = 54;
smg_escape_h = 22;
smg_escape_x = 500;
smg_escape_y = 10;
'''
if "smg_enter_x" not in s:
    s = s.replace(marker, marker + "\n" + menu_defs)

migration = r'''
// Migrate any v1/v2 saved touch layout to the corrected 640x360 v3 layout.
ini_open("touchconfig_button.ini");
var _smg_layout_version = ini_read_real("SMG", "layout_version", 0);
if (_smg_layout_version < 3)
{
    zx = 506;
    zy = 255;
    xx = 548;
    xy = 200;
    cx = 590;
    cy = 145;

    upx = 52;
    upy = 190;
    leftx = 8;
    lefty = 235;
    rightx = 96;
    righty = 235;
    downx = 52;
    downy = 280;

    button_scale = 1.45;
    analog_scale = 1.55;
    controls_opacity = 0.34;

    ini_write_real("CONFIG", "zx", zx);
    ini_write_real("CONFIG", "zy", zy);
    ini_write_real("CONFIG", "xx", xx);
    ini_write_real("CONFIG", "xy", xy);
    ini_write_real("CONFIG", "cx", cx);
    ini_write_real("CONFIG", "cy", cy);
    ini_write_real("CONFIG", "upx", upx);
    ini_write_real("CONFIG", "upy", upy);
    ini_write_real("CONFIG", "leftx", leftx);
    ini_write_real("CONFIG", "lefty", lefty);
    ini_write_real("CONFIG", "rightx", rightx);
    ini_write_real("CONFIG", "righty", righty);
    ini_write_real("CONFIG", "downx", downx);
    ini_write_real("CONFIG", "downy", downy);
    ini_write_real("CONFIG", "button_scale", button_scale);
    ini_write_real("CONFIG", "analog_scale", analog_scale);
    ini_write_real("CONFIG", "controls_opacity", controls_opacity);
    ini_write_real("SMG", "layout_version", 3);
}
ini_close();
'''
if "layout_version" not in s:
    s += "\n" + migration
create.write_text(s, encoding="utf-8")

other = one("gml_Object_obj_mobilecontrols_button_Other_4.gml", "TouchControls_data_button")
s = other.read_text(encoding="utf-8-sig")
old_settings = 'virtual_key_settings = virtual_key_add(-50, 5, 38, 50, 92);'
new_settings = 'virtual_key_settings = virtual_key_add(8, 10, 32, 32, 92);'
s = s.replace(old_settings, new_settings)
menu_keys = r'''
    virtual_key_smg_enter = virtual_key_add(smg_enter_x, smg_enter_y, smg_enter_w, smg_enter_h, 13);
    virtual_key_smg_escape = virtual_key_add(smg_escape_x, smg_escape_y, smg_escape_w, smg_escape_h, 27);
'''
if "virtual_key_smg_enter" not in s:
    s = s.replace(new_settings, new_settings + "\n" + menu_keys)
other.write_text(s, encoding="utf-8")

cleanup = one("gml_Object_obj_mobilecontrols_button_CleanUp_0.gml", "TouchControls_data_button")
s = cleanup.read_text(encoding="utf-8-sig")
if "virtual_key_smg_enter" not in s:
    s += "\nvirtual_key_delete(virtual_key_smg_enter);\nvirtual_key_delete(virtual_key_smg_escape);\n"
cleanup.write_text(s, encoding="utf-8")

step = one("gml_Object_obj_mobilecontrols_button_Step_0.gml", "TouchControls_data_button")
s = step.read_text(encoding="utf-8-sig")
for old, new in layout.items():
    s = s.replace(old, new)
if "virtual_key_smg_enter" not in s:
    s = s.replace(
        "virtual_key_delete(virtual_key_c);",
        "virtual_key_delete(virtual_key_c);\n"
        "virtual_key_delete(virtual_key_smg_enter);\n"
        "virtual_key_delete(virtual_key_smg_escape);",
    )
step.write_text(s, encoding="utf-8")

draw = one("gml_Object_obj_mobilecontrols_button_Draw_75.gml", "TouchControls_data_button")
s = draw.read_text(encoding="utf-8-sig")
s = s.replace(
    'draw_sprite_ext(spr_settings_mobile, keyboard_check(92), settx, setty, 2, 2, 0, button_colour, 0.5);',
    'draw_sprite_ext(spr_settings_mobile, keyboard_check(92), settx, setty, 0.9, 0.9, 0, button_colour, 0.30);',
)
needle = 'draw_sprite_ext(spr_c_button, keyboard_check(ord("C")), (global.dual_controls == 1) ? cx2 : cx, (global.dual_controls == 1) ? cy2 : cy, button_scale, button_scale, 0, button_colour, controls_opacity * image_alpha);'
menu_draw = r'''
// Small menu controls above gameplay; no ATK/JUMP text over dialogue.
var _smg_colour = draw_get_color();
var _smg_alpha = draw_get_alpha();
draw_set_font(settings_font);
draw_set_halign(fa_center);
draw_set_valign(fa_middle);
draw_set_alpha(max(0.28, controls_opacity * image_alpha));

draw_set_color(c_black);
draw_rectangle(smg_escape_x, smg_escape_y, smg_escape_x + smg_escape_w, smg_escape_y + smg_escape_h, false);
draw_set_color(c_white);
draw_rectangle(smg_escape_x, smg_escape_y, smg_escape_x + smg_escape_w, smg_escape_y + smg_escape_h, true);
draw_text_transformed(smg_escape_x + smg_escape_w * 0.5, smg_escape_y + smg_escape_h * 0.5, "ESC", 0.65, 0.65, 0);

draw_set_color(c_black);
draw_rectangle(smg_enter_x, smg_enter_y, smg_enter_x + smg_enter_w, smg_enter_y + smg_enter_h, false);
draw_set_color(c_white);
draw_rectangle(smg_enter_x, smg_enter_y, smg_enter_x + smg_enter_w, smg_enter_y + smg_enter_h, true);
draw_text_transformed(smg_enter_x + smg_enter_w * 0.5, smg_enter_y + smg_enter_h * 0.5, "ENTER", 0.58, 0.58, 0);

draw_set_alpha(_smg_alpha);
draw_set_color(_smg_colour);
draw_set_halign(fa_left);
draw_set_valign(fa_top);
draw_set_font(-1);
'''
if "Small menu controls" not in s:
    s = s.replace(needle, needle + "\n" + menu_draw)
draw.write_text(s, encoding="utf-8")

# Compatibility with GameMaker 2.2.2.
for p in root.rglob("*Draw_75.gml"):
    if not p.is_file():
        continue
    try:
        t = p.read_text(encoding="utf-8-sig")
    except Exception:
        continue
    u = (
        t.replace("draw_get_font()", "-1")
        .replace("draw_get_halign()", "fa_left")
        .replace("draw_get_valign()", "fa_top")
    )
    if u != t:
        p.write_text(u, encoding="utf-8")
        print("GM222_COMPAT", p)

checks = {
    mb: ['global.ui_state = ini_read_real("UI", "state", 4);'],
    create: ["layout_version", "< 3", "button_scale = 1.45", "analog_scale = 1.55", "downy = 280"],
    other: ["virtual_key_smg_enter", "virtual_key_smg_escape", "virtual_key_add(8, 10, 32, 32, 92)"],
    cleanup: ["virtual_key_smg_enter"],
    step: ["virtual_key_smg_escape", "zy = 255", "downy = 280"],
    draw: ['"ENTER"', '"ESC"', "draw_text_transformed", "0.9, 0.9"],
}
for p, needles in checks.items():
    txt = p.read_text(encoding="utf-8")
    for n in needles:
        if n not in txt:
            raise SystemExit(f"Patch validation failed: {p} missing {n}")
    print("PATCHED", p)
