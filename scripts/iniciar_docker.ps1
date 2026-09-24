#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$EnvFile = "backend/.env",
    [string]$ProjectName = "poscosegran"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envPath = if ([IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $projectRoot $EnvFile }

function New-LocalSecret([int]$bytes) {
    $buffer = New-Object byte[] $bytes
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($buffer) } finally { $generator.Dispose() }
    return [Convert]::ToBase64String($buffer).Replace("+", "-").Replace("/", "_").TrimEnd("=")
}

if (-not (Test-Path -LiteralPath $envPath)) {
    $parent = Split-Path -Parent $envPath
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    $jwtSecret = New-LocalSecret 48
    $loginPassword = "testeo"
    $content = @"
POSCOSEGRAN_ENTORNO=local
POSCOSEGRAN_BD_URL_APP=postgresql+psycopg://poscosegran_app:local_app_2026@127.0.0.1:55432/poscosegran
POSCOSEGRAN_BD_URL_MIGRACIONES=postgresql+psycopg://poscosegran_migraciones:local_migraciones_2026@127.0.0.1:55432/poscosegran
POSCOSEGRAN_JWT_MODO=SECRETO_COMPARTIDO
POSCOSEGRAN_JWT_ALGORITMOS=HS256
POSCOSEGRAN_JWT_SECRETO=$jwtSecret
POSCOSEGRAN_JWT_EMISOR=http://localhost/auth/v1
POSCOSEGRAN_AUTH_LOCAL_HABILITADA=true
POSCOSEGRAN_AUTH_LOCAL_PASSWORD=$loginPassword
POSCOSEGRAN_CORS_ORIGENES=http://localhost:8443,http://127.0.0.1:8443
POSCOSEGRAN_LIMITE_PETICIONES_POR_MINUTO=1000
POSCOSEGRAN_LIMITE_PETICIONES_ESCRITURA_POR_MINUTO=300
"@
    [IO.File]::WriteAllText($envPath, $content, (New-Object Text.UTF8Encoding($false)))
    Write-Host "Configuracion local creada en $envPath"
}

Push-Location $projectRoot
try {
    & docker compose --project-name $ProjectName --env-file $envPath up -d --build
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose no pudo iniciar el stack." }
    & docker compose --project-name $ProjectName --env-file $envPath ps --all
    if ($LASTEXITCODE -ne 0) { throw "No se pudo consultar el estado del stack." }
} finally {
    Pop-Location
}

Write-Host "POSCOSEGRAN iniciandose en http://localhost:8080"
Write-Host "Acceso local de prueba: usuario testeo, contrasena testeo (perfil PRODUCTOR)."
