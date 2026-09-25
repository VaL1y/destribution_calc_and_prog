param(
    [int]$Users = 100,
    [int]$SpawnRate = 50,
    [string]$Duration = "20s",
    [int[]]$Workers = @(1, 2, 4)
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Assert-LastExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

function Wait-ForApi {
    $containerId = docker compose ps -q api
    Assert-LastExitCode "Locate API container"

    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $health = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{end}}" $containerId
        if ($health -eq "healthy") {
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "API did not become healthy"
}

try {
    docker compose up --build -d
    Assert-LastExitCode "Start application"

    foreach ($workerCount in $Workers) {
        Write-Host "`n=== $workerCount API worker(s) ===" -ForegroundColor Cyan
        $env:API_WORKERS = [string]$workerCount

        docker compose up -d --force-recreate api
        Assert-LastExitCode "Recreate API with $workerCount workers"
        Wait-ForApi

        docker compose --profile load run --rm locust `
            -f /mnt/locust/locustfile.py `
            --host http://api:8000 `
            --headless `
            -u $Users `
            -r $SpawnRate `
            -t $Duration `
            --only-summary `
            --exit-code-on-error 0 `
            --csv "/results/workers-$workerCount" `
            ReadOnlyUser
        Assert-LastExitCode "Locust test with $workerCount workers"
    }
}
finally {
    $env:API_WORKERS = "2"
    docker compose up -d --force-recreate api
    Remove-Item Env:API_WORKERS -ErrorAction SilentlyContinue
}

Write-Host "`nCSV results: $projectRoot\load-results\workers-*_stats.csv" -ForegroundColor Green
