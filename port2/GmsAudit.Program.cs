using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using UndertaleModLib;
using UndertaleModLib.Models;
using UndertaleModLib.Decompiler;
using Underanalyzer.Decompiler;

if (args.Length < 2) { Console.Error.WriteLine("usage: GmsAudit <data.win> <outdir>"); return; }
var dataPath=args[0]; var outDir=args[1]; Directory.CreateDirectory(outDir);
using var fs=File.OpenRead(dataPath);
using var data=UndertaleIO.Read(fs, warningHandler:(s,b)=>Console.Error.WriteLine("WARN "+s), messageHandler:s=>Console.Error.WriteLine("MSG "+s));
var gi=data.GeneralInfo;
var sb=new StringBuilder();
sb.AppendLine($"version={gi.Major}.{gi.Minor}.{gi.Release}.{gi.Build}");
sb.AppendLine($"bytecode={gi.BytecodeVersion}");
sb.AppendLine($"is_gms2={gi.Major>=2}");
try { sb.AppendLine($"is_yyc={data.IsYYC()}"); } catch(Exception e) { sb.AppendLine("is_yyc_error="+e.Message); }
sb.AppendLine($"codes={data.Code?.Count ?? 0}");
sb.AppendLine($"objects={data.GameObjects?.Count ?? 0}");
sb.AppendLine($"rooms={data.Rooms?.Count ?? 0}");
sb.AppendLine($"sprites={data.Sprites?.Count ?? 0}");
sb.AppendLine($"sounds={data.Sounds?.Count ?? 0}");
if (data.Rooms != null) {
  sb.AppendLine("ROOMS:");
  foreach (var room in data.Rooms.Take(250)) {
    sb.AppendLine($"  {room.Name?.Content} {room.Width}x{room.Height} speed={room.Speed}");
  }
}
var inputRx = new Regex(@"(?i)(keyboard_(?:check|check_pressed|check_released|key_press|key_release)|mouse_(?:check_button|check_button_pressed|check_button_released)|device_mouse_|gamepad_|virtual_key_|vk_[a-z0-9_]+|ord\s*\(|keyboard_key|keyboard_lastkey|keyboard_lastchar)");
var uiRx = new Regex(@"(?i)(display_|window_|application_surface|surface_resize|draw_gui|draw_set_gui|gui_(?:width|height)|view_|camera_|room_width|room_height|fullscreen|pause|menu)");
var ctx=new GlobalDecompileContext(data);
int ok=0, fail=0, relevant=0;
var inputOut=new StringBuilder();
var uiOut=new StringBuilder();
var keys=new Dictionary<string,int>(StringComparer.OrdinalIgnoreCase);
foreach (var code in data.Code ?? new UndertalePointerList<UndertaleCode>()) {
  if (code.ParentEntry != null) continue;
  string text;
  try { text=new DecompileContext(ctx,code).DecompileToString(); ok++; }
  catch(Exception e) { fail++; continue; }
  bool inp=inputRx.IsMatch(text);
  bool ui=uiRx.IsMatch(text);
  if (inp) {
    relevant++;
    inputOut.AppendLine("===== "+code.Name?.Content+" =====");
    var lines=text.Split('\n');
    for(int i=0;i<lines.Length;i++) {
      if(inputRx.IsMatch(lines[i]) || (i>0 && inputRx.IsMatch(lines[i-1])) || (i+1<lines.Length && inputRx.IsMatch(lines[i+1])))
        inputOut.AppendLine($"{i+1}: {lines[i].TrimEnd()}");
    }
    foreach(Match m in Regex.Matches(text,@"(?i)\b(vk_[a-z0-9_]+)\b")) keys[m.Value]=keys.GetValueOrDefault(m.Value)+1;
    foreach(Match m in Regex.Matches(text,@"(?i)ord\s*\(\s*[""'](.{1,4}?)[""']\s*\)")) keys["ord("+m.Groups[1].Value+")"]=keys.GetValueOrDefault("ord("+m.Groups[1].Value+")")+1;
    foreach(Match m in Regex.Matches(text,@"(?i)keyboard_(?:check|check_pressed|check_released)\s*\(\s*(\d{1,3})\s*\)")) keys["keycode "+m.Groups[1].Value]=keys.GetValueOrDefault("keycode "+m.Groups[1].Value)+1;
  }
  if(ui) {
    uiOut.AppendLine("===== "+code.Name?.Content+" =====");
    var lines=text.Split('\n');
    int count=0;
    for(int i=0;i<lines.Length && count<100;i++) if(uiRx.IsMatch(lines[i])) { uiOut.AppendLine($"{i+1}: {lines[i].TrimEnd()}"); count++; }
  }
}
sb.AppendLine($"decompile_ok={ok}");
sb.AppendLine($"decompile_fail={fail}");
sb.AppendLine($"input_relevant_codes={relevant}");
sb.AppendLine("KEY_SUMMARY:");
foreach(var kv in keys.OrderByDescending(x=>x.Value).ThenBy(x=>x.Key)) sb.AppendLine($"  {kv.Key}={kv.Value}");
File.WriteAllText(Path.Combine(outDir,"game-info.txt"),sb.ToString());
File.WriteAllText(Path.Combine(outDir,"input-audit.txt"),inputOut.ToString());
File.WriteAllText(Path.Combine(outDir,"ui-audit.txt"),uiOut.ToString());
Console.WriteLine(sb.ToString());
Console.WriteLine(inputOut.ToString().Substring(0,Math.Min(inputOut.Length,50000)));
