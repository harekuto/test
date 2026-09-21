$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
New-Item -ItemType Directory -Force work/dialogue-audit | Out-Null

./happyheart/prepare.ps1

Remove-Item work/dialogue-dump -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force work/dialogue-dump | Out-Null
& $env:UTMT_CLI dump $env:DATA_WIN -c UMT_DUMP_ALL -o work/dialogue-dump 2>&1 | Tee-Object work/dialogue-audit/dump-log.txt
if($LASTEXITCODE -ne 0){ throw 'UTMT dialogue dump failed' }

$gml=Get-ChildItem work/dialogue-dump -Recurse -Filter *.gml
$patterns=@(
  'Press interact to continue',
  'press interact',
  'global.interact',
  'keyboard_check_pressed',
  'keyboard_check\(',
  '\binteract\b',
  'textbox',
  'dialog',
  'conversation'
)
$rx='('+($patterns -join '|')+')'
$hits=@($gml | Select-String -Pattern $rx -CaseSensitive:$false)
$hits | ForEach-Object {
  "$($_.Path.Replace((Resolve-Path work/dialogue-dump).Path,'')):$($_.LineNumber): $($_.Line.Trim())"
} | Set-Content work/dialogue-audit/hits.txt -Encoding UTF8

$groups=$hits | Group-Object Path | Sort-Object Count -Descending
$groups | ForEach-Object { "$($_.Count) | $($_.Name)" } | Set-Content work/dialogue-audit/files.txt

New-Item -ItemType Directory -Force work/dialogue-audit/gml | Out-Null
foreach($g in $groups | Select-Object -First 80){
  Copy-Item $g.Name (Join-Path work/dialogue-audit/gml ([IO.FileInfo]$g.Name).Name) -Force
}
