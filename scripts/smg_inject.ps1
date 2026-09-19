$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:PYTHONUTF8 = '1'

if (!(Test-Path $env:DATA_WIN)) { throw 'DATA_WIN missing' }
if (!(Test-Path $env:UTMT_CLI)) { throw 'UTMT_CLI missing' }

python scripts/smg_patch_mobile_v3.py work/mobiler

$integration = Get-ChildItem work/mobiler -Recurse -Filter 'Mobile集成脚本.csx' | Select-Object -First 1
if (!$integration) { throw 'Mobile integration script not found' }

$mobileWin = Join-Path $env:GAME_DIR 'data_mobile.win'
& $env:UTMT_CLI load $env:DATA_WIN -s $integration.FullName -o $mobileWin -f -v 2>&1 | Tee-Object work/mobile-injection.log
if ($LASTEXITCODE -ne 0) { throw 'Mobile integration failed' }
if (!(Test-Path $mobileWin)) { throw 'Modified GameMaker data missing' }

# Android-only control cleanup:
# Z remains normal attack; C is reserved for the game's existing magic charge/release logic.
@'
EnsureDataLoaded();
UndertaleModLib.Compiler.CodeImportGroup importGroup = new(Data)
{
    MainThreadAction = MainThreadAction
};
importGroup.QueueReplace("gml_Script_getAttack", @"
var deviceId = getDeviceId();
var keyAttack = keyboard_check_pressed(ord(""Z"")) || gamepad_button_check_pressed(deviceId, gp_face2);
return keyAttack;
");
importGroup.Import();
ScriptMessage("ANDROID_INPUT_PATCH=Z_ATTACK_ONLY_C_MAGIC");
'@ | Set-Content work/separate_attack_magic.csx -Encoding UTF8

$separatedWin = Join-Path $env:GAME_DIR 'data_mobile_separated.win'
& $env:UTMT_CLI load $mobileWin -s work/separate_attack_magic.csx -o $separatedWin -f -v 2>&1 | Tee-Object work/input-separation.log
if ($LASTEXITCODE -ne 0) { throw 'Attack/magic input separation failed' }
if (!(Test-Path $separatedWin)) { throw 'Separated GameMaker data missing' }
$mobileWin = $separatedWin
"MOBILE_WIN=$mobileWin" | Out-File -Append $env:GITHUB_ENV

New-Item -ItemType Directory -Force work/verify-gml | Out-Null
& $env:UTMT_CLI dump $mobileWin -c UMT_DUMP_ALL -o work/verify-gml 2>&1 | Tee-Object work/verify-dump.log

$all = Get-ChildItem work/verify-gml -Recurse -Filter *.gml
$enter = $all | Select-String -Pattern 'virtual_key_smg_enter|virtual_key_add\([^\r\n]*13\)'
$escape = $all | Select-String -Pattern 'virtual_key_smg_escape|virtual_key_add\([^\r\n]*27\)'
$attack = $all | Select-String -Pattern '"ATK"|ord\("Z"\)'
$jump = $all | Select-String -Pattern '"JUMP"|ord\("X"\)'

if (!$enter) { throw 'ENTER mapping missing' }
if (!$escape) { throw 'MENU mapping missing' }
if (!$attack) { throw 'Attack mapping missing' }
if (!$jump) { throw 'Jump mapping missing' }

$attackScript = Get-ChildItem work/verify-gml -Recurse -Filter 'gml_Script_getAttack.gml' | Select-Object -First 1
$playerStep = Get-ChildItem work/verify-gml -Recurse -Filter 'gml_Object_objPlayerAbs_Step_1.gml' | Select-Object -First 1
if (!$attackScript -or !$playerStep) { throw 'Input verification scripts missing' }
$attackText = Get-Content $attackScript.FullName -Raw
$playerText = Get-Content $playerStep.FullName -Raw
if ($attackText -match 'ord\("C"\)') { throw 'C still mapped to normal attack' }
if ($attackText -notmatch 'ord\("Z"\)') { throw 'Z attack mapping missing after separation' }
if ($playerText -notmatch 'keyMagicCharge\s*=\s*keyboard_check\(ord\("C"\)\)') { throw 'C magic charge mapping missing' }
if ($playerText -notmatch 'keyMagicRelease\s*=\s*keyboard_check_released\(ord\("C"\)\)') { throw 'C magic release mapping missing' }

"ENTER_MATCHES=$($enter.Count) ESC_MATCHES=$($escape.Count) ATK_MATCHES=$($attack.Count) JUMP_MATCHES=$($jump.Count) Z_ATTACK_ONLY=1 C_MAGIC_ONLY=1" |
    Tee-Object work/control-verification.txt

try {
    Add-Type -AssemblyName System.Drawing
    $exe = Get-ChildItem $env:GAME_DIR -Filter *.exe | Select-Object -First 1
    if ($exe) {
        $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($exe.FullName)
        if ($icon) {
            $bmp = $icon.ToBitmap()
            $bmp.Save((Join-Path $PWD 'work/game-icon.png'), [System.Drawing.Imaging.ImageFormat]::Png)
            $bmp.Dispose()
            $icon.Dispose()
        }
    }
} catch {
    Write-Warning "Icon extraction failed: $_"
}
