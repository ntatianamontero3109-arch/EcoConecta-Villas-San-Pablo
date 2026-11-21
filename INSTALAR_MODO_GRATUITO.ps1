# EcoConecta 2.0.1 - actualización segura en modo gratuito
# Ejecutar desde la carpeta donde se extrajo este ZIP.
# No elimina contenedores, volúmenes, .env ni datos de PostgreSQL.
$ErrorActionPreference = 'Stop'

Write-Host "`nECOCONECTA 2.0.1 - ACTUALIZACION MODO GRATUITO" -ForegroundColor Cyan

if (!(Test-Path '.\app\main.py') -or !(Test-Path '.\docker-compose.yml')) {
    throw 'Extrae el ZIP completo y ejecuta este script desde la carpeta del proyecto.'
}
if (!(Test-Path '.\.env')) {
    throw 'No se encontró .env. Copia el .env de tu instalación actual; no crees uno nuevo con valores de ejemplo.'
}

Write-Host "`n1. Verificando que Docker esté disponible" -ForegroundColor Cyan
docker version --format '{{.Server.Version}}' | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Docker Engine no está disponible.' }

Write-Host "`n2. Validando Docker Compose" -ForegroundColor Cyan
docker compose -p ecoconecta config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose no es válido. No se modificó ningún contenedor.' }

Write-Host "`n3. Comprobando PostgreSQL existente" -ForegroundColor Cyan
docker exec ecoconecta-db-1 pg_isready -U ecoconecta -d ecoconecta
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL no está disponible. No se actualizará el servicio web.' }

Write-Host "`n4. Confirmando volúmenes existentes" -ForegroundColor Cyan
$expected = @('ecoconecta_postgres_data','ecoconecta_uploads_data')
$volumes = @(docker volume ls --format '{{.Name}}')
foreach ($v in $expected) {
    if ($volumes -notcontains $v) { throw "No se encontró el volumen esperado: $v. Deteniendo para evitar crear una base vacía." }
    Write-Host "$v : encontrado" -ForegroundColor Green
}

Write-Host "`n5. Reconstruyendo únicamente el servicio web" -ForegroundColor Cyan
docker compose -p ecoconecta up --build -d --no-deps web
if ($LASTEXITCODE -ne 0) { throw 'No se pudo actualizar el servicio web.' }

Write-Host "`n6. Esperando y comprobando la API" -ForegroundColor Cyan
$ok = $false
for ($i=0; $i -lt 20; $i++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://localhost:8000/api/health' -TimeoutSec 3
        if ($health.status -eq 'ok') { $ok = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (!$ok) {
    docker compose -p ecoconecta logs --tail=80 web
    throw 'La API no respondió correctamente. Los volúmenes y la base de datos no se eliminaron.'
}

Write-Host "`nACTUALIZACION COMPLETADA" -ForegroundColor Green
Write-Host 'Web: http://localhost:8000'
Write-Host 'API: http://localhost:8000/docs'
Write-Host 'Chatbot: EcoBot local gratuito'
Write-Host 'WhatsApp automático: desactivado; no se generan cargos.'
Write-Host "`nNo se ejecutó docker compose down ni docker volume rm." -ForegroundColor Green
