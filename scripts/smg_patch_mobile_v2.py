from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: smg_patch_mobile_v2.py <GameMaker-Mobiler root>")

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

layout_replacements = {
    "settx = -50;": "settx = 6;",
    "setty = 5;": "setty = 8;",
    "zx = 404;": "zx = 500;",
    "zy = 338;": "zy = 346;",
    "xx = 488;": "xx = 544;",
    "xy = 294;": "xy = 292;",
    "cx = 573;": "cx = 586;",
    "cy = 253;": "cy = 238;",
    "upx = 59;": "upx = 54;",
    "upy = 194;": "upy = 270;",
    "leftx = -22;": "leftx = 0;",
    "lefty = 275;": "lefty = 330;",
    "rightx = 140;": "rightx = 108;",
    "righty = 275;": "righty = 330;",
    "downx = 59;": "downx = 54;",
    "downy = 356;": "downy = 390;",
    "button_scale = 3;": "button_scale = 2.0;",
    "analog_scale = 3.5;": "analog_scale = 2.15;",
    "controls_opacity = 0.5;": "controls_opacity = 0.38;",
}

# Force the configurable mobile-button layout and keep it above game content.
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

# Compact action/D-pad defaults for the library's native 640x480 GUI space.
create = one("gml_Object_obj_mobilecontrols_button_Create_0.gml", "TouchControls_data_button")
s = create.read_text(encoding="utf-8-sig")
for old, new in layout_replacements.items():
    s = s.replace(old, new)

marker = "active_key = -1;"
menu_defs = r'''
// Super Monsters'n Girls v2: compact top menu buttons.
smg_enter_w = 68;
smg_enter_h = 28;
smg_enter_x = 558;
smg_enter_y = 14;
smg_escape_w = 68;
smg_escape_h = 28;
smg_escape_x = 480;
smg_escape_y = 14;
'''
if "smg_enter_x" not in s:
    s = s.replace(marker, marker + "\n" + menu_defs)

migration = r'''
// One-time migration from the oversized v1 layout.
ini_open("touchconfig_button.ini");
var _smg_layout_version = ini_read_real("SMG", "layout_version", 0);
if (_smg_layout_version < 2)
{
    zx = 500;
    zy = 346;
    xx = 544;
    xy = 292;
    cx = 586;
    cy = 238;
    upx = 54;
    upy = 270;
    leftx = 0;
    lefty = 330;
    rightx = 108;
    righty = 330;
    downx = 54;
    downy = 390;
    button_scale = 2.0;
    analog_scale = 2.15;
    controls_opacity = 0.38;

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
    ini_write_real("SMG", "layout_version", 2);
}
ini_close();
'''
if "layout_version" not in s:
    s += "\n" + migration
create.write_text(s, encoding="utf-8")

# Add native virtual ENTER/ESC and move the settings hitbox fully on-screen.
other = one("gml_Object_obj_mobilecontrols_button_Other_4.gml", "TouchControls_data_button")
s = other.read_text(encoding="utf-8-sig")
old_settings = 'virtual_key_settings = virtual_key_add(-50, 5, 38, 50, 92);'
new_settings = 'virtual_key_settings = virtual_key_add(6, 8, 42, 42, 92);'
s = s.replace(old_settings, new_settings)
menu_keys = r'''
    // Native virtual keys used by the game's existing keyboard input.
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

# Keep edit/reset logic compatible with the v2 layout and menu virtual keys.
step = one("gml_Object_obj_mobilecontrols_button_Step_0.gml", "TouchControls_data_button")
s = step.read_text(encoding="utf-8-sig")
for old, new in layout_replacements.items():
    s = s.replace(old, new)
if "virtual_key_smg_enter" not in s:
    s = s.replace(
        "virtual_key_delete(virtual_key_c);",
        "virtual_key_delete(virtual_key_c);\n"
        "virtual_key_delete(virtual_key_smg_enter);\n"
        "virtual_key_delete(virtual_key_smg_escape);",
    )
step.write_text(s, encoding="utf-8")

# Draw Z/X/C using the library sprites only; no extra ATK/JUMP labels over dialogue.
draw = one("gml_Object_obj_mobilecontrols_button_Draw_75.gml", "TouchControls_data_button")
s = draw.read_text(encoding="utf-8-sig")
s = s.replace(
    'draw_sprite_ext(spr_settings_mobile, keyboard_check(92), settx, setty, 2, 2, 0, button_colour, 0.5);',
    'draw_sprite_ext(spr_settings_mobile, keyboard_check(92), settx, setty, 1.25, 1.25, 0, button_colour, 0.38);',
)
needle = 'draw_sprite_ext(spr_c_button, keyboard_check(ord("C")), (global.dual_controls == 1) ? cx2 : cx, (global.dual_controls == 1) ? cy2 : cy, button_scale, button_scale, 0, button_colour, controls_opacity * image_alpha);'
menu_draw = r'''
// Compact ENTER/ESC controls positioned above the dialogue area.
var _smg_colour = draw_get_color();
var _smg_alpha = draw_get_alpha();
draw_set_font(settings_font);
draw_set_halign(fa_center);
draw_set_valign(fa_middle);
draw_set_alpha(max(0.32, controls_opacity * image_alpha));

draw_set_color(c_black);
draw_rectangle(smg_enter_x, smg_enter_y, smg_enter_x + smg_enter_w, smg_enter_y + smg_enter_h, false);
draw_set_color(c_white);
draw_rectangle(smg_enter_x, smg_enter_y, smg_enter_x + smg_enter_w, smg_enter_y + smg_enter_h, true);
draw_text(smg_enter_x + smg_enter_w * 0.5, smg_enter_y + smg_enter_h * 0.5, "ENTER");

draw_set_color(c_black);
draw_rectangle(smg_escape_x, smg_escape_y, smg_escape_x + smg_escape_w, smg_escape_y + smg_escape_h, false);
draw_set_color(c_white);
draw_rectangle(smg_escape_x, smg_escape_y, smg_escape_x + smg_escape_w, smg_escape_y + smg_escape_h, true);
draw_text(smg_escape_x + smg_escape_w * 0.5, smg_escape_y + smg_escape_h * 0.5, "ESC");

draw_set_alpha(_smg_alpha);
draw_set_color(_smg_colour);
draw_set_halign(fa_left);
draw_set_valign(fa_top);
draw_set_font(-1);
'''
if "Compact ENTER/ESC controls" not in s:
    s = s.replace(needle, needle + "\n" + menu_draw)
draw.write_text(s, encoding="utf-8")

# GameMaker 2.2.2 compatibility for later-version draw state getters.
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
    create: ["smg_enter_x", "smg_escape_x", "layout_version", "analog_scale = 2.15"],
    other: ["virtual_key_smg_enter", "virtual_key_smg_escape", "virtual_key_add(6, 8, 42, 42, 92)"],
    cleanup: ["virtual_key_smg_enter"],
    step: ["virtual_key_smg_escape", "button_scale = 2.0"],
    draw: ['"ENTER"', '"ESC"', "1.25, 1.25"],
}
for p, needles in checks.items():
    txt = p.read_text(encoding="utf-8")
    for n in needles:
        if n not in txt:
            raise SystemExit(f"Patch validation failed: {p} missing {n}")
    print("PATCHED", p)
