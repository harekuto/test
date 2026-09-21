from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_stability.py <dump-root> <patch-output>")

dump=Path(sys.argv[1])
out=Path(sys.argv[2])
out.mkdir(parents=True,exist_ok=True)

def find(name):
    hits=list(dump.rglob(name))
    if len(hits)!=1:
        raise SystemExit(f"Expected exactly one {name}, got {len(hits)}: {hits}")
    return hits[0]

def write_patch(name, transform):
    src=find(name)
    text=src.read_text(encoding="utf-8-sig")
    new=transform(text)
    if new==text:
        raise SystemExit(f"No changes made to {name}")
    dst=out/name
    dst.write_text(new,encoding="utf-8")
    print("PATCHED",name)

def replace_exact(text, old, new, label):
    if old not in text:
        raise SystemExit(f"Missing expected block for {label}")
    return text.replace(old,new,1)

def menu_create(text):
    text=replace_exact(text,
'''if (!file_exists("agreement.txt"))
{
    room_goto(r_agree);
}''',
'''if (!file_exists("agreement.txt"))
{
    room_goto(r_agree);
    exit;
}''',"agreement redirect")

    text=replace_exact(text,
'''var file = file_text_open_read("supporters.txt");
var i = 0;
while (!file_text_eof(file))
{
    global.supporter[i++] = file_text_read_string(file);
    file_text_readln(file);
}''',
'''var i = 0;
if (file_exists("supporters.txt"))
{
    var file = file_text_open_read("supporters.txt");
    if (file >= 0)
    {
        while (!file_text_eof(file))
        {
            global.supporter[i++] = file_text_read_string(file);
            file_text_readln(file);
        }
        file_text_close(file);
    }
}''',"supporters safe read")
    return text

def agree_step(text):
    text=replace_exact(text,
'''    var file = file_text_open_write(working_directory + "agreement.txt");
    file_text_write_string(file, "Thank you, hope you enjoy the game!");
    file_text_close(file);
    game_restart();''',
'''    var file = file_text_open_write("agreement.txt");
    if (file >= 0)
    {
        file_text_write_string(file, "Thank you, hope you enjoy the game!");
        file_text_close(file);
        game_restart();
    }''',"agreement writable sandbox")
    return text

def credits_draw(text):
    text=replace_exact(text,
'''var num = 0;
var file = file_text_open_read("credits.txt");
while (!file_text_eof(file))
{
    str[num++] = file_text_readln(file);
}
file_text_close(file);
var length = array_length_1d(str);''',
'''var num = 0;
str = [];
if (file_exists("credits.txt"))
{
    var file = file_text_open_read("credits.txt");
    if (file >= 0)
    {
        while (!file_text_eof(file))
        {
            str[num++] = file_text_readln(file);
        }
        file_text_close(file);
    }
}
var length = array_length_1d(str);''',"credits safe read")
    return text

def gameplay_input(text):
    old_cond = 'keyboard_check_pressed(_interact) || gamepad_button_check_pressed(4, gp_face1)'
    new_cond = 'keyboard_check_pressed(_interact) || keyboard_check_pressed(vk_enter) || gamepad_button_check_pressed(4, gp_face1)'
    count = text.count(old_cond)
    if count < 3:
        raise SystemExit(f"Expected at least 3 interact/talk paths, got {count}")
    text = text.replace(old_cond, new_cond)
    if text.count('keyboard_check_pressed(vk_enter)') < 3:
        raise SystemExit("Enter fallback did not reach all interact/talk branches")
    return text

def input_step(text):
    text=replace_exact(text,
'''if (instance_exists(o_player))
{
    var file = file_text_open_read("Input");
    global.up = file_text_readln(file);
    global.down = file_text_readln(file);
    global.left = file_text_readln(file);
    global.right = file_text_readln(file);
    global.interact = file_text_readln(file);
    global.attack = file_text_readln(file);
    global.kick = file_text_readln(file);
    global.taunt = file_text_readln(file);
    global.dash = file_text_readln(file);
    global.use_item1 = file_text_readln(file);
    global.use_item2 = file_text_readln(file);
    global.retry = file_text_readln(file);
    global.horny = file_text_readln(file);
    global.zoomset = file_text_readln(file);
    global.mute = file_text_readln(file);
    global.lockscene = file_text_readln(file);
    global.fullscreen_b = file_text_readln(file);
    global.cheat_health = file_text_readln(file);
    global.cheat_remove_health = file_text_readln(file);
    file_text_close(file);
    get_input();
}''',
'''if (instance_exists(o_player))
{
    if (file_exists("Input"))
    {
        var file = file_text_open_read("Input");
        if (file >= 0)
        {
            global.up = file_text_readln(file);
            global.down = file_text_readln(file);
            global.left = file_text_readln(file);
            global.right = file_text_readln(file);
            global.interact = file_text_readln(file);
            global.attack = file_text_readln(file);
            global.kick = file_text_readln(file);
            global.taunt = file_text_readln(file);
            global.dash = file_text_readln(file);
            global.use_item1 = file_text_readln(file);
            global.use_item2 = file_text_readln(file);
            global.retry = file_text_readln(file);
            global.horny = file_text_readln(file);
            global.zoomset = file_text_readln(file);
            global.mute = file_text_readln(file);
            global.lockscene = file_text_readln(file);
            global.fullscreen_b = file_text_readln(file);
            global.cheat_health = file_text_readln(file);
            global.cheat_remove_health = file_text_readln(file);
            file_text_close(file);
        }
    }
    get_input();
}''',"Input safe read")
    return text


