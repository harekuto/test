using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using GameMaker_Mobiler.Services;
using UndertaleModLib;
using UndertaleModLib.Compiler;
using UndertaleModLib.Util;

static class Program
{
    static void Log(string m, bool e=false) => Console.WriteLine((e?"[ERR] ":"[LOG] ")+m);

    static async Task<int> Main(string[] args)
    {
        if (args.Length != 3) return 2;
        var originalData=Path.GetFullPath(args[0]);
        var gameDir=Path.GetFullPath(args[1]);
        var outputApk=Path.GetFullPath(args[2]);
        Directory.CreateDirectory(Path.GetDirectoryName(outputApk)!);

        var version=DataWinVersionReader.Read(originalData);
        Console.WriteLine("GAME_VERSION="+version.RawGen8Version);
        Console.WriteLine("BYTECODE="+version.BytecodeVersion);
        Console.WriteLine("IS_YYC="+version.IsYyc);
        if (!version.IsValid || version.Major!=2 || version.Minor!=2 || version.Release!=2 || version.Build!=302 || version.BytecodeVersion!=17 || version.IsYyc)
            throw new InvalidDataException("Unexpected GameMaker build");

        var workDir=Path.Combine(Path.GetDirectoryName(outputApk)!,"port-work");
        if (Directory.Exists(workDir)) Directory.Delete(workDir,true);
        Directory.CreateDirectory(workDir);
        var patchedData=Path.Combine(workDir,"data.mobile.win");

        var mobileOptions=new[]{true,false,false,false,false,false,false};
        var utmt=new UtmtService(Log);
        await utmt.ModifyDataWinToPath(originalData,mobileOptions,patchedData,CancellationToken.None);

        using(var data=DataWinVersionReader.ReadData(patchedData,Log,m=>Console.WriteLine("[UTMT] "+m)))
        {
            var create = """
display_set_gui_size(640,360);
depth=-1000000;
ui_alpha=0.36;
ui_alpha_pressed=0.62;
ui_font=asset_get_index("font_mubai");
vk_touch_left=-1; vk_touch_right=-1; vk_touch_up=-1; vk_touch_down=-1;
vk_touch_jump=-1; vk_touch_attack=-1; vk_touch_enter=-1; vk_touch_escape=-1;
vk_touch_mode=-1; vk_touch_lang_ctrl=-1; vk_touch_lang_insert=-1;
vk_touch_left=virtual_key_add(16,270,68,72,vk_left);
vk_touch_right=virtual_key_add(96,270,68,72,vk_right);
vk_touch_up=virtual_key_add(56,218,68,68,vk_up);
vk_touch_down=virtual_key_add(56,292,68,56,vk_down);
vk_touch_jump=virtual_key_add(438,228,88,108,ord("X"));
vk_touch_attack=virtual_key_add(536,246,92,96,ord("C"));
vk_touch_mode=virtual_key_add(190,10,72,34,vk_space);
vk_touch_lang_ctrl=virtual_key_add(274,10,76,34,vk_lcontrol);
vk_touch_lang_insert=virtual_key_add(274,10,76,34,vk_insert);
vk_touch_escape=virtual_key_add(454,10,78,34,vk_escape);
vk_touch_enter=virtual_key_add(540,10,86,34,vk_enter);
""";

            var roomStart = """
vk_touch_left=virtual_key_add(16,270,68,72,vk_left);
vk_touch_right=virtual_key_add(96,270,68,72,vk_right);
vk_touch_up=virtual_key_add(56,218,68,68,vk_up);
vk_touch_down=virtual_key_add(56,292,68,56,vk_down);
vk_touch_jump=virtual_key_add(438,228,88,108,ord("X"));
vk_touch_attack=virtual_key_add(536,246,92,96,ord("C"));
vk_touch_mode=virtual_key_add(190,10,72,34,vk_space);
vk_touch_lang_ctrl=virtual_key_add(274,10,76,34,vk_lcontrol);
vk_touch_lang_insert=virtual_key_add(274,10,76,34,vk_insert);
vk_touch_escape=virtual_key_add(454,10,78,34,vk_escape);
vk_touch_enter=virtual_key_add(540,10,86,34,vk_enter);
""";

            var step = """
// Virtual keys handle multitouch. Gameplay timing is left untouched.
""";

            var draw = """
var old_alpha=draw_get_alpha();
var old_color=draw_get_color();
var old_halign=draw_get_halign();
var old_valign=draw_get_valign();
var old_font=draw_get_font();
if (ui_font>=0) draw_set_font(ui_font);
draw_set_halign(fa_center);
draw_set_valign(fa_middle);

draw_set_color(c_black);
draw_set_alpha(keyboard_check(vk_left)?ui_alpha_pressed:ui_alpha); draw_rectangle(22,278,76,334,false);
draw_set_alpha(keyboard_check(vk_right)?ui_alpha_pressed:ui_alpha); draw_rectangle(104,278,158,334,false);
draw_set_alpha(keyboard_check(vk_up)?ui_alpha_pressed:ui_alpha); draw_rectangle(62,224,116,278,false);
draw_set_alpha(keyboard_check(vk_down)?ui_alpha_pressed:ui_alpha); draw_rectangle(62,294,116,346,false);
draw_set_color(c_white); draw_set_alpha(0.78);
draw_text(49,306,"<"); draw_text(131,306,">"); draw_text(89,251,"^"); draw_text(89,320,"v");

draw_set_color(c_black);
draw_set_alpha(keyboard_check(ord("X"))?ui_alpha_pressed:ui_alpha); draw_circle(482,279,42,false);
draw_set_alpha(keyboard_check(ord("C"))?ui_alpha_pressed:ui_alpha); draw_circle(582,294,44,false);
draw_set_color(c_white); draw_set_alpha(0.86);
draw_text(482,274,"JUMP"); draw_text(482,292,"X");
draw_text(582,289,"ATK"); draw_text(582,307,"C");

draw_set_color(c_black);
draw_set_alpha(keyboard_check(vk_space)?0.58:0.30); draw_rectangle(190,10,262,42,false);
draw_set_alpha((keyboard_check(vk_lcontrol)&&keyboard_check(vk_insert))?0.58:0.30); draw_rectangle(274,10,350,42,false);
draw_set_alpha(keyboard_check(vk_escape)?0.58:0.30); draw_rectangle(454,10,532,42,false);
draw_set_alpha(keyboard_check(vk_enter)?0.58:0.30); draw_rectangle(540,10,626,42,false);
draw_set_color(c_white); draw_set_alpha(0.78);
draw_text(226,26,"MODE"); draw_text(312,26,"LANG"); draw_text(493,26,"BACK"); draw_text(583,26,"MENU");

draw_set_font(old_font); draw_set_halign(old_halign); draw_set_valign(old_valign);
draw_set_color(old_color); draw_set_alpha(old_alpha);
""";

            var cleanup = """
if (vk_touch_left>=0) virtual_key_delete(vk_touch_left);
if (vk_touch_right>=0) virtual_key_delete(vk_touch_right);
if (vk_touch_up>=0) virtual_key_delete(vk_touch_up);
if (vk_touch_down>=0) virtual_key_delete(vk_touch_down);
if (vk_touch_jump>=0) virtual_key_delete(vk_touch_jump);
if (vk_touch_attack>=0) virtual_key_delete(vk_touch_attack);
if (vk_touch_enter>=0) virtual_key_delete(vk_touch_enter);
if (vk_touch_escape>=0) virtual_key_delete(vk_touch_escape);
if (vk_touch_mode>=0) virtual_key_delete(vk_touch_mode);
if (vk_touch_lang_ctrl>=0) virtual_key_delete(vk_touch_lang_ctrl);
if (vk_touch_lang_insert>=0) virtual_key_delete(vk_touch_lang_insert);
""";

            var controllerCreate = """
global.ui_state=3;
global.add_mobilekey=0;
global.mobile_f2=0;
global.mobile_heal=0;
global.Android_System_Keyboard=0;
global.dual_controls=0;
global.mobile_room_speed_keep_60=0;
if (!instance_exists(obj_mobilecontrols)) instance_create_depth(0,0,-1000000,obj_mobilecontrols);
""";

            var controllerStep = """
if (!instance_exists(obj_mobilecontrols)) instance_create_depth(0,0,-1000000,obj_mobilecontrols);
""";

            var noCycle = """
// Generic control-mode cycling disabled for the tailored port.
""";

            var patches=new(string Name,string Gml)[]{
                ("gml_Object_obj_mobilecontrols_Create_0",create),
                ("gml_Object_obj_mobilecontrols_Other_4",roomStart),
                ("gml_Object_obj_mobilecontrols_Step_0",step),
                ("gml_Object_obj_mobilecontrols_Draw_75",draw),
                ("gml_Object_obj_mobilecontrols_CleanUp_0",cleanup),
                ("gml_Object_mb_cont_mobile_Create_0",controllerCreate),
                ("gml_Object_mb_cont_mobile_Step_0",controllerStep),
                ("gml_Object_mb_cont_mobile_KeyPress_8",noCycle)
            };
            var import=new CodeImportGroup(data);
            foreach(var p in patches)
            {
                var code=data.Code.ByName(p.Name) ?? throw new InvalidDataException("Missing injected code: "+p.Name);
                import.QueueReplace(code,p.Gml);
            }
            import.Import();

            var controls=data.GameObjects.ByName("obj_mobilecontrols") ?? throw new InvalidDataException("obj_mobilecontrols missing");
            controls.Persistent=true;
            var controller=data.GameObjects.ByName("mb_cont_mobile") ?? throw new InvalidDataException("mb_cont_mobile missing");
            controller.Persistent=true;

            using var fs=new FileStream(patchedData,FileMode.Create,FileAccess.Write,FileShare.None);
            UndertaleIO.Write(fs,data);
        }

        using(var verify=DataWinVersionReader.ReadData(patchedData))
        {
            foreach(var n in new[]{"gml_Object_obj_mobilecontrols_Create_0","gml_Object_obj_mobilecontrols_Other_4","gml_Object_obj_mobilecontrols_Draw_75","gml_Object_mb_cont_mobile_Create_0"})
                if (verify.Code.ByName(n) is null) throw new InvalidDataException("Post-write verification failed: "+n);
            Console.WriteLine("PATCHED_CODES="+verify.Code.Count);
            Console.WriteLine("PATCHED_OBJECTS="+verify.GameObjects.Count);
        }

        var builder=new ApkBuilder(Log);
        var template=builder.FindTemplateApk(version);
        Console.WriteLine("TEMPLATE_APK="+template);
        if (!string.Equals(Path.GetFileName(template),"2.2.2.apk",StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Exact 2.2.2 runner template was not selected");

        var progress=new Progress<(int Percent,string Message)>(p=>Console.WriteLine("[APK "+p.Percent+"%] "+p.Message));
        await builder.BuildApkAsync(template,gameDir,patchedData,outputApk,
            "Super Monsters'n Girls","com.harekuto.supermonstersngirls","2.0.2-android-v1",
            null,null,false,false,progress,CancellationToken.None);

        if (!File.Exists(outputApk) || new FileInfo(outputApk).Length<10_000_000)
            throw new InvalidDataException("APK missing or unexpectedly small");
        Console.WriteLine("APK="+outputApk);
        Console.WriteLine("APK_BYTES="+new FileInfo(outputApk).Length);
        return 0;
    }
}
