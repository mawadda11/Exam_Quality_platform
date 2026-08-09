$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker غير مثبت أو غير متاح في PATH."
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env" -Force
        Write-Host "تم إنشاء .env من .env.example" -ForegroundColor Yellow
    }
    else {
        throw "لم أجد .env أو .env.example"
    }
}

Write-Host "تشغيل قاعدة البيانات والخدمات المساندة..." -ForegroundColor Cyan
docker compose -p exam_quality_fixed up -d postgres chromadb
if ($LASTEXITCODE -ne 0) { throw "فشل تشغيل الخدمات المساندة." }

Write-Host "تطبيق ترحيلات قاعدة البيانات الموجودة..." -ForegroundColor Cyan
docker compose -p exam_quality_fixed run --rm --build backend alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "فشل تحديث قاعدة البيانات." }

Write-Host "بناء وتشغيل الموقع..." -ForegroundColor Cyan
docker compose -p exam_quality_fixed up --build -d
if ($LASTEXITCODE -ne 0) { throw "فشل تشغيل الموقع." }

Start-Sleep -Seconds 20

docker compose -p exam_quality_fixed ps

try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 20
    $health | ConvertTo-Json
    Write-Host "Backend يعمل بنجاح." -ForegroundColor Green
    Start-Process "http://localhost:5173"
}
catch {
    Write-Host "لم ينجح اختبار Backend. آخر السجلات:" -ForegroundColor Red
    docker compose -p exam_quality_fixed logs --tail=150 backend
    throw
}
