param()

$ErrorActionPreference = "Stop"

# Detectar raíz del repo
$root = git rev-parse --show-toplevel 2>$null
if (-not $root) { throw "No estoy dentro de un repo git." }
Set-Location $root

$out = Join-Path $root "docs\_support_pack"
New-Item -ItemType Directory -Force -Path $out | Out-Null

# 1) Info base
"DATE: $(Get-Date -Format o)" | Set-Content (Join-Path $out "meta.txt")
"ROOT: $root" | Add-Content (Join-Path $out "meta.txt")
"PY: $(& py -3.11 -V 2>$null)" | Add-Content (Join-Path $out "meta.txt")

# 2) Git
(git status) | Out-File (Join-Path $out "git_status.txt") -Encoding utf8
(git log -1 --oneline) | Out-File (Join-Path $out "git_head.txt") -Encoding utf8
(git remote -v) | Out-File (Join-Path $out "git_remote.txt") -Encoding utf8

# 3) Árbol (sin volcar binarios)
(Get-ChildItem -Force -Recurse -Directory |
  Select-Object FullName |
  ForEach-Object { $_.FullName.Replace($root,".") }) |
  Out-File (Join-Path $out "tree_dirs.txt") -Encoding utf8

# 4) Top archivos más grandes (para matar el problema de 2GB)
(Get-ChildItem -Force -Recurse -File |
  Sort-Object Length -Descending |
  Select-Object -First 80 FullName, Length) |
  Out-File (Join-Path $out "top_big_files.txt") -Encoding utf8

# 5) Dependencias (si hay venv, mejor; si no, al menos pip freeze)
try {
  $py = ".\.venv\Scripts\python.exe"
  if (Test-Path $py) {
    & $py -m pip freeze | Out-File (Join-Path $out "pip_freeze.txt") -Encoding utf8
  } else {
    & py -3.11 -m pip freeze | Out-File (Join-Path $out "pip_freeze.txt") -Encoding utf8
  }
} catch {
  "pip freeze failed: $($_.Exception.Message)" | Out-File (Join-Path $out "pip_freeze.txt") -Encoding utf8
}

# 6) Buscar posibles secretos (solo rutas + línea, no valores)
$patterns = @(
  "API_KEY","APISECRET","API_SECRET","PASSPHRASE","SECRET","PASSWORD","PRIVATE_KEY",
  "BITGET","BINANCE","BYBIT","OPENAI","ANTHROPIC"
)

$codeDirs = @("src","tests","main.py","app.py",".env",".env.*","config*","settings*")
$hits = @()

foreach ($p in $patterns) {
  $r = Get-ChildItem -Recurse -Force -ErrorAction SilentlyContinue |
       Where-Object { $_.FullName -match "\\(src|tests)\\" -and -not $_.PSIsContainer } |
       Select-String -Pattern $p -SimpleMatch -ErrorAction SilentlyContinue |
       Select-Object Path, LineNumber, Line
  if ($r) { $hits += $r }
}

$hits | ForEach-Object {
  # enmascarar posible valor si aparece "KEY=xxxxx"
  $line = $_.Line -replace "=.+","=***"
  "$($_.Path):$($_.LineNumber): $line"
} | Out-File (Join-Path $out "secret_scan.txt") -Encoding utf8

# 7) Comprimir
$zip = Join-Path $root "ZER0X_support_pack.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $out\* -DestinationPath $zip -Force

"OK: generado $zip"
