<#
.SYNOPSIS
Runs the repository's grouped UI verification test suites.

.DESCRIPTION
This helper script wraps the project's pytest-based UI checks into named groups so
contributors can run fast theme checks, runtime smoke coverage, visual regression
checks, or the full set from one entry point. It also sets the environment
variables required by the headless Qt and visual-baseline test paths.
#>

param(
    [switch]$Fast,
    [switch]$Runtime,
    [switch]$Visual,
    [switch]$All,
    [switch]$UpdateVisualBaseline
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-PytestGroup {
    <#
    .SYNOPSIS
    Runs a named pytest group and fails immediately if it exits non-zero.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Args
    )
    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & python -m pytest @Args
    if ($LASTEXITCODE -ne 0) {
        throw "pytest group failed: $Name (exit $LASTEXITCODE)"
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    if (-not ($Fast -or $Runtime -or $Visual -or $All)) {
        $All = $true
    }

    $runFast = $All -or $Fast
    $runRuntime = $All -or $Runtime
    $runVisual = $All -or $Visual

    if ($runFast) {
        Invoke-PytestGroup -Name "Fast UI checks" -Args @(
            "tests/test_ui_theme_tokens.py",
            "tests/test_dialog_theme.py",
            "tests/test_main_theme_qss_builder.py",
            "-q"
        )
    }

    if ($runRuntime) {
        $env:QT_QPA_PLATFORM = "offscreen"
        Invoke-PytestGroup -Name "Runtime smoke" -Args @(
            "tests/test_settings_apply_runtime.py",
            "-q"
        )
    }

    if ($runVisual) {
        $env:QT_QPA_PLATFORM = "offscreen"
        $env:PYPAD_VISUAL_BASELINE_MODE = if ($UpdateVisualBaseline) { "update" } else { "compare" }
        if (-not $env:PYPAD_VISUAL_AHASH_THRESHOLD) {
            $env:PYPAD_VISUAL_AHASH_THRESHOLD = "6"
        }
        Invoke-PytestGroup -Name "Visual smoke" -Args @(
            "tests/test_ui_visual_smoke_screenshots.py",
            "-q"
        )
    }

    Write-Host ""
    Write-Host "UI checks completed successfully." -ForegroundColor Green
}
finally {
    Pop-Location
}
