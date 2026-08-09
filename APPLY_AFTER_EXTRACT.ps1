$ErrorActionPreference = "Stop"

$obsolete = @(
  "backend\app\services\translation",
  "backend\tests\test_local_translation.py",
  "CHANGELOG_20260808_LOCAL_ARABIC_TRANSLATION.md"
)

foreach ($path in $obsolete) {
  if (Test-Path $path) {
    Remove-Item $path -Recurse -Force
    Write-Host "Removed obsolete dynamic translation artifact: $path"
  }
}

Write-Host "Dynamic translation removal cleanup completed."
