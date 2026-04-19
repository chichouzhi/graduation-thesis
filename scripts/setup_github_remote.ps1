<#
.SYNOPSIS
  在 GitHub 上创建空仓库并添加 origin、推送当前 main（需已执行 gh auth login）。

.EXAMPLE
  .\scripts\setup_github_remote.ps1
  .\scripts\setup_github_remote.ps1 -RepoName my-thesis -Visibility public
#>
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoName = "graduation-thesis",

    [Parameter(Mandatory = $false)]
    [ValidateSet("private", "public")]
    [string]$Visibility = "private"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

$gh = $null
foreach ($c in @("C:\Program Files\GitHub CLI\gh.exe", "C:\Program Files (x86)\GitHub CLI\gh.exe")) {
    if (Test-Path -LiteralPath $c) {
        $gh = $c
        break
    }
}
if (-not $gh) {
    $cmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($cmd) {
        $gh = $cmd.Source
    }
}
if (-not $gh) {
    throw "未找到 gh。请安装: winget install GitHub.cli"
}

Write-Host "Using gh: $gh"
& $gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "尚未登录 GitHub。请在本机终端执行（会打开浏览器）：" -ForegroundColor Yellow
    Write-Host "  & `"$gh`" auth login -h github.com -p https -w" -ForegroundColor Cyan
    exit 1
}

$null = git rev-parse --git-dir 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "当前目录不是 git 仓库：$repoRoot"
}

$hasOrigin = $false
git remote get-url origin 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $hasOrigin = $true
}

if ($hasOrigin) {
    Write-Host "已存在 remote origin，跳过创建：" -ForegroundColor Green
    git remote -v
    Write-Host "若只需推送：git push -u origin main"
    exit 0
}

$flag = if ($Visibility -eq "public") { "--public" } else { "--private" }
Write-Host "Creating GitHub repo '$RepoName' ($Visibility) and pushing..." -ForegroundColor Green
& $gh repo create $RepoName $flag --source . --remote origin --push
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "Done. Remote:" -ForegroundColor Green
git remote -v
