$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$env:PYTHONUTF8='1'
New-Item -ItemType Directory -Force work, report | Out-Null
python -m pip install --upgrade pip gdown | Out-Null

gdown 'https://drive.google.com/uc?id=1Iy5ZMgEM_JP7wxeSNySKD4fdxz3dWo3e' -O work/game.rar
7z x -y work/game.rar -owork/game | Out-Null
$data=Get-ChildItem work/game -Recurse -Filter data.win | Select-Object -First 1
if(!$data){ throw 'data.win missing' }

Invoke-WebRequest -Uri 'https://github.com/UnderminersTeam/UndertaleModTool/releases/download/0.9.2.0/UTMT_CLI_v0.9.2.0-Windows.zip' -OutFile work/utmt.zip
Expand-Archive work/utmt.zip -DestinationPath work/utmt -Force
$cli=Get-ChildItem work/utmt -Recurse -Filter UndertaleModCli.exe | Select-Object -First 1
if(!$cli){ throw 'UTMT CLI missing' }

New-Item -ItemType Directory -Force work/dump | Out-Null
& $cli.FullName dump $data.FullName -c UMT_DUMP_ALL -o work/dump 2>&1 | Tee-Object report/dump-log.txt
if($LASTEXITCODE -ne 0){ throw 'UTMT dump failed' }

$gml=Get-ChildItem work/dump -Recurse -Filter *.gml
$patterns=@(
 'file_text_open_read','file_text_read','file_text_eof',
 'file_bin_open','file_bin_read','buffer_load','buffer_load_ext',
 'ini_open','json_load','json_parse','load_csv','load_ini',
 'file_exists','directory_exists','working_directory','program_directory'
)
$rx='('+($patterns -join '|')+')'
$hits=@($gml | Select-String -Pattern $rx -CaseSensitive:$false)
$hits | ForEach-Object {
  "$($_.Path.Replace((Resolve-Path work/dump).Path,'')):$($_.LineNumber): $($_.Line.Trim())"
} | Set-Content report/all-fileio-hits.txt -Encoding UTF8

$groups=$hits | Group-Object Path | Sort-Object Count -Descending
$groups | ForEach-Object { "$($_.Count) | $($_.Name)" } | Set-Content report/fileio-files.txt

New-Item -ItemType Directory -Force report/gml | Out-Null
foreach($g in $groups){
  $p=[IO.FileInfo]$g.Name
  Copy-Item $p.FullName (Join-Path report/gml $p.Name) -Force
}

@'
ScriptMessage($"DATAFILES={Data.EmbeddedFiles.Count}");
foreach (var f in Data.EmbeddedFiles)
{
    string name = f.Name?.Content ?? "";
    string fn = f.Filename?.Content ?? "";
    ScriptMessage($"DAFL={name}|{fn}|SIZE={f.Data?.Length ?? 0}");
}
'@ | Set-Content work/datafiles.csx -Encoding UTF8
& $cli.FullName load $data.FullName -s work/datafiles.csx -v 2>&1 | Tee-Object report/datafiles.txt
