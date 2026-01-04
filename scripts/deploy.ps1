# AIDX Fusion360 Addin Deploy Script
# Deploy Addin files from repository to Fusion360 AddIns directory

param(
    [switch]$Clean = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# Paths
$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourceDir = Join-Path $RepoRoot "addins\fusion360\AIDX"
$TargetDir = "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\AddIns\AIDX"

Write-Host "[INFO] AIDX Fusion360 Addin Deploy Script" -ForegroundColor Cyan
Write-Host "Source: $SourceDir" -ForegroundColor Cyan
Write-Host "Target: $TargetDir" -ForegroundColor Cyan
Write-Host ""

# Check source directory
if (-not (Test-Path $SourceDir)) {
    Write-Host "[ERROR] Source directory not found: $SourceDir" -ForegroundColor Red
    exit 1
}

# Clean deploy
if ($Clean -and (Test-Path $TargetDir)) {
    if (-not $Force) {
        $response = Read-Host "Delete existing Addin directory for clean deploy? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "[WARN] Deploy cancelled" -ForegroundColor Yellow
            exit 0
        }
    }

    Write-Host "[INFO] Removing existing directory..." -ForegroundColor Cyan
    Remove-Item -Path $TargetDir -Recurse -Force
    Write-Host "[OK] Removed" -ForegroundColor Green
}

# Create target directory
if (-not (Test-Path $TargetDir)) {
    Write-Host "[INFO] Creating target directory..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Write-Host "[OK] Created" -ForegroundColor Green
}

# Copy files
Write-Host "[INFO] Copying files..." -ForegroundColor Cyan

$ExcludePatterns = @("__pycache__", "*.pyc", "*.pyo", ".git*", "*.log")
$copiedCount = 0

Get-ChildItem -Path $SourceDir -Recurse | ForEach-Object {
    $skip = $false
    foreach ($pattern in $ExcludePatterns) {
        if ($_.Name -like $pattern -or $_.FullName -like "*\$pattern\*") {
            $skip = $true
            break
        }
    }

    if (-not $skip) {
        $relativePath = $_.FullName.Substring($SourceDir.Length)
        $targetPath = Join-Path $TargetDir $relativePath

        if ($_.PSIsContainer) {
            if (-not (Test-Path $targetPath)) {
                New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
            }
        } else {
            Copy-Item -Path $_.FullName -Destination $targetPath -Force
            $copiedCount++
        }
    }
}

Write-Host "[OK] Copied $copiedCount files" -ForegroundColor Green

# Clear Python cache
Write-Host "[INFO] Clearing Python cache..." -ForegroundColor Cyan
$cacheFiles = Get-ChildItem -Path $TargetDir -Recurse -Include "__pycache__", "*.pyc", "*.pyo" -ErrorAction SilentlyContinue
if ($cacheFiles) {
    $cacheFiles | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Removed $($cacheFiles.Count) cache files" -ForegroundColor Green
} else {
    Write-Host "[OK] No cache files" -ForegroundColor Green
}

# Done
Write-Host ""
Write-Host "[OK] Deploy completed" -ForegroundColor Green
Write-Host ""
Write-Host "[WARN] Please restart Fusion360 to reload the Addin" -ForegroundColor Yellow
Write-Host "Steps:" -ForegroundColor Cyan
Write-Host "  1. Launch Fusion360" -ForegroundColor Cyan
Write-Host "  2. Utilities > ADD-INS > Scripts and Add-Ins" -ForegroundColor Cyan
Write-Host "  3. Stop AIDX Addin (if running)" -ForegroundColor Cyan
Write-Host "  4. Start AIDX Addin" -ForegroundColor Cyan
Write-Host ""
