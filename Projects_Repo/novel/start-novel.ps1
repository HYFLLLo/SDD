param(
    [switch]$Rebuild,
    [switch]$SkipMigration,
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot 'backend'
$FrontendDir = Join-Path $ProjectRoot 'frontend'

$JavaHome = 'D:\tools\jdk21\jdk-21.0.12.1+1'
$JavaExe = Join-Path $JavaHome 'bin\java.exe'
$MavenLocalRepo = 'D:/tools/infra/m2-repo'

$MySqlDir = 'E:\mysql\mysql-8.0.28-winx64'
$MySqlExe = Join-Path $MySqlDir 'bin\mysqld.exe'
$MySqlCli = Join-Path $MySqlDir 'bin\mysql.exe'
$MySqlIni = Join-Path $MySqlDir 'my.ini'
$MySqlHost = '127.0.0.1'
$MySqlPort = 3306
$DbName = 'novel'

$RedisDir = 'E:\redis'
$RedisExe = Join-Path $RedisDir 'redis-server.exe'
$RedisConf = 'redis.windows.conf'
$RedisPort = 6379

$BackendPort = 8888
$FrontendPort = 1024

$JarName = 'novel-3.5.1-SNAPSHOT.jar'
$JarPath = Join-Path $BackendDir "target\$JarName"

$ApplicationYml = Join-Path $BackendDir 'src\main\resources\application.yml'
$MigrationSql = Join-Path $BackendDir 'doc\sql\uploader_id_2026-10-20.sql'

function Write-Step {
    param([string]$Message)
    Write-Host "[start-novel] $Message"
}

function Test-TcpPort {
    param([int]$Port)
    $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-TcpPort {
    param(
        [int]$Port,
        [string]$Name,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPort -Port $Port) {
            Write-Step "$Name is listening on port $Port."
            return $true
        }
        Start-Sleep -Seconds 1
    }

    Write-Error "$Name did not start on port $Port within $TimeoutSeconds seconds."
    return $false
}

function Invoke-BackendBuild {
    Write-Step 'Building backend package...'
    $env:JAVA_HOME = $JavaHome
    $env:MAVEN_OPTS = "-Dmaven.repo.local=$MavenLocalRepo"

    Push-Location $BackendDir
    try {
        & (Join-Path $BackendDir 'mvnw.cmd') '-DskipTests' 'package'
        if ($LASTEXITCODE -ne 0) {
            throw 'Backend package build failed.'
        }
    }
    finally {
        Pop-Location
    }
}

function Get-DatasourceCredential {
    $yml = Get-Content -Raw -Encoding UTF8 -LiteralPath $ApplicationYml
    $username = [regex]::Match($yml, '(?m)^\s*username:\s*(.+?)\s*$').Groups[1].Value.Trim()
    $password = [regex]::Match($yml, '(?m)^\s*password:\s*(.+?)\s*$').Groups[1].Value.Trim()

    if ([string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrWhiteSpace($password)) {
        throw 'Could not parse database username or password from application.yml.'
    }

    [PSCustomObject]@{
        Username = $username
        Password = $password
    }
}

function Invoke-Mysql {
    param(
        [string]$Sql,
        [string]$AdditionalArgs = ''
    )

    $credential = Get-DatasourceCredential
    $env:MYSQL_PWD = $credential.Password
    $username = $credential.Username

    try {
        if ($AdditionalArgs) {
            & $MySqlCli --host=$MySqlHost --port=$MySqlPort --user=$username --database=$DbName $AdditionalArgs.Split(' ') --execute $Sql
        }
        else {
            & $MySqlCli --host=$MySqlHost --port=$MySqlPort --user=$username --database=$DbName --execute $Sql
        }
        if ($LASTEXITCODE -ne 0) {
            throw 'mysql command failed.'
        }
    }
    finally {
        Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
    }
}

function Ensure-DatabaseSchema {
    if ($SkipMigration) {
        Write-Step 'Skipping database migration check as requested.'
        return
    }

    if (-not (Test-TcpPort -Port $MySqlPort)) {
        throw 'MySQL is not running; cannot run the database migration check.'
    }

    Write-Step 'Checking/applying novel database migration...'
    $sql = Get-Content -Raw -Encoding UTF8 -LiteralPath $MigrationSql
    Invoke-Mysql -Sql $sql
}

function Start-Mysql {
    if (Test-TcpPort -Port $MySqlPort) {
        Write-Step "MySQL is already listening on port $MySqlPort."
        return
    }

    Write-Step 'Starting MySQL...'
    Start-Process -FilePath $MySqlExe `
        -ArgumentList "--defaults-file=$MySqlIni" `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $MySqlDir 'mysql-start.out') `
        -RedirectStandardError (Join-Path $MySqlDir 'mysql-start.err')

    if (-not (Wait-TcpPort -Port $MySqlPort -Name 'MySQL' -TimeoutSeconds $TimeoutSeconds)) {
        exit 1
    }
}

function Start-Redis {
    if (Test-TcpPort -Port $RedisPort) {
        Write-Step "Redis is already listening on port $RedisPort."
        return
    }

    Write-Step 'Starting Redis...'
    Start-Process -FilePath $RedisExe `
        -ArgumentList $RedisConf `
        -WorkingDirectory $RedisDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $RedisDir 'redis-start.out') `
        -RedirectStandardError (Join-Path $RedisDir 'redis-start.err')

    if (-not (Wait-TcpPort -Port $RedisPort -Name 'Redis' -TimeoutSeconds $TimeoutSeconds)) {
        exit 1
    }
}

function Start-Backend {
    if (Test-TcpPort -Port $BackendPort) {
        Write-Step "Backend is already listening on port $BackendPort."
        return
    }

    if ($Rebuild -or -not (Test-Path -LiteralPath $JarPath)) {
        Invoke-BackendBuild
    }

    if (-not (Test-Path -LiteralPath $JarPath)) {
        throw "Backend jar not found: $JarPath"
    }

    Write-Step 'Starting backend...'
    $env:JAVA_HOME = $JavaHome
    Start-Process -FilePath $JavaExe `
        -ArgumentList '-jar', "target\$JarName" `
        -WorkingDirectory $BackendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $BackendDir 'novel-run.log') `
        -RedirectStandardError (Join-Path $BackendDir 'novel-run.err.log')

    if (-not (Wait-TcpPort -Port $BackendPort -Name 'Backend' -TimeoutSeconds $TimeoutSeconds)) {
        exit 1
    }

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://${MySqlHost}:$BackendPort/api/front/home/books" -TimeoutSec 15
        if ($response.StatusCode -ne 200 -or $response.Content -notmatch '"code":"00000"') {
            Write-Warning 'Backend is listening, but the home books API did not return code 00000.'
        }
        else {
            Write-Step 'Backend home books API check passed.'
        }
    }
    catch {
        Write-Warning "Backend API check failed: $($_.Exception.Message)"
    }
}

function Start-Frontend {
    if (Test-TcpPort -Port $FrontendPort) {
        Write-Step "Frontend is already listening on port $FrontendPort."
        return
    }

    Write-Step 'Starting frontend...'
    Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', 'npm.cmd run serve' `
        -WorkingDirectory $FrontendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $FrontendDir 'frontend-run.log') `
        -RedirectStandardError (Join-Path $FrontendDir 'frontend-run.err.log')

    if (-not (Wait-TcpPort -Port $FrontendPort -Name 'Frontend' -TimeoutSeconds $TimeoutSeconds)) {
        exit 1
    }

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$FrontendPort/" -TimeoutSec 15
        if ($response.StatusCode -ne 200) {
            Write-Warning 'Frontend is listening, but did not return HTTP 200.'
        }
        else {
            Write-Step 'Frontend HTTP check passed.'
        }
    }
    catch {
        Write-Warning "Frontend HTTP check failed: $($_.Exception.Message)"
    }
}

Write-Step 'novel startup started.'
Write-Step 'No seed SQL import will be performed; existing MySQL data is preserved.'
Start-Mysql
Start-Redis
Ensure-DatabaseSchema
Start-Backend
Start-Frontend

Write-Step 'novel startup finished.'
Write-Host "Frontend: http://localhost:$FrontendPort/"
Write-Host "Backend:  http://${MySqlHost}:$BackendPort"
Write-Host "MySQL:    port $MySqlPort"
Write-Host "Redis:    port $RedisPort"



