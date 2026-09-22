using System;
using System.Linq;
using UndertaleModLib.Models;
using UndertaleModLib.Compiler;

EnsureDataLoaded();

Data.GeneralInfo.FileName = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.Name = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.DisplayName = Data.Strings.MakeString("LAB Still Alive Native");
Data.GeneralInfo.Config = Data.Strings.MakeString("Default");
Data.GeneralInfo.DefaultWindowWidth = 640;
Data.GeneralInfo.DefaultWindowHeight = 480;
Data.GeneralInfo.BytecodeVersion = 16;
Data.GeneralInfo.GMS2FPS = 60.0f;

var room = Data.Rooms[0];
room.Name = Data.Strings.MakeString("rm_bootstrap");
room.Caption = Data.Strings.MakeString("LAB Still Alive Native Bootstrap");
room.Width = 640;
room.Height = 480;
room.Speed = 60;
room.BackgroundColor = 0xFF000000;
room.DrawBackgroundColor = true;

Data.GeneralInfo.RoomOrder.Clear();
Data.GeneralInfo.RoomOrder.Add(new UndertaleResourceById<UndertaleRoom, UndertaleChunkROOM>() { Resource = room });

var obj = new UndertaleGameObject()
{
    Name = Data.Strings.MakeString("obj_bootstrap"),
    Persistent = false,
    Visible = true
};
Data.GameObjects.Add(obj);

var inst = new UndertaleRoom.GameObject()
{
    InstanceID = Data.GeneralInfo.LastObj++,
    ObjectDefinition = obj,
    X = 0,
    Y = 0
};
room.GameObjects.Add(inst);

var importGroup = new CodeImportGroup(Data)
{
    MainThreadAction = MainThreadAction
};

importGroup.QueueReplace(obj.EventHandlerFor(EventType.Create, Data), @"
display_set_gui_size(640, 480);
window_set_caption(""LAB Still Alive Native"");
");

importGroup.QueueReplace(obj.EventHandlerFor(EventType.Draw, Data), @"
draw_clear(c_black);
draw_set_color(c_white);
draw_text(32, 32, ""LAB STILL ALIVE - NATIVE GAME MAKER BOOTSTRAP"");
draw_text(32, 64, ""NO WINE / NO WINLATOR"");
draw_text(32, 96, ""GAME.DROID GENERATED FROM SCRATCH"");
draw_text(32, 144, ""Touch screen to verify input"");
if (mouse_check_button(mb_left))
{
    draw_set_color(c_lime);
    draw_text(32, 192, ""TOUCH INPUT OK"");
}
");

importGroup.Import();

ScriptMessage($"BOOTSTRAP_OBJECTS={Data.GameObjects.Count};ROOMS={Data.Rooms.Count};ROOMORDER={Data.GeneralInfo.RoomOrder.Count};BC={Data.GeneralInfo.BytecodeVersion}");
