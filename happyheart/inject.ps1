$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
python happyheart/patch_mobile.py work/mobiler

$integration=Get-ChildItem work/mobiler -Recurse -Filter 'Mobile集成脚本.csx' | Select-Object -First 1
if(!$integration){ throw 'Mobile integration script missing' }

$mobileWin=Join-Path $env:GAME_DIR 'data_mobile.win'
& $env:UTMT_CLI load $env:DATA_WIN -s $integration.FullName -o $mobileWin -f -v 2>&1 | Tee-Object work/mobile-injection.log
if($LASTEXITCODE -ne 0){ throw 'Mobile integration failed' }
if(!(Test-Path $mobileWin)){ throw 'data_mobile.win missing' }
"MOBILE_WIN=$mobileWin" | Out-File -Append $env:GITHUB_ENV

New-Item -ItemType Directory -Force work/verify | Out-Null
& $env:UTMT_CLI dump $mobileWin -c UMT_DUMP_ALL -o work/verify 2>&1 | Tee-Object work/verify-dump.log
if($LASTEXITCODE -ne 0){ throw 'Modified data decompile failed' }

$gml=Get-ChildItem work/verify -Recurse -Filter *.gml
$checks=@(
 'virtual_key_hhp_interact',
 'virtual_key_hhp_dash',
 'virtual_key_hhp_item1',
 'virtual_key_hhp_item2',
 'virtual_key_hhp_retry',
 'virtual_key_hhp_back',
 '"E / OK"',
 '"LIGHT"',
 '"HEAVY"'
)
foreach($c in $checks){
  $m=@($gml | Select-String -SimpleMatch $c)
  if($m.Count -eq 0){ throw "Injected control missing after decompile: $c" }
  "$c=$($m.Count)" | Add-Content work/control-verification.txt
}

try {
  Add-Type -AssemblyName System.Drawing
  $exe=Get-ChildItem $env:GAME_DIR -Filter *.exe | Select-Object -First 1
  if($exe){
    $icon=[System.Drawing.Icon]::ExtractAssociatedIcon($exe.FullName)
    if($icon){
      $bmp=$icon.ToBitmap()
      $bmp.Save((Join-Path $PWD 'work/game-icon.png'),[System.Drawing.Imaging.ImageFormat]::Png)
      $bmp.Dispose(); $icon.Dispose()
    }
  }
} catch { Write-Warning "Icon extraction failed: $_" }
