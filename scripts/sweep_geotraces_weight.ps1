# Sweep GEOTRACES_W to find the alpfe-scav_rat balance point.
#
# GEOTRACES_W=1.0 result (just ran): alpfe broken to cal-grade (0.074 off),
# scav_rat collapses to 0.949 off, R_PICPOC Excellent (0.034 off).
# Hypothesis: lower weight keeps alpfe close-ish to Carroll without
# nuking scav_rat. Sweet spot = both within 40%.
#
# 5 runs sequential, ~80 sec each = ~7 min total.

$ErrorActionPreference = "Continue"
$LogPath = Join-Path $PSScriptRoot "sweep_geotraces_log.txt"
$env:PYTHONIOENCODING = "utf-8"
$env:DARWIN_DATA_ROOT = "D:\ecco_darwin_v5"
$env:GEOTRACES_DATA_ROOT = "D:\geotraces"
$env:NB23_PINN_WEIGHT = "3.0"
$env:NB23_PINN_TYPE = "drift"
$env:NB23_FET_WEIGHT = "1.0"
$env:NB23_SEED = "0"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Output $line
    Add-Content -Path $LogPath -Value $line
}

Write-Log "=== Sweep GEOTRACES_W = 0.05, 0.1, 0.3, 0.5, 1.0 ==="

foreach ($w in @("0.05", "0.1", "0.3", "0.5", "1.0")) {
    $env:GEOTRACES_W = $w
    Write-Log "Running GEOTRACES_W=$w ..."
    $output = & python scripts/run_geotraces_hybrid_quick.py 2>&1
    $verdict = ($output | Select-String "^Verdict:").Line
    $alpfe = ($output | Select-String "^alpfe ").Line
    $scav = ($output | Select-String "^scav_rat ").Line
    Write-Log "  $verdict"
    Write-Log "  $alpfe"
    Write-Log "  $scav"
}

Remove-Item Env:GEOTRACES_W -ErrorAction SilentlyContinue
Write-Log "=== Sweep complete. Results JSONs in data/legacy/scripts_json_archive/run_geotraces_hybrid_result_seed0_w*.json ==="
