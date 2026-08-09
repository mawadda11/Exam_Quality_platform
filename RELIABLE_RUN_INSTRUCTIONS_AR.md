# تشغيل النسخة الجديدة على ويندوز

## 1) حمّلي ملف ZIP النهائي

ضعي ملف:

`Exam_Quality_RELIABLE_QUESTION_PREPARATION_20260805.zip`

داخل مجلد `Downloads`.

## 2) افتحي PowerShell جديدًا

الصقي الكتلة كاملة:

```powershell
Set-Location "$env:USERPROFILE\Downloads"

$oldCandidates = @(
    "$env:USERPROFILE\Downloads\Exam_Quality_FINAL_RUN\Exam_Quality_FINAL_20260804",
    "$env:USERPROFILE\Downloads\Exam_Quality_VISUAL_REVIEW_RUN\Exam_Quality_VISUAL_REVIEW_FIXED_20260804"
)
$oldProject = $oldCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

$newRoot = "$env:USERPROFILE\Downloads\Exam_Quality_RELIABLE_RUN"
$zip = Get-ChildItem "$env:USERPROFILE\Downloads\Exam_Quality_RELIABLE_QUESTION_PREPARATION_20260805*.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $zip) {
    throw "لم أجد ملف النسخة الجديدة داخل Downloads"
}

# إيقاف النسخة السابقة دون حذف قاعدة البيانات
if ($oldProject) {
    Set-Location $oldProject
    docker compose -p exam_quality_fixed down
}

Set-Location "$env:USERPROFILE\Downloads"

# الاحتفاظ بأي تركيب سابق من النسخة الجديدة
if (Test-Path $newRoot) {
    $backup = "${newRoot}_BACKUP_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Rename-Item $newRoot $backup
}

New-Item -ItemType Directory -Path $newRoot -Force | Out-Null
Expand-Archive -Path $zip.FullName -DestinationPath $newRoot -Force

$composeFile = Get-ChildItem $newRoot -Recurse -File |
    Where-Object {
        $_.Name -in @(
            "compose.yml",
            "compose.yaml",
            "docker-compose.yml",
            "docker-compose.yaml"
        )
    } |
    Select-Object -First 1

if (-not $composeFile) {
    throw "تم فك ZIP لكن لم يتم العثور على Docker Compose"
}

$newProject = $composeFile.Directory.FullName

# استعادة الإعدادات القديمة من دون وضعها داخل ZIP
if ($oldProject -and (Test-Path "$oldProject\.env")) {
    Copy-Item "$oldProject\.env" "$newProject\.env" -Force
}
elseif (-not (Test-Path "$newProject\.env")) {
    Copy-Item "$newProject\.env.example" "$newProject\.env" -Force
}

# استعادة ملفات الاختبارات القديمة عند وجودها
if ($oldProject -and (Test-Path "$oldProject\storage")) {
    New-Item -ItemType Directory -Path "$newProject\storage" -Force | Out-Null
    robocopy "$oldProject\storage" "$newProject\storage" /E /COPY:DAT /R:2 /W:1
    if ($LASTEXITCODE -ge 8) {
        throw "فشل نسخ storage. كود Robocopy: $LASTEXITCODE"
    }
}

Set-Location $newProject

docker compose -p exam_quality_fixed run --rm --build backend alembic upgrade head
docker compose -p exam_quality_fixed up --build -d
docker compose -p exam_quality_fixed ps

Start-Process "http://localhost:5173"
```

## 3) داخل الموقع

1. اضغطي `Ctrl + F5`.
2. أنشئي **تحليلًا جديدًا**؛ التحليلات القديمة تحتفظ بطريقة تجهيز الأسئلة القديمة.
3. ارفعي ملف الاختبار وملف TP-153 المطابق.
4. في خطوة **Review and Start** اختاري إحدى الطرق:
   - **Structured question template**: الموصى بها للعرض والنتائج الأكثر ثباتًا.
   - **Manual visual review from PDF**: للملفات غير المنتظمة.
   - **Assisted extraction from PDF**: اقتراح آلي يحتاج مراجعة دقيقة.
5. لا تدخلي درجة إلا إذا كانت ظاهرة في الاختبار.
6. راجعي الأسئلة ثم أكدي النسخة قبل تشغيل التحليل.

## 4) استخدام القالب المنظم

في شاشة Extraction Review:

1. اضغطي **Download CSV template**.
2. افتحي الملف في Excel.
3. أدخلي سؤالًا كاملًا في كل صف.
4. احفظيه بصيغة CSV.
5. اضغطي **Import completed CSV**.
6. قارني كل سؤال مع ملف PDF الأصلي قبل التأكيد.

## 5) Gemini

لا تحتاجين Gemini لتشغيل الطرق الثلاث. يظل استخراج Gemini معطلًا افتراضيًا. لا تضعي مفتاحًا حقيقيًا إلا عند قرار اختبار التحليل الدلالي لاحقًا.

## 6) إيقاف الموقع

```powershell
Set-Location "$env:USERPROFILE\Downloads\Exam_Quality_RELIABLE_RUN"
$composeFile = Get-ChildItem . -Recurse -File |
    Where-Object { $_.Name -in @("compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml") } |
    Select-Object -First 1
Set-Location $composeFile.Directory.FullName
docker compose -p exam_quality_fixed down
```
