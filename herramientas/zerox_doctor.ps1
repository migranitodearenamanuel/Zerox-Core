param()

$ErrorActionPreference="Stop"
$root=(Get-Location).Path
$outDir=Join-Path $root "docs\_local_doctor"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$runNow=Join-Path $outDir "RUN_NOW.txt"
$report=Join-Path $outDir "REPORT.txt"

function FindFiles([string]$name){
  Get-ChildItem -Recurse -Force -File -Filter $name -ErrorAction SilentlyContinue
}

function PreferPath($items, $regex){
  $m = $items | Where-Object { $_.FullName -match $regex } | Select-Object -First 1
  if ($m) { return $m }
  return ($items | Select-Object -First 1)
}

"ROOT: $root" | Set-Content $report -Encoding utf8
"DATE: $(Get-Date -Format o)" | Add-Content $report -Encoding utf8
"" | Set-Content $runNow -Encoding utf8

# --- NODE: detecta interfaz y electron ---
$pkgs = FindFiles "package.json"
$pkgInterfaz = PreferPath ($pkgs | Where-Object { $_.FullName -match "\\interfaz\\package\.json$" }) "\\interfaz\\package\.json$"
$pkgElectron = PreferPath ($pkgs | Where-Object { $_.FullName -match "\\electron\\package\.json$" }) "\\electron\\package\.json$"

function AddNodeBlock($pkgPath, $label){
  if (-not $pkgPath) { return }
  Add-Content $report "FOUND $label package.json: $($pkgPath.FullName)" -Encoding utf8
  try {
    $json = Get-Content $pkgPath.FullName -Raw -Encoding utf8 | ConvertFrom-Json
    $scripts = $json.scripts
    Add-Content $report "SCRIPTS ($label):" -Encoding utf8
    $scripts.PSObject.Properties | ForEach-Object { Add-Content $report (" - " + $_.Name + " = " + $_.Value) -Encoding utf8 }

    $dir = Split-Path $pkgPath.FullName -Parent
    Add-Content $runNow "" -Encoding utf8
    Add-Content $runNow ("# === ARRANQUE " + $label.ToUpper() + " ===") -Encoding utf8
    Add-Content $runNow ("cd `"$dir`"") -Encoding utf8
    Add-Content $runNow "npm install" -Encoding utf8

    if ($scripts.PSObject.Properties.Name -contains "dev") {
      Add-Content $runNow "npm run dev" -Encoding utf8
    } elseif ($scripts.PSObject.Properties.Name -contains "start") {
      Add-Content $runNow "npm run start" -Encoding utf8
    } else {
      Add-Content $runNow "npm run" -Encoding utf8
    }
  } catch {
    Add-Content $report "ERROR leyendo $label package.json: $($_.Exception.Message)" -Encoding utf8
  }
}

AddNodeBlock $pkgInterfaz "interfaz"
AddNodeBlock $pkgElectron "electron"

# --- PYTHON: requirements + posible entrypoint ---
$reqs = FindFiles "requirements.txt"
$pyprojs = FindFiles "pyproject.toml"

$reqPick = PreferPath $reqs "\\nucleo\\|\\src\\|\\inteligencia\\"
if ($reqPick) { Add-Content $report "FOUND requirements.txt: $($reqPick.FullName)" -Encoding utf8 }
$pyprojPick = PreferPath $pyprojs "\\nucleo\\|\\src\\|\\inteligencia\\"
if ($pyprojPick) { Add-Content $report "FOUND pyproject.toml: $($pyprojPick.FullName)" -Encoding utf8 }

# Buscar entrypoints python típicos
$cands = Get-ChildItem -Recurse -Force -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Extension -eq ".py" -and $_.Name -match "^(main|app|run|server|ui|streamlit_app)\.py$" }

# Rank simple: preferir nucleo/src y que contenga streamlit/fastapi
function ScorePy($file){
  $s=0
  if ($file.FullName -match "\\nucleo\\|\\src\\") { $s += 5 }
  try {
    $txt = Get-Content $file.FullName -Raw -ErrorAction Stop
    if ($txt -match "streamlit") { $s += 10 }
    if ($txt -match "FastAPI|uvicorn") { $s += 8 }
    if ($txt -match "__name__\s*==\s*['""]__main__['""]") { $s += 3 }
  } catch {}
  return $s
}

$best = $null
$bestScore = -1
foreach($f in $cands){
  $sc = ScorePy $f
  if ($sc -gt $bestScore){
    $bestScore = $sc
    $best = $f
  }
}

if ($best) {
  Add-Content $report "BEST python entrypoint candidate: $($best.FullName) (score=$bestScore)" -Encoding utf8

  Add-Content $runNow "" -Encoding utf8
  Add-Content $runNow "# === ARRANQUE PYTHON (VENV EN RAIZ) ===" -Encoding utf8
  Add-Content $runNow ("cd `"$root`"") -Encoding utf8
  Add-Content $runNow "if (!(Test-Path .\.venv)) { py -3.11 -m venv .venv }" -Encoding utf8
  Add-Content $runNow ".\.venv\Scripts\Activate.ps1" -Encoding utf8
  Add-Content $runNow "python -m pip install -U pip setuptools wheel" -Encoding utf8

  if ($reqPick) {
    Add-Content $runNow ("pip install -r `"$($reqPick.FullName)`"") -Encoding utf8
  } elseif ($pyprojPick) {
    $projDir = Split-Path $pyprojPick.FullName -Parent
    Add-Content $runNow ("pip install -e `"$projDir`"") -Encoding utf8
  } else {
    Add-Content $runNow "# NO encuentro requirements/pyproject. Busca en REPORT.txt" -Encoding utf8
  }

  # Ejecutar como script o streamlit si detecta streamlit
  $content = ""
  try { $content = Get-Content $best.FullName -Raw } catch {}
  if ($content -match "streamlit") {
    Add-Content $runNow ("python -m streamlit run `"$($best.FullName)`"") -Encoding utf8
  } else {
    Add-Content $runNow ("python `"$($best.FullName)`"") -Encoding utf8
  }
} else {
  Add-Content $report "NO python entrypoint found (main/app/run/server/ui/streamlit_app). Mira estructura manual." -Encoding utf8
}

Write-Host "OK: generado"
Write-Host $report
Write-Host $runNow
