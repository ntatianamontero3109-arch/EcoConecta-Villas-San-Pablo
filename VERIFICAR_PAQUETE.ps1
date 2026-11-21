$ErrorActionPreference = 'Stop'
Write-Host 'ECOCONECTA 2.0.1 - PRUEBAS LOCALES DEL CODIGO' -ForegroundColor Cyan
python -m compileall -q app scripts tests
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación Python.' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas unitarias.' }
Write-Host 'Pruebas locales del código completadas.' -ForegroundColor Green
Write-Host 'Estas pruebas no sustituyen pruebas de integración en la base real.' -ForegroundColor Yellow
