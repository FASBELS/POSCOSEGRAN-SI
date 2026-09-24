<#
.SYNOPSIS
    Reproduce en Windows los gates del workflow de integración continua.

.DESCRIPTION
    Ejecuta los mismos pasos que .github/workflows/ci.yml en el mismo orden y se
    detiene en el primer fallo, para que el error que se ve en local sea el que
    fallaría en CI.

    No contiene credenciales: las lee del entorno. Defina antes

        $env:POSCOSEGRAN_BD_URL_PRUEBAS = 'postgresql+psycopg://...'

    o pase -UrlBd. Sin base de datos, -SinBd salta los pasos que la necesitan;
    en ese modo el resultado NO equivale al del workflow y el script lo dice.

.EXAMPLE
    pwsh scripts/verificar.ps1
    pwsh scripts/verificar.ps1 -SinBd
    pwsh scripts/verificar.ps1 -SaltarE2E
#>
[CmdletBinding()]
param(
    [string]$UrlBd = $env:POSCOSEGRAN_BD_URL_PRUEBAS,
    [string]$UrlBdAplicacion = $env:POSCOSEGRAN_BD_URL_PRUEBAS_APP,
    [switch]$SinBd,
    [switch]$SaltarE2E
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz 'backend\.venv\Scripts\python.exe'
$fallos = @()
$omitidos = @()

function Paso {
    param([string]$Nombre, [scriptblock]$Accion)
    Write-Host ''
    Write-Host "== $Nombre" -ForegroundColor Cyan
    & $Accion
    if ($LASTEXITCODE -ne 0) {
        throw "Falló: $Nombre (código $LASTEXITCODE)"
    }
}

function PasoConBd {
    param([string]$Nombre, [scriptblock]$Accion)
    if ($SinBd) {
        Write-Host "-- $Nombre (omitido: sin base de datos)" -ForegroundColor DarkYellow
        $script:omitidos += $Nombre
        return
    }
    Paso $Nombre $Accion
}

if (-not (Test-Path $python)) {
    throw "No existe $python. Cree el entorno con: py -3.13 -m venv backend\.venv; backend\.venv\Scripts\python.exe -m pip install -e 'backend[dev]'"
}
if (-not $SinBd -and -not $UrlBd) {
    throw 'Defina POSCOSEGRAN_BD_URL_PRUEBAS o pase -UrlBd. Use -SinBd para una verificación parcial.'
}

# Que una prueba de integración se omita en silencio es el fallo que este script
# existe para impedir.
$env:POSCOSEGRAN_EXIGIR_BD = if ($SinBd) { '0' } else { '1' }
$env:POSCOSEGRAN_BD_URL_PRUEBAS = $UrlBd

try {
    Push-Location $raiz

    PasoConBd 'Carga idempotente de la base de conocimiento' {
        $env:POSCOSEGRAN_BD_URL_MIGRACIONES = $UrlBd
        Push-Location backend
        & $python -m poscosegran.conocimiento.cargar --activar
        if ($LASTEXITCODE -eq 0) { & $python -m poscosegran.conocimiento.cargar --activar }
        Pop-Location
    }

    Paso 'Ruff' { & $python -m ruff check backend/src backend/tests backend/scripts }

    Paso 'Mypy estricto' {
        Push-Location backend
        & $python -m mypy
        Pop-Location
    }

    PasoConBd 'Alembic check' {
        Push-Location backend
        & $python -m alembic check
        Pop-Location
    }

    Paso 'Pytest' {
        Push-Location backend
        & $python -m pytest -q -rs
        Pop-Location
    }

    if (-not $SinBd -and $UrlBdAplicacion) {
        Paso 'Privilegios de la credencial restringida' {
            $anterior = $env:POSCOSEGRAN_BD_URL_PRUEBAS
            $env:POSCOSEGRAN_BD_URL_PRUEBAS = $UrlBdAplicacion
            Push-Location backend
            & $python -m pytest -q tests/test_esquema_bd.py::test_la_credencial_de_aplicacion_no_puede_crear_tablas
            Pop-Location
            $env:POSCOSEGRAN_BD_URL_PRUEBAS = $anterior
        }
    } else {
        Write-Host '-- Privilegios de la credencial restringida (omitido: falta POSCOSEGRAN_BD_URL_PRUEBAS_APP)' -ForegroundColor DarkYellow
        $omitidos += 'Privilegios de la credencial restringida'
    }

    Paso 'Contrato generado' {
        & $python backend/scripts/exportar_contrato.py
        if ($LASTEXITCODE -eq 0) { pnpm api:types }
        if ($LASTEXITCODE -eq 0) { git diff --exit-code -- docs/openapi.json src/api/contrato.ts src/campos.json }
    }

    Paso 'Lint del frontend' { pnpm lint }
    Paso 'Build del frontend' { pnpm build }

    if ($SaltarE2E) {
        Write-Host '-- Playwright (omitido por -SaltarE2E)' -ForegroundColor DarkYellow
        $omitidos += 'Playwright'
    } else {
        Paso 'Playwright' { pnpm test:e2e }
    }
}
catch {
    $fallos += $_.Exception.Message
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
}

Write-Host ''
if ($fallos.Count -gt 0) {
    Write-Host 'VERIFICACIÓN FALLIDA' -ForegroundColor Red
    $fallos | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}
if ($omitidos.Count -gt 0) {
    Write-Host "VERIFICACIÓN PARCIAL: $($omitidos.Count) paso(s) omitido(s)" -ForegroundColor Yellow
    $omitidos | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    Write-Host 'Este resultado no equivale al del workflow.' -ForegroundColor Yellow
    exit 0
}
Write-Host 'VERIFICACIÓN COMPLETA: todos los gates pasan.' -ForegroundColor Green
exit 0
