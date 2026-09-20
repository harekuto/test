$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

python happyheart/patch_mobile.py work/mobiler

$integration=Get-ChildItem work/mobiler -Recurse -Filter 'Mobile集成脚本.csx' | Select-Object -First 1
if(!$integration){ throw 'Mobile integration script missing' }

$stage1=Join-Path $env:GAME_DIR 'data_mobile_stage1.win'
& $env:UTMT_CLI load $env:DATA_WIN -s $integration.FullName -o $stage1 -f -v 2>&1 | Tee-Object work/mobile-injection.log
if($LASTEXITCODE -ne 0){ throw 'Mobile integration failed' }
if(!(Test-Path $stage1)){ throw 'Stage-1 mobile data missing' }

Remove-Item work/stability-dump -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item work/stability-patches -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force work/stability-dump,work/stability-patches | Out-Null

& $env:UTMT_CLI dump $stage1 -c UMT_DUMP_ALL -o work/stability-dump 2>&1 | Tee-Object work/stability-dump.log
if($LASTEXITCODE -ne 0){ throw 'Stage-1 stability dump failed' }

python happyheart/patch_stability.py work/stability-dump work/stability-patches 2>&1 | Tee-Object work/stability-source-patch.log
if($LASTEXITCODE -ne 0){ throw 'Stability source patch failed' }

$env:HHP_PATCH_DIR=(Resolve-Path work/stability-patches).Path
$stableWin=Join-Path $env:GAME_DIR 'data_mobile.win'
& $env:UTMT_CLI load $stage1 -s happyheart/apply_stability.csx -o $stableWin -f -v 2>&1 | Tee-Object work/stability-import.log
if($LASTEXITCODE -ne 0){ throw 'Stability patch import failed' }
if(!(Test-Path $stableWin)){ throw 'Final mobile data missing' }
"MOBILE_WIN=$stableWin" | Out-File -Append $env:GITHUB_ENV

Remove-Item work/verify -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force work/verify | Out-Null
& $env:UTMT_CLI dump $stableWin -c UMT_DUMP_ALL -o work/verify 2>&1 | Tee-Object work/verify-dump.log
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
 '"HEAVY"',
 'file_exists("supporters.txt")',
 'file_text_open_write("agreement.txt")',
 'file_exists("credits.txt")',
 'file_exists("Input")',
 'if (file < 0)',
 'if (file3 < 0)',
 'if (file2 < 0)',
 'file_exists("dlc/dlc_sam.png")'
)
foreach($c in $checks){
  $m=@($gml | Select-String -SimpleMatch $c)
  if($m.Count -eq 0){ throw "Injected/patch control missing after decompile: $c" }
  "$c=$($m.Count)" | Add-Content work/control-verification.txt
}
$unsafe=@($gml | Select-String -SimpleMatch 'working_directory + "agreement.txt"')
if($unsafe.Count -gt 0){ throw 'Unsafe agreement working_directory path survived stability patch' }

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
