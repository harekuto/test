using System;
using System.Linq;
using UndertaleModLib.Models;
using UndertaleModLib.Compiler;

EnsureDataLoaded();

Data.GeneralInfo.FileName = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.Name = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.DisplayName = Data.Strings.MakeString("LAB Still Alive Native Bootstrap");
Data.GeneralInfo.DefaultWindowWidth = 640;
Data.GeneralInfo.DefaultWindowHeight = 480;
Data.GeneralInfo.GMS2FPS = 60.0f;

if (Data.Rooms.Count == 0)
    throw new Exception("Donor has no rooms");

var room = Data.Rooms[0];
room.Name = Data.Strings.MakeString("rm_lab_native_bootstrap");
room.Width = 640;
room.Height = 480;
room.Speed = 60;
room.BackgroundColor = 0xFF101018;
room.DrawBackgroundColor = true;
room.CreationCodeId = null;

// Remove donor room instances while preserving the room/layer serialization shape.
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
        LayerId = 900001,
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
    Name = Data.Strings.MakeString("obj_lab_native_bootstrap"),
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
counter = 0;
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Step, EventSubtypeStep.Step, Data), @"
counter += 1;
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Draw, Data), @"
draw_clear(make_color_rgb(16, 16, 24));
draw_set_color(c_white);
draw_text(32, 32, ""LAB STILL ALIVE - NATIVE GAMEMAKER BOOTSTRAP"");
draw_text(32, 64, ""MODERN DONOR FORMAT / LAB-ONLY ROOM"");
draw_set_color(c_lime);
draw_rectangle(32, 110, 608, 150, false);
draw_text(44, 118, ""NATIVE GAME.DROID IS RUNNING"");
draw_set_color(c_gray);
draw_text(32, 190, ""640x480 / 60 FPS"");
draw_text(32, 218, ""NO WINE / NO WINLATOR / NO WINDOWS EXE"");
draw_set_color(c_yellow);
draw_text(32, 280, ""LAB_BOOTSTRAP_OK"");
draw_set_color(c_white);
draw_text(32, 320, ""Frame: "" + string(counter));
if (device_mouse_check_button(0, mb_left))
{
    draw_set_color(c_lime);
    draw_text(32, 360, ""TOUCH INPUT OK"");
}
");

imports.Import();

ScriptMessage($"LAB_DONOR_BOOTSTRAP_READY room={room.Name.Content};objects={Data.GameObjects.Count};roomObjects={room.GameObjects.Count};layers={room.Layers.Count};version={Data.GeneralInfo.Major}.{Data.GeneralInfo.Minor}.{Data.GeneralInfo.Release}.{Data.GeneralInfo.Build};bc={Data.GeneralInfo.BytecodeVersion}");
