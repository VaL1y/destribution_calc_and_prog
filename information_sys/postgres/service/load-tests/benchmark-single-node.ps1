param(
    [string]$Duration = "15s",
    [int]$SpawnRate = 50,
    [int[]]$ReadUsers = @(25, 50, 100, 200),
    [int[]]$WriteUsers = @(5, 10, 20, 40),
    [string]$DatabaseCompose = "../tier_1/compose.yml",
    [string]$DatabaseService = "pg-1"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Assert-ExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

function Wait-ForApi {
    $containerId = docker compose ps -q api
    Assert-ExitCode "Locate API container"

    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $health = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{end}}" $containerId
        if ($health -eq "healthy") {
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "API did not become healthy"
}

function Reset-TestData {
    docker compose -f $DatabaseCompose exec -T $DatabaseService psql -U warehouse -d warehouse -v ON_ERROR_STOP=1 `
        -c "DELETE FROM warehouse.products WHERE sku LIKE 'LOAD-%';"
    Assert-ExitCode "Delete load-test data"

    docker compose -f $DatabaseCompose exec -T $DatabaseService psql -U warehouse -d warehouse -v ON_ERROR_STOP=1 `
        -c "VACUUM (ANALYZE) warehouse.products, warehouse.stock_movements;"
    Assert-ExitCode "Vacuum load-test data"
}

function Run-LocustTest([string]$Scenario, [int]$Users, [string]$Label) {
    Write-Host "`n=== ${Label}: $Users users ===" -ForegroundColor Cyan
    Reset-TestData
    docker compose up -d --force-recreate api
    Assert-ExitCode "Restart API before $Label test"
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
        --csv "/results/single-node-$Label-$Users" `
        $Scenario
    Assert-ExitCode "$Label test with $Users users"
    Start-Sleep -Seconds 2
}

docker compose -f $DatabaseCompose up -d
Assert-ExitCode "Start database"
docker compose build
docker compose --profile tools run --rm migrate
Assert-ExitCode "Apply migrations"
docker compose up -d api
Assert-ExitCode "Start application"

foreach ($users in $ReadUsers) {
    Run-LocustTest "ReadOnlyUser" $users "read"
}

foreach ($users in $WriteUsers) {
    Run-LocustTest "ParallelProductWriter" $users "write"
}

Reset-TestData
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
$summary = @()
foreach ($test in @(
    $ReadUsers | ForEach-Object { [pscustomobject]@{ Label = "read"; Users = $_ } }
    $WriteUsers | ForEach-Object { [pscustomobject]@{ Label = "write"; Users = $_ } }
)) {
    $csvPath = Join-Path $projectRoot "load-results\single-node-$($test.Label)-$($test.Users)_stats.csv"
    $aggregate = Import-Csv -LiteralPath $csvPath | Where-Object Name -eq "Aggregated"
    $summary += [pscustomobject]@{
        Scenario = $test.Label
        Users = $test.Users
        RPS = [math]::Round([double]::Parse($aggregate."Requests/s", [Globalization.CultureInfo]::InvariantCulture), 1)
        AvgMs = [math]::Round([double]::Parse($aggregate."Average Response Time", [Globalization.CultureInfo]::InvariantCulture), 0)
        P95Ms = [int]$aggregate."95%"
        Failures = [int]$aggregate."Failure Count"
    }
}
$summary | Format-Table -AutoSize
Write-Host "`nCSV results: $projectRoot\load-results\single-node-*_stats.csv" -ForegroundColor Green
