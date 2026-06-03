<#
.SYNOPSIS
  Start the Vite frontend for real local operation.

.DESCRIPTION
  Starts the frontend with VITE_API_PROXY_TARGET pointing to a backend URL.
  Optionally checks backend health and performs a frontend proxy login smoke test.

.EXAMPLE
  .\scripts\start_frontend_demo.ps1

.EXAMPLE
  .\scripts\start_frontend_demo.ps1 -BackendUrl http://127.0.0.1:5051 -FrontendPort 5189
#>
param(
    [Parameter(Mandatory = $false)]
    [string]$BackendUrl = "http://127.0.0.1:5051",

    [Parameter(Mandatory = $false)]
    [int]$FrontendPort = 5189,

    [Parameter(Mandatory = $false)]
    [switch]$SkipBackendCheck,

    [Parameter(Mandatory = $false)]
    [switch]$SkipProxySmoke
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-RestMethod -Uri $Url -TimeoutSec 5
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "Timed out waiting for $Url"
}

function Invoke-JsonPost {
    param(
        [string]$Url,
        [hashtable]$Body
    )

    $json = $Body | ConvertTo-Json -Depth 20 -Compress
    Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Body $json
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendRoot = Join-Path $repoRoot "frontend"
$frontendBaseUrl = "http://127.0.0.1:$FrontendPort"

if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "package.json"))) {
    throw "Cannot find frontend/package.json under $repoRoot"
}

Write-Step "Checking npm"
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) {
    throw "npm.cmd was not found. Install Node.js before starting the frontend."
}

if (-not $SkipBackendCheck) {
    Write-Step "Checking backend health: $BackendUrl/health"
    $health = Wait-HttpOk -Url "$BackendUrl/health" -TimeoutSeconds 60
    if ($health.status -ne "healthy") {
        throw "Unexpected backend health response from $BackendUrl/health"
    }
}

Write-Step "Starting or reusing Vite frontend on port $FrontendPort"
$frontendReady = $false
try {
    $page = Invoke-WebRequest -UseBasicParsing -Uri "$frontendBaseUrl/login" -TimeoutSec 5
    $frontendReady = $page.StatusCode -eq 200
} catch {
    $frontendReady = $false
}

if (-not $frontendReady) {
    $viteCommand = "`$env:VITE_API_PROXY_TARGET='$BackendUrl'; npm run dev -- --host 127.0.0.1 --port $FrontendPort"
    $process = Start-Process `
        -FilePath powershell.exe `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $viteCommand) `
        -WorkingDirectory $frontendRoot `
        -PassThru `
        -WindowStyle Hidden
    Write-Host "Started frontend process: $($process.Id)"
} else {
    Write-Host "Frontend already responds on $frontendBaseUrl; reusing it." -ForegroundColor Yellow
}

Wait-HttpOk -Url "$frontendBaseUrl/login" -TimeoutSeconds 120 | Out-Null

if (-not $SkipProxySmoke) {
    Write-Step "Running frontend proxy smoke check"
    $login = Invoke-JsonPost -Url "$frontendBaseUrl/api/v1/auth/login" -Body @{
        username = "api-login-user"
        password = "correct-pass"
    }
    $me = Invoke-RestMethod -Method Get -Uri "$frontendBaseUrl/api/v1/users/me" -Headers @{
        Authorization = "Bearer $($login.access_token)"
    }
    [ordered]@{
        frontend = $frontendBaseUrl
        backend_proxy_target = $BackendUrl
        frontend_proxy_user_id = $me.id
        frontend_proxy_username = $me.username
    } | ConvertTo-Json -Depth 20
}

Write-Host ""
Write-Host "Frontend demo is ready." -ForegroundColor Green
Write-Host "Frontend: $frontendBaseUrl"
Write-Host "Backend proxy target: $BackendUrl"
Write-Host "Student: api-login-user / correct-pass"
