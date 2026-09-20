using System;
using System.IO;
using UndertaleModLib.Compiler;

EnsureDataLoaded();

string patchDir = Environment.GetEnvironmentVariable("HHP_PATCH_DIR");
if (String.IsNullOrWhiteSpace(patchDir) || !Directory.Exists(patchDir))
{
    throw new ScriptException("HHP_PATCH_DIR is missing or invalid.");
}

string[] files = Directory.GetFiles(patchDir, "*.gml", SearchOption.TopDirectoryOnly);
if (files.Length == 0)
{
    throw new ScriptException("No stability GML patches found.");
}

CodeImportGroup importGroup = new(Data);
foreach (string file in files)
{
    string codeName = Path.GetFileNameWithoutExtension(file);
    if (Data.Code.ByName(codeName) is null)
    {
        throw new ScriptException("Target code entry missing: " + codeName);
    }
    importGroup.QueueReplace(codeName, File.ReadAllText(file));
}
importGroup.Import();
ScriptMessage("HHP_ANDROID_STABILITY_PATCHES=" + files.Length);
