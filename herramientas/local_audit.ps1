param()

$ErrorActionPreference = "Stop"
$root = (Get-Location).Path
$out = Join-Path $root "docs\_local_audit"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$exclude = @(".git",".venv","venv","node_modules","dist","build","__pycache__","logs","reports","data","epub",".streamlit",".pytest_cache")

function IsExcluded([string]$full){
  foreach($e in $exclude){
    if($full -match "\\$([regex]::Escape($e))($|\\)"){ return $true }
  }
  return $false
}

# META
"DATE: $(Get-Date -Format o)" | Set-Content (Join-Path $out "SUMMARY.txt") -Encoding utf8
"ROOT: $root" | Add-Content (Join-Path $out "SUMMARY.txt") -Encoding utf8
"PS: $($PSVersionTable.PSVersion)" | Add-Content (Join-Path $out "SUMMARY.txt") -Encoding utf8

# Detectar Python (prioriza venv)
$py = Join-Path $root ".venv\Scripts\python.exe"
if (!(Test-Path $py)) { $py = "py -3.11" }

# Python info + pip freeze (si puede)
try {
  & $py -V 2>&1 | Out-File (Join-Path $out "python_version.txt") -Encoding utf8
  & $py -m pip --version 2>&1 | Out-File (Join-Path $out "pip_version.txt") -Encoding utf8
  & $py -m pip freeze 2>&1 | Out-File (Join-Path $out "pip_freeze.txt") -Encoding utf8
} catch {
  "PY/PIP ERROR: $($_.Exception.Message)" | Out-File (Join-Path $out "pip_freeze.txt") -Encoding utf8
}

# Key files
"KEY FILES:" | Add-Content (Join-Path $out "SUMMARY.txt") -Encoding utf8
Get-ChildItem -File -Force -Path $root |
  Where-Object { $_.Name -in @("main.py","app.py","requirements.txt","pyproject.toml","setup.py","tasks.ps1") } |
  ForEach-Object { " - $($_.Name)" } | Add-Content (Join-Path $out "SUMMARY.txt") -Encoding utf8

# Entrypoints (busca cómo se arranca)
$entry = Join-Path $out "ENTRYPOINTS.txt"
"" | Set-Content $entry -Encoding utf8
Get-ChildItem -Recurse -Force -File -Path $root |
  Where-Object { -not (IsExcluded $_.FullName) -and $_.Extension -in @(".py",".ps1",".bat",".cmd") } |
  ForEach-Object {
    Select-String -Path $_.FullName -Pattern "streamlit run|__main__|if __name__|main\(|run\(|typer\.|click\.|argparse" -SimpleMatch -ErrorAction SilentlyContinue |
    ForEach-Object { "$($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
  } | Out-File $entry -Encoding utf8

# Top archivos grandes (para saber qué infla todo)
Get-ChildItem -Recurse -Force -File -Path $root |
  Where-Object { -not (IsExcluded $_.FullName) } |
  Sort-Object Length -Descending |
  Select-Object -First 120 FullName, Length |
  Out-File (Join-Path $out "TOP_BIG_FILES.txt") -Encoding utf8

# Tree dirs (sin basura)
Get-ChildItem -Recurse -Force -Directory -Path $root |
  Where-Object { -not (IsExcluded $_.FullName) } |
  ForEach-Object { $_.FullName.Replace($root,".") } |
  Out-File (Join-Path $out "TREE_DIRS.txt") -Encoding utf8

# ZIP final
$zip = Join-Path $root "ZER0X_local_audit.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $out\* -DestinationPath $zip -Force

"OK: $zip" | Add-Content (Join-Path $out "SUMMARY.txt") -Encoding utf8
Write-Host "OK: creado $zip"
