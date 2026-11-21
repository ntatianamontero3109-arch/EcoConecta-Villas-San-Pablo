# Pruebas de humo locales: API, frontend y EcoBot gratuito.
$ErrorActionPreference = 'Stop'
$base = 'http://localhost:8000'
$fallos = 0

function Test-Http($label, $url) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
        if ($r.StatusCode -eq 200) { Write-Host "OK  $label" -ForegroundColor Green }
        else { Write-Host "FAIL $label : HTTP $($r.StatusCode)" -ForegroundColor Red; $script:fallos++ }
    } catch { Write-Host "FAIL $label : $($_.Exception.Message)" -ForegroundColor Red; $script:fallos++ }
}

Write-Host "`nECOCONECTA - VERIFICACION LOCAL" -ForegroundColor Cyan
Test-Http 'Página principal' "$base/"
Test-Http 'CSS' "$base/static/styles.css"
Test-Http 'JavaScript' "$base/static/app.js"
Test-Http 'Documentación API' "$base/docs"

try {
    $health = Invoke-RestMethod "$base/api/health" -TimeoutSec 10
    if ($health.status -eq 'ok' -and $health.database -eq 'PostgreSQL') {
        Write-Host 'OK  API y PostgreSQL' -ForegroundColor Green
    } else { throw 'Respuesta inesperada de health' }
} catch { Write-Host "FAIL API y PostgreSQL : $($_.Exception.Message)" -ForegroundColor Red; $fallos++ }

$preguntas = @(
    @{q='¿Cómo puedo solicitar una recolección?'; esperado='solicitud'},
    @{q='¿Qué hago con botellas plásticas?'; esperado='plasticos'},
    @{q='¿Qué puedo hacer con pilas usadas?'; esperado='pilas'},
    @{q='¿Cómo consulto el estado de mi solicitud?'; esperado='seguimiento'},
    @{q='¿Cómo se acumulan los puntos?'; esperado='puntos'}
)

foreach ($item in $preguntas) {
    try {
        $payload = @{ messages = @(@{ role='user'; content=$item.q }) } | ConvertTo-Json -Depth 5 -Compress
        $body = [System.Text.Encoding]::UTF8.GetBytes($payload)
        $r = Invoke-RestMethod -Uri "$base/api/chat" -Method Post -ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec 15
        if ($r.answer -and $r.category -eq $item.esperado -and $r.mode -eq 'local_gratuito') {
            Write-Host "OK  EcoBot: $($item.esperado)" -ForegroundColor Green
        } else {
            Write-Host "FAIL EcoBot: $($item.q) -> $($r.category)" -ForegroundColor Red
            $fallos++
        }
    } catch { Write-Host "FAIL EcoBot: $($_.Exception.Message)" -ForegroundColor Red; $fallos++ }
}

Write-Host "`nRESULTADO: $fallos fallo(s)" -ForegroundColor Cyan
if ($fallos -gt 0) { throw 'Hay verificaciones pendientes. Revisa los registros del servicio web.' }
Write-Host 'PRUEBAS DE HUMO APROBADAS' -ForegroundColor Green
