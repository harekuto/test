using System;
using System.Collections.Generic;
using UndertaleModLib;
using UndertaleModLib.Models;
using UndertaleModLib.Compiler;

EnsureDataLoaded();

void AddOrReplaceChunk(string name, UndertaleChunk chunk)
{
    Data.FORM.Chunks[name] = chunk;
}

Data.SetGMS2Version(2, 3, 7, 476);
Data.GeneralInfo.BytecodeVersion = 17;
Data.GeneralInfo.FileName = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.Name = Data.Strings.MakeString("LABStillAliveNative");
Data.GeneralInfo.DisplayName = Data.Strings.MakeString("LAB Still Alive Native Bootstrap");
Data.GeneralInfo.DefaultWindowWidth = 640;
Data.GeneralInfo.DefaultWindowHeight = 480;
Data.GeneralInfo.GMS2FPS = 60f;

// Add the structural chunks expected by GameMaker Studio 2.3.7.
AddOrReplaceChunk("TGIN", new UndertaleChunkTGIN());
AddOrReplaceChunk("ACRV", new UndertaleChunkACRV());
AddOrReplaceChunk("SEQN", new UndertaleChunkSEQN());
AddOrReplaceChunk("TAGS", new UndertaleChunkTAGS()
{
    Object = new UndertaleTags()
    {
        Tags = new UndertaleSimpleListString(),
        AssetTags = new Dictionary<int, UndertaleSimpleListString>()
    }
});
AddOrReplaceChunk("FEDS", new UndertaleChunkFEDS());

// Rebuild chunk order to the canonical GMS2 ordering.
string[] canonicalOrder = new[]
{
    "GEN8","OPTN","LANG","EXTN","SOND","AGRP","SPRT","BGND","PATH","SCPT","GLOB",
    "GMEN","SHDR","FONT","TMLN","OBJT","ROOM","UILR","DAFL","EMBI","TPAG","TGIN",
    "CODE","VARI","FUNC","STRG","TXTR","AUDO","ACRV","SEQN","TAGS","FEAT","FEDS","PSEM","PSYS"
};
var ordered = new Dictionary<string, UndertaleChunk>();
foreach (string name in canonicalOrder)
{
    if (Data.FORM.Chunks.TryGetValue(name, out UndertaleChunk chunk))
        ordered[name] = chunk;
}
foreach (var kv in Data.FORM.Chunks)
{
    if (!ordered.ContainsKey(kv.Key))
        ordered[kv.Key] = kv.Value;
}
Data.FORM.Chunks = ordered;
Data.FORM.ChunksTypeDict = new Dictionary<Type, UndertaleChunk>();
foreach (var kv in Data.FORM.Chunks)
    Data.FORM.ChunksTypeDict[kv.Value.GetType()] = kv.Value;

var room = Data.Rooms[0];
room.Name = Data.Strings.MakeString("room_bootstrap");
room.Caption = Data.Strings.MakeString("LAB Still Alive Native Bootstrap");
room.Width = 640;
room.Height = 480;
room.Speed = 60;
room.BackgroundColor = 0xFF101018;
room.DrawBackgroundColor = true;
room.GameObjects.Clear();
room.Tiles.Clear();
room.Layers.Clear();
room.Sequences.Clear();

Data.GeneralInfo.RoomOrder.Clear();
Data.GeneralInfo.RoomOrder.Add(new UndertaleResourceById<UndertaleRoom, UndertaleChunkROOM>() { Resource = room });

var obj = new UndertaleGameObject()
{
    Name = Data.Strings.MakeString("obj_lab_bootstrap"),
    Persistent = true,
    Visible = true,
    Solid = false,
    Depth = 0,
    UsesPhysics = false
};
Data.GameObjects.Add(obj);

var instanceLayer = new UndertaleRoom.Layer()
{
    ParentRoom = room,
    LayerName = Data.Strings.MakeString("Instances"),
    LayerId = 1,
    LayerType = UndertaleRoom.LayerType.Instances,
    LayerDepth = 0,
    XOffset = 0,
    YOffset = 0,
    HSpeed = 0,
    VSpeed = 0,
    IsVisible = true,
    Data = new UndertaleRoom.Layer.LayerInstancesData()
};
// Keep the serialized instance layer empty. The bootstrap instance is created
// from room creation code after CLayerManager has initialized its runtime pools.
room.Layers.Add(instanceLayer);

var roomCreate = UndertaleCode.CreateEmptyEntry(Data, "gml_RoomCC_room_bootstrap_0_Create");
room.CreationCodeId = roomCreate;

var imports = new CodeImportGroup(Data)
{
    MainThreadAction = MainThreadAction
};

imports.QueueReplace(roomCreate, @"
instance_create_depth(0, 0, 0, obj_lab_bootstrap);
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Create, Data), @"
display_set_gui_size(640, 480);
counter = 0;
pulse = 0;
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Step, EventSubtypeStep.Step, Data), @"
counter += 1;
pulse = (pulse + 1) mod 120;
");

imports.QueueReplace(obj.EventHandlerFor(EventType.Draw, Data), @"
draw_clear(make_color_rgb(16, 16, 24));
draw_set_alpha(1);
draw_set_color(c_white);
draw_text(32, 32, ""LAB STILL ALIVE - NATIVE GAMEMAKER"");
draw_text(32, 62, ""GMS2.3.7 data / Android runner"");
draw_set_color(c_lime);
draw_rectangle(30, 108, 610, 156, false);
draw_text(44, 122, ""Native game.droid is running"");
draw_set_color(c_gray);
draw_text(32, 195, ""640x480 / 60 FPS / bytecode 17"");
draw_text(32, 224, ""No Wine. No Winlator. No Windows EXE."");
draw_set_color(c_yellow);
draw_text(32, 285, ""BOOTSTRAP_OK"");
draw_set_color(c_white);
draw_text(32, 326, ""Frame: "" + string(counter));
draw_set_color(make_color_rgb(64 + (pulse mod 64), 180, 255));
draw_rectangle(32, 380, 32 + ((counter mod 300) * 1.8), 398, false);
");

imports.Import();

ScriptMessage($"GMS23_BOOTSTRAP_READY version={Data.GeneralInfo.Major}.{Data.GeneralInfo.Minor}.{Data.GeneralInfo.Release}.{Data.GeneralInfo.Build} bc={Data.GeneralInfo.BytecodeVersion} rooms={Data.Rooms.Count} objects={Data.GameObjects.Count} layers={room.Layers.Count} roomInstances={room.GameObjects.Count}");
