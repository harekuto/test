from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: smg_patch_mobile.py <GameMaker-Mobiler root>")

root = Path(sys.argv[1])
files = list(root.rglob("*"))

def one(name: str, contains: str | None = None) -> Path:
    matches = [p for p in files if p.is_file() and p.name == name and (contains is None or contains in str(p).replace("\\", "/"))]
    if len(matches) != 1:
        raise SystemExit(f"Expected one {name}, got {len(matches)}: {matches}")
    return matches[0]

# Force the configurable button layout, keep English settings assets, and draw above game content.
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

# Add responsive ENTER/MENU hit boxes to the button-layout object.
create = one("gml_Object_obj_mobilecontrols_button_Create_0.gml", "TouchControls_data_button")
s = create.read_text(encoding="utf-8-sig")
marker = "active_key = -1;"
add = r'''
// Super Monsters'n Girls: responsive menu/start buttons.
var _smg_gui_w = display_get_gui_width();
var _smg_gui_h = display_get_gui_height();
if (_smg_gui_w <= 0) _smg_gui_w = 640;
if (_smg_gui_h <= 0) _smg_gui_h = 480;
smg_enter_w = 72;
smg_enter_h = 36;
smg_enter_x = _smg_gui_w - smg_enter_w - 16;
smg_enter_y = 14;
smg_escape_w = 72;
smg_escape_h = 36;
smg_escape_x = _smg_gui_w - smg_enter_w - smg_escape_w - 28;
smg_escape_y = 14;
'''
if "smg_enter_x" not in s:
    s = s.replace(marker, marker + "\n" + add)
create.write_text(s, encoding="utf-8")

# Add native virtual key mappings that feed the game's existing input code.
other = one("gml_Object_obj_mobilecontrols_button_Other_4.gml", "TouchControls_data_button")
s = other.read_text(encoding="utf-8-sig")
needle = 'virtual_key_settings = virtual_key_add(-50, 5, 38, 50, 92);'
add = r'''
    // Native virtual keys used by the game's real input code.
    virtual_key_smg_enter = virtual_key_add(smg_enter_x, smg_enter_y, smg_enter_w, smg_enter_h, 13);
    virtual_key_smg_escape = virtual_key_add(smg_escape_x, smg_escape_y, smg_escape_w, smg_escape_h, 27);
'''
if "virtual_key_smg_enter" not in s:
    s = s.replace(needle, needle + "\n" + add)
other.write_text(s, encoding="utf-8")

cleanup = one("gml_Object_obj_mobilecontrols_button_CleanUp_0.gml", "TouchControls_data_button")
s = cleanup.read_text(encoding="utf-8-sig")
if "virtual_key_smg_enter" not in s:
    s += "\nvirtual_key_delete(virtual_key_smg_enter);\nvirtual_key_delete(virtual_key_smg_escape);\n"
cleanup.write_text(s, encoding="utf-8")

step = one("gml_Object_obj_mobilecontrols_button_Step_0.gml", "TouchControls_data_button")
s = step.read_text(encoding="utf-8-sig")
if "virtual_key_smg_enter" not in s:
    s = s.replace(
        "virtual_key_delete(virtual_key_c);",
        "virtual_key_delete(virtual_key_c);\n"
        "virtual_key_delete(virtual_key_smg_enter);\n"
        "virtual_key_delete(virtual_key_smg_escape);",
    )
step.write_text(s, encoding="utf-8")

# Label actions clearly in the mobile HUD.
draw = one("gml_Object_obj_mobilecontrols_button_Draw_75.gml", "TouchControls_data_button")
s = draw.read_text(encoding="utf-8-sig")
needle = 'draw_sprite_ext(spr_c_button, keyboard_check(ord("C")), (global.dual_controls == 1) ? cx2 : cx, (global.dual_controls == 1) ? cy2 : cy, button_scale, button_scale, 0, button_colour, controls_opacity * image_alpha);'
add = r'''
// Clear action labels for this game's actual controls.
var _smg_font = draw_get_font();
var _smg_halign = draw_get_halign();
var _smg_valign = draw_get_valign();
var _smg_colour = draw_get_color();
var _smg_alpha = draw_get_alpha();
draw_set_font(settings_font);
draw_set_halign(fa_center);
draw_set_valign(fa_middle);

draw_set_alpha(controls_opacity * image_alpha);
draw_set_color(keyboard_check(vk_enter) ? c_lime : c_black);
draw_rectangle(smg_enter_x, smg_enter_y, smg_enter_x + smg_enter_w, smg_enter_y + smg_enter_h, false);
draw_set_color(c_white);
draw_text(smg_enter_x + smg_enter_w * 0.5, smg_enter_y + smg_enter_h * 0.5, "ENTER");

draw_set_color(keyboard_check(vk_escape) ? c_lime : c_black);
draw_rectangle(smg_escape_x, smg_escape_y, smg_escape_x + smg_escape_w, smg_escape_y + smg_escape_h, false);
draw_set_color(c_white);
draw_text(smg_escape_x + smg_escape_w * 0.5, smg_escape_y + smg_escape_h * 0.5, "MENU");

draw_set_alpha(max(0.25, controls_opacity * image_alpha));
draw_text(((global.dual_controls == 1) ? zx2 : zx) + 40, ((global.dual_controls == 1) ? zy2 : zy) - 8, "ATK");
draw_text(((global.dual_controls == 1) ? xx2 : xx) + 40, ((global.dual_controls == 1) ? xy2 : xy) - 8, "JUMP");
draw_text(((global.dual_controls == 1) ? cx2 : cx) + 40, ((global.dual_controls == 1) ? cy2 : cy) - 8, "C");

draw_set_alpha(_smg_alpha);
draw_set_color(_smg_colour);
draw_set_halign(_smg_halign);
draw_set_valign(_smg_valign);
draw_set_font(_smg_font);
'''
if "Clear action labels" not in s:
    s = s.replace(needle, needle + "\n" + add)
draw.write_text(s, encoding="utf-8")

# GameMaker 2.2.2 compatibility: these draw state getters are unavailable.
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
    create: ["smg_enter_x", "smg_escape_x"],
    other: ["virtual_key_smg_enter", "virtual_key_smg_escape"],
    cleanup: ["virtual_key_smg_enter"],
    step: ["virtual_key_smg_escape"],
    draw: ['"ENTER"', '"MENU"', '"ATK"', '"JUMP"'],
}
for p, needles in checks.items():
    txt = p.read_text(encoding="utf-8")
    for n in needles:
        if n not in txt:
            raise SystemExit(f"Patch validation failed: {p} missing {n}")
    print("PATCHED", p)
