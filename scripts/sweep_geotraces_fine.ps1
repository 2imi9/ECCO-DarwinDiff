# Fine GEOTRACES_W sweep in the transition zone where alpfe goes
# Cal-grade but scav_rat hasn't yet collapsed. The existing sweep showed
# a sharp transition between w<=0.1 (alpfe stuck) and w>=0.3 (alpfe ok,
# scav_rat broken). This fine sweep at 0.15 / 0.20 / 0.25 tests whether
# there's a smooth middle ground or whether the transition is genuinely
# abrupt.
#
# 3 runs sequential, ~80 sec each = ~5 min.

$ErrorActionPreference = "Continue"
$LogPath = Join-Path $PSScriptRoot "sweep_geotraces_fine_log.txt"
$env:PYTHONIOENCODING = "utf-8"
$env:DARWIN_DATA_ROOT = "D:\ecco_darwin_v5"
$env:GEOTRACES_DATA_ROOT = "D:\geotraces"
$env:NB23_FET_WEIGHT = "1.0"
$env:NB23_PINN_TYPE = "drift"
$env:NB23_PINN_WEIGHT = "3.0"
$env:NB23_RAW_FET_WEIGHT = "0.0"
$env:NB23_SEED = "0"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Output $line
    Add-Content -Path $LogPath -Value $line
}

Write-Log "=== Fine sweep GEOTRACES_W = 0.15, 0.20, 0.25 ==="

foreach ($w in @("0.15", "0.2", "0.25")) {
    $env:GEOTRACES_W = $w
    Write-Log "Running GEOTRACES_W=$w ..."
    $output = & python scripts/run_geotraces_hybrid_quick.py 2>&1
    $verdict = ($output | Select-String "^Verdict:").Line
    Write-Log "  $verdict"
    foreach ($p in @("alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC")) {
        $row = ($output | Select-String "^$p ").Line
        if ($row) { Write-Log "  $row" }
    }
}

Remove-Item Env:GEOTRACES_W -ErrorAction SilentlyContinue
Write-Log "=== Fine sweep done ==="
