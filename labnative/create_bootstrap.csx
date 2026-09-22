using System;
using UndertaleModLib;
using UndertaleModLib.Models;
using UndertaleModLib.Compiler;

EnsureDataLoaded();

Data.GeneralInfo.FileName = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.Name = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.DisplayName = Data.Strings.MakeString("LAB Still Alive Native Bootstrap");
Data.GeneralInfo.DefaultWindowWidth = 640;
Data.GeneralInfo.DefaultWindowHeight = 480;
Data.GeneralInfo.BytecodeVersion = 16;
Data.GeneralInfo.Major = 1;
Data.GeneralInfo.Minor = 4;
Data.GeneralInfo.Release = 9999;
Data.GeneralInfo.Build = 0;
Data.GeneralInfo.GMS2FPS = 60f;

var room = Data.Rooms[0];
room.Name = Data.Strings.MakeString("room_bootstrap");
room.Caption = Data.Strings.MakeString("LAB Still Alive Native Bootstrap");
room.Width = 640;
room.Height = 480;
room.Speed = 60;
room.BackgroundColor = 0xFF101018;

Data.GeneralInfo.RoomOrder.Clear();
Data.GeneralInfo.RoomOrder.Add(new UndertaleResourceById<UndertaleRoom, UndertaleChunkROOM>() { Resource = room });

var obj = new UndertaleGameObject()
{
    Name = Data.Strings.MakeString("obj_lab_bootstrap"),
    Persistent = true,
    Visible = true
};
Data.GameObjects.Add(obj);

var inst = new UndertaleRoom.GameObject()
{
    X = 0,
    Y = 0,
    InstanceID = Data.GeneralInfo.LastObj++,
    ObjectDefinition = obj
};
room.GameObjects.Add(inst);

var imports = new CodeImportGroup(Data)
{
    MainThreadAction = MainThreadAction
};

imports.QueueReplace(obj.EventHandlerFor(EventType.Create, Data), @"
display_set_gui_size(640, 480);
window_set_size(640, 480);
counter = 0;
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Step, EventSubtypeStep.Step, Data), @"
counter += 1;
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Draw, Data), @"
draw_clear(make_color_rgb(16, 16, 24));
draw_set_color(c_white);
draw_text(32, 32, ""LAB STILL ALIVE - NATIVE GAMEMAKER BOOTSTRAP"");
draw_text(32, 64, ""GitHub + UndertaleModTool + Android runner"");
draw_set_color(c_lime);
draw_rectangle(32, 110, 608, 150, false);
draw_text(44, 118, ""Native game.droid is running"");
draw_set_color(c_gray);
draw_text(32, 190, ""640x480 / 60 FPS"");
draw_text(32, 218, ""No Wine. No Winlator. No Windows EXE."");
draw_set_color(c_yellow);
draw_text(32, 280, ""BOOTSTRAP_OK"");
draw_set_color(c_white);
draw_text(32, 320, ""Frame: "" + string(counter));
");

imports.Import();

ScriptMessage($"BOOTSTRAP_DATA_READY rooms={Data.Rooms.Count} objects={Data.GameObjects.Count} code={Data.Code.Count}");
