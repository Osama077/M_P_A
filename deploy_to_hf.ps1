# Match Performance Analysis — Deploy to Hugging Face Spaces
# Run this script from the project root directory

param(
    [Parameter(Mandatory=$false)]
    [string]$SpaceName = "match-performance-api",

    [Parameter(Mandatory=$false)]
    [string]$HFUsername
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Get-Location

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Match Performance API — HF Spaces Deploy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Prerequisites Check ──
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

# Check git
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Error "Git not found. Install from https://git-scm.com"
    exit 1
}
Write-Host "  ✓ git: $(& git --version)"

# Check git-lfs
$gitLfs = & git lfs version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git LFS not found. Install from https://git-lfs.com"
    exit 1
}
Write-Host "  ✓ git-lfs: $gitLfs"

# Check Python + huggingface_hub
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Error "Python not found"
    exit 1
}
$hfInstalled = & python -c "import huggingface_hub; print(huggingface_hub.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Installing huggingface_hub..." -ForegroundColor Yellow
    & python -m pip install huggingface_hub
}
Write-Host "  ✓ huggingface_hub: $(& python -c 'import huggingface_hub; print(huggingface_hub.__version__)')"

# ── Login ──
Write-Host ""
Write-Host "[2/5] Hugging Face login..." -ForegroundColor Yellow
Write-Host "  Go to https://huggingface.co/settings/tokens → create a token with 'write' access"
& huggingface-cli login

# ── Create Space ──
Write-Host ""
Write-Host "[3/5] Creating Hugging Face Space..." -ForegroundColor Yellow
$whoami = & huggingface-cli whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not logged in. Run 'huggingface-cli login' first."
    exit 1
}
$HFUsername = ($whoami | Select-Object -First 1).Trim()
Write-Host "  Logged in as: $HFUsername"

$existing = & huggingface-cli repo list --space 2>&1 | Select-String $SpaceName
if (-not $existing) {
    & huggingface-cli repo create $SpaceName --type space --sdk docker --yes
    Write-Host "  ✓ Space created: https://huggingface.co/spaces/$HFUsername/$SpaceName"
} else {
    Write-Host "  ✓ Space already exists"
}

$SpaceUrl = "https://huggingface.co/spaces/$HFUsername/$SpaceName"

# ── Clone Space & Copy Files ──
Write-Host ""
Write-Host "[4/5] Cloning Space repo and copying files..." -ForegroundColor Yellow

$tempDir = Join-Path $env:TEMP "hf-deploy-$SpaceName"
if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
& git clone "https://huggingface.co/spaces/$HFUsername/$SpaceName" $tempDir 2>&1 | Out-Null

# Initialize git-lfs in the space repo
Push-Location $tempDir
& git lfs install
Pop-Location

Write-Host "  Copying project files to $tempDir ..."

# Core source code
Copy-Item -Recurse (Join-Path $ProjectRoot "api") $tempDir -Force
Copy-Item -Recurse (Join-Path $ProjectRoot "pipeline") $tempDir -Force
Copy-Item -Recurse (Join-Path $ProjectRoot "utils") $tempDir -Force
Copy-Item -Recurse (Join-Path $ProjectRoot "visualizations") $tempDir -Force
Copy-Item (Join-Path $ProjectRoot "config.py") $tempDir -Force

# Data + models (include .gitattributes for LFS)
Copy-Item -Recurse (Join-Path $ProjectRoot "data") $tempDir -Force
Copy-Item -Recurse (Join-Path $ProjectRoot "models") $tempDir -Force

# Deployment files
Copy-Item (Join-Path $ProjectRoot "Dockerfile") $tempDir -Force
Copy-Item (Join-Path $ProjectRoot ".dockerignore") $tempDir -Force
Copy-Item (Join-Path $ProjectRoot "requirements.txt") $tempDir -Force
Copy-Item (Join-Path $ProjectRoot ".gitattributes") $tempDir -Force

# ── Commit & Push ──
Write-Host ""
Write-Host "[5/5] Pushing to Hugging Face Spaces..." -ForegroundColor Yellow

Push-Location $tempDir
& git add -A
& git status

$commitMsg = "Deploy Match Performance API v1.0.0"
& git commit -m $commitMsg

Write-Host "  Pushing (this may take a few minutes for large files)..." -ForegroundColor Yellow
& git push

Pop-Location

# Cleanup
Remove-Item -Recurse -Force $tempDir

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✓ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Your API is live at:" -ForegroundColor White
Write-Host "  $SpaceUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Docs (Swagger):" -ForegroundColor White
Write-Host "  $SpaceUrl/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  First request will be slow (~1-2 min cold start)." -ForegroundColor Yellow
Write-Host "  Keep it warm with a cron job hitting / every 12h." -ForegroundColor Yellow
