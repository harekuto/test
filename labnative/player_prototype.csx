using System;
using System.Linq;
using UndertaleModLib.Models;
using UndertaleModLib.Compiler;

EnsureDataLoaded();

Data.GeneralInfo.FileName = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.Name = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.DisplayName = Data.Strings.MakeString("LAB Still Alive Native");
Data.GeneralInfo.DefaultWindowWidth = 640;
Data.GeneralInfo.DefaultWindowHeight = 480;
Data.GeneralInfo.GMS2FPS = 60.0f;

var room = Data.Rooms[0];
room.Name = Data.Strings.MakeString("rm_lab_player_test");
room.Width = 640;
room.Height = 480;
room.Speed = 60;
room.BackgroundColor = 0xFF111119;
room.DrawBackgroundColor = true;
room.CreationCodeId = null;

room.GameObjects.Clear();
foreach (var layer in room.Layers)
{
    if (layer != null && layer.LayerType == UndertaleRoom.LayerType.Instances && layer.InstancesData != null)
        layer.InstancesData.Instances.Clear();
}

var instanceLayer = room.Layers.FirstOrDefault(l =>
    l != null &&
    l.LayerType == UndertaleRoom.LayerType.Instances &&
    l.InstancesData != null);

if (instanceLayer == null)
{
    instanceLayer = new UndertaleRoom.Layer
    {
        LayerName = Data.Strings.MakeString("LAB_Instances"),
        LayerId = 910001,
        LayerDepth = 0,
        LayerType = UndertaleRoom.LayerType.Instances,
        IsVisible = true,
        Data = new UndertaleRoom.Layer.LayerInstancesData()
    };
    room.Layers.Add(instanceLayer);
}

Data.GeneralInfo.RoomOrder.Clear();
Data.GeneralInfo.RoomOrder.Add(new UndertaleResourceById<UndertaleRoom, UndertaleChunkROOM>() { Resource = room });

var obj = new UndertaleGameObject()
{
    Name = Data.Strings.MakeString("obj_lab_player_native"),
    Persistent = false,
    Visible = true
};
Data.GameObjects.Add(obj);

var inst = new UndertaleRoom.GameObject
{
    InstanceID = Data.GeneralInfo.LastObj++,
    ObjectDefinition = obj,
    X = 0,
    Y = 0
};
room.GameObjects.Add(inst);
instanceLayer.InstancesData.Instances.Add(inst);

var imports = new CodeImportGroup(Data)
{
    MainThreadAction = MainThreadAction
};

imports.QueueReplace(obj.EventHandlerFor(EventType.Create, Data), @"
display_set_gui_size(640, 480);

atlas = sprite_add(""wall_008.png"", 1, false, false, 0, 0);
px = 320;
py = 350;
vy = 0;
facing = 1;
anim_index = 0;
anim_timer = 0;
state_run = false;
last_mv = 0;
jump_count = 0;
jump_was_down = false;

idle_x = [1,2,3,0,0,1,2];
idle_y = [0,0,0,0,1,1,1];
idle_d = [6,3,3,6,6,3,3];

run_x = [2,1,0,3,2,1,0];
run_y = [3,3,3,2,2,2,2];
run_d = [6,3,3,3,6,3,3];

vk_l = virtual_key_add(24, 350, 86, 86, vk_left);
vk_r = virtual_key_add(120, 350, 86, 86, vk_right);
vk_j = virtual_key_add(530, 340, 86, 86, ord(""X""));
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Step, EventSubtypeStep.Step, Data), @"
var mv = 0;
if (keyboard_check(vk_left)) mv -= 1;
if (keyboard_check(vk_right)) mv += 1;

if (mv != last_mv)
{
    show_debug_message(""LAB_INPUT_MV="" + string(mv) + "" PX="" + string(px));
    last_mv = mv;
}

if (mv != 0)
{
    px += mv * 3.2;
    facing = mv;
    if (!state_run)
    {
        state_run = true;
        anim_index = 0;
        anim_timer = 0;
    }
}
else if (state_run)
{
    state_run = false;
    anim_index = 0;
    anim_timer = 0;
}

var jump_down = keyboard_check(ord(""X""));
if (jump_down && !jump_was_down && py >= 350)
{
    vy = -7.2;
    jump_count += 1;
    show_debug_message(""LAB_JUMP_TRIGGERED="" + string(jump_count) + "" PY="" + string(py));
}
jump_was_down = jump_down;

vy += 0.36;
py += vy;
if (py > 350)
{
    py = 350;
    vy = 0;
}

px = clamp(px, 48, 592);

anim_timer += 1;
var dur = state_run ? run_d[anim_index] : idle_d[anim_index];
if (anim_timer >= dur)
{
    anim_timer = 0;
    anim_index += 1;
    if (anim_index >= 7) anim_index = 0;
}
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Draw, Data), @"
draw_clear(make_color_rgb(17,17,25));

draw_set_color(make_color_rgb(45,45,58));
draw_rectangle(0, 446, 640, 480, false);
draw_set_color(c_white);
draw_text(18, 18, ""LAB STILL ALIVE - NATIVE PLAYABLE PROTOTYPE"");
draw_set_color(c_gray);
draw_text(18, 42, ""Original ACTKOOL Misa atlas / native GameMaker Android"");

var cx = state_run ? run_x[anim_index] : idle_x[anim_index];
var cy = state_run ? run_y[anim_index] : idle_y[anim_index];
var sx = (facing < 0) ? -1 : 1;

draw_sprite_part_ext(atlas, 0, cx*96, cy*96, 96, 96, px, py, sx, 1, c_white, 1);

draw_set_alpha(0.30);
draw_set_color(c_white);
draw_circle(67,393,43,false);
draw_circle(163,393,43,false);
draw_circle(573,383,43,false);
draw_set_alpha(1);
draw_set_color(c_white);
draw_text(54,384,""<"");
draw_text(150,384,"">"");
draw_text(563,374,""X"");

draw_set_color(c_lime);
draw_text(18, 70, ""LAB_NATIVE_PLAYER_OK"");
draw_set_color(c_white);
draw_text(18, 94, ""PX="" + string(px) + "" PY="" + string(py) + "" JUMPS="" + string(jump_count));
");

imports.Import();

ScriptMessage($"LAB_PLAYER_PROTO_READY room={room.Name.Content};version={Data.GeneralInfo.Major}.{Data.GeneralInfo.Minor}.{Data.GeneralInfo.Release}.{Data.GeneralInfo.Build};bc={Data.GeneralInfo.BytecodeVersion}");
