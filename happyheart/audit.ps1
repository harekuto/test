$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$env:PYTHONUTF8='1'

New-Item -ItemType Directory -Force work, report | Out-Null
python -m pip install --upgrade pip gdown | Out-Null

gdown 'https://drive.google.com/uc?id=1Iy5ZMgEM_JP7wxeSNySKD4fdxz3dWo3e' -O work/game.rar
if(!(Test-Path work/game.rar)){ throw 'download failed' }
$hash=(Get-FileHash work/game.rar -Algorithm SHA256).Hash.ToLower()
"ARCHIVE_SHA256=$hash" | Tee-Object report/archive-sha256.txt

7z x -y work/game.rar -owork/game | Out-Null
$data=Get-ChildItem work/game -Recurse -Filter data.win | Select-Object -First 1
if(!$data){ throw 'data.win not found' }
$gameDir=$data.DirectoryName
"DATA_WIN=$($data.FullName)" | Out-File -Append $env:GITHUB_ENV
"GAME_DIR=$gameDir" | Out-File -Append $env:GITHUB_ENV

$controls=Get-ChildItem work/game -Recurse -Filter CONTROLS.txt | Select-Object -First 1
if($controls){ Copy-Item $controls.FullName report/CONTROLS.txt -Force }

Invoke-WebRequest -Uri 'https://github.com/UnderminersTeam/UndertaleModTool/releases/download/0.9.2.0/UTMT_CLI_v0.9.2.0-Windows.zip' -OutFile work/utmt.zip
Expand-Archive work/utmt.zip -DestinationPath work/utmt -Force
$cli=Get-ChildItem work/utmt -Recurse -Filter UndertaleModCli.exe | Select-Object -First 1
if(!$cli){ throw 'UTMT CLI missing' }
"UTMT_CLI=$($cli.FullName)" | Out-File -Append $env:GITHUB_ENV

@'
ScriptMessage($"GM_EXACT={Data.GeneralInfo.Major}.{Data.GeneralInfo.Minor}.{Data.GeneralInfo.Release}.{Data.GeneralInfo.Build};BC={Data.GeneralInfo.BytecodeVersion};YYC={Data.IsYYC()}");
ScriptMessage($"GAME_NAME={Data.GeneralInfo.Name.Content};DISPLAY={Data.GeneralInfo.DefaultWindowWidth}x{Data.GeneralInfo.DefaultWindowHeight}");
ScriptMessage($"ROOMS={Data.Rooms.Count};OBJECTS={Data.GameObjects.Count};CODE={Data.Code.Count};SPRITES={Data.Sprites.Count};SOUNDS={Data.Sounds.Count}");
for (int i = 0; i < Data.Rooms.Count && i < 30; i++)
{
    var room = Data.Rooms[i];
    ScriptMessage($"ROOM={room.Name.Content};SIZE={room.Width}x{room.Height}");
}
'@ | Set-Content work/meta.csx -Encoding UTF8

& $cli.FullName load $data.FullName -s work/meta.csx -v 2>&1 | Tee-Object report/version-room.txt
if($LASTEXITCODE -ne 0){ throw 'UTMT metadata read failed' }

New-Item -ItemType Directory -Force work/dump | Out-Null
& $cli.FullName dump $data.FullName -c UMT_DUMP_ALL -o work/dump 2>&1 | Tee-Object report/dump-log.txt
if($LASTEXITCODE -ne 0){ throw 'UTMT dump failed' }

$gml=Get-ChildItem work/dump -Recurse -Filter *.gml
"DECOMPILED_GML=$($gml.Count)" | Tee-Object report/gml-count.txt

$patterns=@(
 'keyboard_check','keyboard_check_pressed','keyboard_check_released','vk_','ord\(',
 'gamepad_','mouse_check','display_set_gui','display_get_gui','window_set_size',
 'room_width','room_height','application_surface','draw_gui','pause','menu'
)
$rx='('+($patterns -join '|')+')'
$hits=$gml | Select-String -Pattern $rx -CaseSensitive:$false
$hits | Select-Object -First 12000 | ForEach-Object {
  "$($_.Path.Replace((Resolve-Path work/dump).Path,'')):$($_.LineNumber): $($_.Line.Trim())"
} | Set-Content report/input-ui-hits.txt -Encoding UTF8

$keys=@('vk_left','vk_right','vk_up','vk_down','vk_enter','vk_escape','vk_space','vk_shift','vk_control','vk_tab','vk_backspace','ord("Z")','ord("X")','ord("C")','ord("A")','ord("S")','ord("D")','ord("W")','ord("E")','ord("Q")','ord("R")','ord("F")')
foreach($k in $keys){
  $m=@($gml | Select-String -SimpleMatch $k)
  if($m.Count -gt 0){
    "===== $k ($($m.Count)) =====" | Add-Content report/key-semantics.txt
    $m | Select-Object -First 80 | ForEach-Object {
      "$($_.Path.Replace((Resolve-Path work/dump).Path,'')):$($_.LineNumber): $($_.Line.Trim())"
    } | Add-Content report/key-semantics.txt
  }
}

$interesting=$hits | Group-Object Path | Sort-Object Count -Descending | Select-Object -First 80
$interesting | ForEach-Object { "$($_.Count) | $($_.Name)" } | Set-Content report/interesting-files.txt

New-Item -ItemType Directory -Force report/gml | Out-Null
foreach($group in $interesting | Select-Object -First 35){
  $p=[IO.FileInfo]$group.Name
  Copy-Item $p.FullName (Join-Path report/gml $p.Name) -Force
}

$fileHits=$gml | Select-String -Pattern 'file_(text_)?(open|read|write|exists|delete|rename|copy|find)|working_directory|program_directory|environment_get_variable' -CaseSensitive:$false
$fileHits | Select-Object -First 20000 | ForEach-Object {
  "$($_.Path.Replace((Resolve-Path work/dump).Path,'')):$($_.LineNumber): $($_.Line.Trim())"
} | Set-Content report/file-io-hits.txt -Encoding UTF8

Get-ChildItem $gameDir -Recurse -File | Select-Object FullName,Length | Format-Table -AutoSize | Out-String -Width 400 | Set-Content report/game-files.txt