def menu_step(text):
    # Rebind-controls path: never read from an invalid handle.
    text=replace_exact(text,
'''        case 5:
            var file = file_text_open_read("Input");
            global.up = file_text_readln(file);''',
'''        case 5:
            var file = file_text_open_read("Input");
            if (file < 0)
            {
                inmenu_control = false;
                menu_selection = -1;
                state = "idle";
                break;
            }
            global.up = file_text_readln(file);''',"menu Input handle guard")

    # Load-game path: savepoint is normally created by o_menu, but corrupted/
    # inaccessible storage must not crash Android.
    text=replace_exact(text,
'''        case 7:
            var file3 = file_text_open_read("savepoint");
            target = file_text_readln(file3);''',
'''        case 7:
            var file3 = file_text_open_read("savepoint");
            if (file3 < 0)
            {
                menu_selection = -1;
                state = "idle";
                break;
            }
            target = file_text_readln(file3);''',"menu savepoint handle guard")
    return text

def player_step(text):
    text=replace_exact(text,
'''    var file = file_text_open_read("savepoint");
    target = file_text_readln(file);''',
'''    var file = file_text_open_read("savepoint");
    if (file < 0)
    {
        player_restart = false;
        hascontrol = true;
        state = "move";
        exit;
    }
    target = file_text_readln(file);''',"player retry savepoint guard")
    return text

def savecontrols_script(text):
    text=replace_exact(text,
'''        var file2 = file_text_open_write("Input");
        file_text_write_real(file2, global.up);''',
'''        var file2 = file_text_open_write("Input");
        if (file2 < 0)
            exit;
        file_text_write_real(file2, global.up);''',"savecontrols write guard")
    return text

def checkpoint_save(text):
    text=replace_exact(text,
'''    var file = file_text_open_write("savepoint");
    file_text_write_real(file, global.checkpointroom);''',
'''    var file = file_text_open_write("savepoint");
    if (file < 0)
    {
        can_save = true;
        exit;
    }
    file_text_write_real(file, global.checkpointroom);''',"checkpoint write guard")
    return text

def samtest_create(text):
    text=replace_exact(text,
'''if (directory_exists(working_directory + "/dlc/"))
{
    spr_ = sprite_add(working_directory + "dlc/dlc_sam.png", 6, false, false, sprite_width / 2, sprite_height);''',
'''if (file_exists("dlc/dlc_sam.png"))
{
    spr_ = sprite_add("dlc/dlc_sam.png", 6, false, false, sprite_width / 2, sprite_height);''',"Android DLC included-file path")
    return text

write_patch("gml_Object_o_menu_Create_0.gml",menu_create)
write_patch("gml_Object_o_agree_main_Step_0.gml",agree_step)
write_patch("gml_Object_o_credits_screen_Draw_0.gml",credits_draw)
write_patch("gml_Object_input_Step_0.gml",input_step)
write_patch("gml_GlobalScript_get_input.gml",gameplay_input)
write_patch("gml_Object_o_menu_Step_0.gml",menu_step)
write_patch("gml_Object_o_player_Step_0.gml",player_step)
write_patch("gml_GlobalScript_savecontrols.gml",savecontrols_script)
write_patch("gml_Object_o_checkpoint_Collision_o_player.gml",checkpoint_save)
write_patch("gml_Object_o_samtest_Create_0.gml",samtest_create)

# Final source-level assertions.
joined="\n".join(p.read_text(encoding="utf-8") for p in out.glob("*.gml"))
required=[
    'file_exists("supporters.txt")',
    'file_text_open_write("agreement.txt")',
    'file_exists("credits.txt")',
    'file_exists("Input")',
    'if (file < 0)',
    'if (file3 < 0)',
    'if (file2 < 0)',
    'file_exists("dlc/dlc_sam.png")',
    'keyboard_check_pressed(vk_enter)',
]
for token in required:
    if token not in joined:
        raise SystemExit("Missing final stability token: "+token)
if 'working_directory + "agreement.txt"' in joined:
    raise SystemExit("Unsafe Android agreement path survived")
print("HHP_ANDROID_FILE_IO_FIX_OK")
