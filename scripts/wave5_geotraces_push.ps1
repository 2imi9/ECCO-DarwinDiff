# Wave 5 — push the new GEOTRACES_W=0.3 4/6 baseline toward 5/6 or 6/6.
#
# The 4/6 from GEOTRACES_W=0.3 has alpfe Cal-grade + Smallgrow Excellent
# (0.002 off Carroll — project-first). scav_rat and R_PICPOC are the
# casualties. Try three angles:
#
#   1-2. Combo with raw_fet — adds Darwin-internal iron magnitude as a
#        second pin. Hypothesis: two magnitude constraints together
#        preserve scav_rat while keeping alpfe locked.
#   3.   Higher PINN drift weight — tighter iron mass-balance constraint
#        might force scav_rat back to physical values.
#   4-7. Multi-seed of GEOTRACES_W=0.3 baseline — verify the 4/6 +
#        Smallgrow-Excellent reproduces across seeds (was seed=0 only).
#
# 7 runs sequential, ~80 sec each = ~10 min.

$ErrorActionPreference = "Continue"
$LogPath = Join-Path $PSScriptRoot "wave5_geotraces_log.txt"
$env:PYTHONIOENCODING = "utf-8"
$env:DARWIN_DATA_ROOT = "D:\ecco_darwin_v5"
$env:GEOTRACES_DATA_ROOT = "D:\geotraces"
$env:NB23_FET_WEIGHT = "1.0"
$env:NB23_PINN_TYPE = "drift"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Output $line
    Add-Content -Path $LogPath -Value $line
}

# Each row: seed, geotraces_w, raw_fet_w, pinn_w, label.
$experiments = @(
    @{ seed = "0"; geotraces_w = "0.3"; raw_fet_w = "0.005"; pinn_w = "3.0"; label = "Combo: GEO 0.3 + raw_fet 0.005" },
    @{ seed = "0"; geotraces_w = "0.3"; raw_fet_w = "0.01";  pinn_w = "3.0"; label = "Combo: GEO 0.3 + raw_fet 0.01" },
    @{ seed = "0"; geotraces_w = "0.3"; raw_fet_w = "0.0";   pinn_w = "5.0"; label = "PINN drift 5.0" },
    @{ seed = "1"; geotraces_w = "0.3"; raw_fet_w = "0.0";   pinn_w = "3.0"; label = "Multi-seed 1" },
    @{ seed = "2"; geotraces_w = "0.3"; raw_fet_w = "0.0";   pinn_w = "3.0"; label = "Multi-seed 2" },
    @{ seed = "3"; geotraces_w = "0.3"; raw_fet_w = "0.0";   pinn_w = "3.0"; label = "Multi-seed 3" },
    @{ seed = "4"; geotraces_w = "0.3"; raw_fet_w = "0.0";   pinn_w = "3.0"; label = "Multi-seed 4" }
)

Write-Log "=== Wave 5: $($experiments.Count) experiments queued ==="

foreach ($exp in $experiments) {
    $env:NB23_SEED = $exp.seed
    $env:GEOTRACES_W = $exp.geotraces_w
    $env:NB23_RAW_FET_WEIGHT = $exp.raw_fet_w
    $env:NB23_PINN_WEIGHT = $exp.pinn_w
    Write-Log "Running: $($exp.label) [seed=$($exp.seed) geo=$($exp.geotraces_w) raw_fet=$($exp.raw_fet_w) pinn=$($exp.pinn_w)]"
    $output = & python scripts/run_geotraces_hybrid_quick.py 2>&1
    $verdict = ($output | Select-String "^Verdict:").Line
    Write-Log "  $verdict"
    foreach ($p in @("alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC")) {
        $row = ($output | Select-String "^$p ").Line
        if ($row) { Write-Log "  $row" }
    }
}

Remove-Item Env:GEOTRACES_W -ErrorAction SilentlyContinue
Remove-Item Env:NB23_RAW_FET_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_PINN_WEIGHT -ErrorAction SilentlyContinue
Remove-Item Env:NB23_SEED -ErrorAction SilentlyContinue
Write-Log "=== Wave 5 done. JSONs in data/legacy/scripts_json_archive/run_geotraces_hybrid_result_*.json ==="
