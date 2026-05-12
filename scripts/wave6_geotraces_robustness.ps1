# Wave 6 — three questions a reviewer will ask about the v2.6 result.
#
# Q1 (statistical robustness): is the 5-seed Smallgrow Excellent finding
# stable when extended to 10 seeds? Multi-seed seeds 5-9 at GEOTRACES_W=0.3.
#
# Q2 (isolation): does GEOTRACES carry the result, or is the PINN drift
# term doing the work? Run with PINN_W=0 (GEOTRACES alone, no PINN).
#
# Q3 (PINN dominance): at extreme PINN weight (10.0), does the result
# improve, degrade, or stay the same? Tests whether PINN is the active
# constraint or just a backstop.
#
# 7 runs sequential, ~80 sec each on RTX 5090 Laptop = ~10 min wall-clock.

$ErrorActionPreference = "Continue"
$LogPath = Join-Path $PSScriptRoot "wave6_robustness_log.txt"
$env:PYTHONIOENCODING = "utf-8"
$env:DARWIN_DATA_ROOT = "D:\ecco_darwin_v5"
$env:GEOTRACES_DATA_ROOT = "D:\geotraces"
$env:NB23_FET_WEIGHT = "1.0"
$env:NB23_RAW_FET_WEIGHT = "0.0"
$env:NB23_PINN_TYPE = "drift"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Output $line
    Add-Content -Path $LogPath -Value $line
}

$experiments = @(
    # Q1: extended multi-seed (seeds 5-9) at GEOTRACES_W=0.3, PINN drift w=3.0.
    @{ seed = "5"; geotraces_w = "0.3"; pinn_w = "3.0"; label = "Multi-seed 5" },
    @{ seed = "6"; geotraces_w = "0.3"; pinn_w = "3.0"; label = "Multi-seed 6" },
    @{ seed = "7"; geotraces_w = "0.3"; pinn_w = "3.0"; label = "Multi-seed 7" },
    @{ seed = "8"; geotraces_w = "0.3"; pinn_w = "3.0"; label = "Multi-seed 8" },
    @{ seed = "9"; geotraces_w = "0.3"; pinn_w = "3.0"; label = "Multi-seed 9" },
    # Q2: isolate the GEOTRACES contribution (no PINN).
    @{ seed = "0"; geotraces_w = "0.3"; pinn_w = "0.0"; label = "Isolation: GEOTRACES alone, no PINN" },
    # Q3: extreme PINN weight, see if it dominates or breaks.
    @{ seed = "0"; geotraces_w = "0.3"; pinn_w = "10.0"; label = "Extreme: PINN drift w=10.0" }
)

Write-Log "=== Wave 6: $($experiments.Count) experiments queued ==="

foreach ($exp in $experiments) {
    $env:NB23_SEED = $exp.seed
    $env:GEOTRACES_W = $exp.geotraces_w
    $env:NB23_PINN_WEIGHT = $exp.pinn_w
    Write-Log "Running: $($exp.label) [seed=$($exp.seed) geo=$($exp.geotraces_w) pinn=$($exp.pinn_w)]"
    $output = & python scripts/run_geotraces_hybrid_quick.py 2>&1
    $verdict = ($output | Select-String "^Verdict:").Line
    Write-Log "  $verdict"
    foreach ($p in @("alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC")) {
        $row = ($output | Select-String "^$p ").Line
        if ($row) { Write-Log "  $row" }
    }
}

Remove-Item Env:NB23_SEED -ErrorAction SilentlyContinue
Remove-Item Env:GEOTRACES_W -ErrorAction SilentlyContinue
Remove-Item Env:NB23_PINN_WEIGHT -ErrorAction SilentlyContinue
Write-Log "=== Wave 6 done ==="
