param(
    [switch]$Force,
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'

# 统一控制台编码，避免中文输出在 cmd / 管道下乱码
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
}
catch {
    # 某些宿主（如重定向到不支持 UTF-8 的终端）会失败，忽略即可
}

$ProjectRoot = $PSScriptRoot
$ApplicationYml = Join-Path $ProjectRoot 'backend\src\main\resources\application.yml'

$MySqlDir = 'E:\mysql\mysql-8.0.28-winx64'
$MySqlAdmin = Join-Path $MySqlDir 'bin\mysqladmin.exe'
$MySqlHost = '127.0.0.1'
$MySqlPort = 3306

$RedisDir = 'E:\redis'
$RedisCli = Join-Path $RedisDir 'redis-cli.exe'
$RedisPort = 6379

$BackendPort = 8888
$FrontendPort = 1024

function Write-Step {
    param([string]$Message)
    Write-Host "[stop-novel] $Message"
}

function Write-Warn-Step {
    param([string]$Message)
    Write-Host "[stop-novel] $Message" -ForegroundColor Yellow
}

function Write-Ok-Step {
    param([string]$Message)
    Write-Host "[stop-novel] $Message" -ForegroundColor Green
}

function Get-ListenerPid {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $conn) { return $null }
    return [int]$conn.OwningProcess
}

function Test-TcpPort {
    param([int]$Port)
    $null -ne (Get-ListenerPid -Port $Port)
}

function Wait-PortFree {
    param([int]$Port, [int]$TimeoutSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Test-TcpPort -Port $Port)) { return $true }
        Start-Sleep -Milliseconds 300
    }
    return -not (Test-TcpPort -Port $Port)
}

function Get-ProcessNameById {
    param([int]$TargetPid)
    $proc = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
    if ($null -eq $proc) { return $null }
    return $proc.ProcessName
}

function Stop-ProcessTree {
    param([int]$TargetPid)
    & taskkill.exe /PID $TargetPid /T /F 2>&1 | Out-Null
}

function Get-DatasourceCredential {
    if (-not (Test-Path -LiteralPath $ApplicationYml)) { return $null }

    $yml = Get-Content -Raw -Encoding UTF8 -LiteralPath $ApplicationYml
    $username = [regex]::Match($yml, '(?m)^\s*username:\s*(.+?)\s*$').Groups[1].Value.Trim()
    $password = [regex]::Match($yml, '(?m)^\s*password:\s*(.+?)\s*$').Groups[1].Value.Trim()

    if ([string]::IsNullOrWhiteSpace($username)) { return $null }

    [PSCustomObject]@{
        Username = $username
        Password = $password
    }
}

function Stop-Frontend {
    $targetPid = Get-ListenerPid -Port $FrontendPort
    if ($null -eq $targetPid) {
        Write-Step "端口 $FrontendPort（前端）已是空闲状态。"
        return $true
    }

    $name = Get-ProcessNameById -TargetPid $targetPid
    if (-not $Force -and $name -notmatch '^(node|npm|npx|cmd)$') {
        Write-Warn-Step "端口 $FrontendPort 被 '$name'（PID $targetPid）占用，看起来不是 novel 前端，已跳过。确认要关闭请加 -Force。"
        return $false
    }

    Write-Step "正在关闭前端（$name，PID $targetPid）..."
    Stop-ProcessTree -TargetPid $targetPid

    $frontendDir = Join-Path $ProjectRoot 'frontend'
    Get-CimInstance Win32_Process -Filter "Name='node.exe' OR Name='cmd.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessId -ne $targetPid -and
            $_.CommandLine -and
            $_.CommandLine -like "*$frontendDir*" -and
            ($_.CommandLine -match 'vue-cli-service' -or ($_.CommandLine -match 'npm' -and $_.CommandLine -match 'serve'))
        } |
        ForEach-Object { Stop-ProcessTree -TargetPid $_.ProcessId }

    if (Wait-PortFree -Port $FrontendPort -TimeoutSeconds $TimeoutSeconds) {
        Write-Ok-Step "前端已关闭，端口 $FrontendPort 已释放。"
        return $true
    }
    Write-Warn-Step "前端进程已发出关闭指令，但端口 $FrontendPort 在 $TimeoutSeconds 秒内仍未释放。"
    return $false
}

function Stop-Backend {
    $targetPid = Get-ListenerPid -Port $BackendPort
    if ($null -eq $targetPid) {
        Write-Step "端口 $BackendPort（后端）已是空闲状态。"
        return $true
    }

    $name = Get-ProcessNameById -TargetPid $targetPid
    if (-not $Force -and $name -notmatch '^(java|javaw)$') {
        Write-Warn-Step "端口 $BackendPort 被 '$name'（PID $targetPid）占用，看起来不是 novel 后端，已跳过。确认要关闭请加 -Force。"
        return $false
    }

    Write-Step "正在关闭后端（$name，PID $targetPid）..."
    Stop-ProcessTree -TargetPid $targetPid

    if (Wait-PortFree -Port $BackendPort -TimeoutSeconds $TimeoutSeconds) {
        Write-Ok-Step "后端已关闭，端口 $BackendPort 已释放。"
        return $true
    }
    Write-Warn-Step "后端端口 $BackendPort 在 $TimeoutSeconds 秒内仍未释放。"
    return $false
}

function Stop-Redis {
    $targetPid = Get-ListenerPid -Port $RedisPort
    if ($null -eq $targetPid) {
        Write-Step "端口 $RedisPort（Redis）已是空闲状态。"
        return $true
    }

    $name = Get-ProcessNameById -TargetPid $targetPid
    if (-not $Force -and $name -notmatch '^redis-server') {
        Write-Warn-Step "端口 $RedisPort 被 '$name'（PID $targetPid）占用，看起来不是项目 Redis，已跳过。确认要关闭请加 -Force。"
        return $false
    }

    if (Test-Path -LiteralPath $RedisCli) {
        Write-Step '正在通过 redis-cli 优雅关闭 Redis（会按配置落盘）...'
        try {
            & $RedisCli -p $RedisPort shutdown 2>&1 | Out-Null
        }
        catch {
            Write-Warn-Step "redis-cli shutdown 失败：$($_.Exception.Message)"
        }

        if (Wait-PortFree -Port $RedisPort -TimeoutSeconds 10) {
            Write-Ok-Step "Redis 已优雅关闭，端口 $RedisPort 已释放。"
            return $true
        }
        Write-Warn-Step 'Redis 未在优雅关闭后退出，改为强制结束进程。'
    }

    Write-Step "正在强制关闭 Redis（PID $targetPid）..."
    Stop-ProcessTree -TargetPid $targetPid

    if (Wait-PortFree -Port $RedisPort -TimeoutSeconds $TimeoutSeconds) {
        Write-Ok-Step "Redis 已关闭，端口 $RedisPort 已释放。"
        return $true
    }
    Write-Warn-Step "Redis 端口 $RedisPort 在 $TimeoutSeconds 秒内仍未释放。"
    return $false
}

function Stop-Mysql {
    $targetPid = Get-ListenerPid -Port $MySqlPort
    if ($null -eq $targetPid) {
        Write-Step "端口 $MySqlPort（MySQL）已是空闲状态。"
        return $true
    }

    $name = Get-ProcessNameById -TargetPid $targetPid
    if (-not $Force -and $name -notmatch '^mysqld') {
        Write-Warn-Step "端口 $MySqlPort 被 '$name'（PID $targetPid）占用，看起来不是 MySQL，已跳过。确认要关闭请加 -Force。"
        return $false
    }

    $credential = Get-DatasourceCredential
    if ($null -ne $credential -and (Test-Path -LiteralPath $MySqlAdmin)) {
        Write-Step '正在通过 mysqladmin 优雅关闭 MySQL（InnoDB 正常落盘）...'
        $env:MYSQL_PWD = $credential.Password
        try {
            & $MySqlAdmin "--host=$MySqlHost" "--port=$MySqlPort" "--user=$($credential.Username)" '--connect-timeout=5' 'shutdown' 2>&1 | Out-Null
            $adminExit = $LASTEXITCODE
        }
        catch {
            $adminExit = 1
            Write-Warn-Step "mysqladmin shutdown 失败：$($_.Exception.Message)"
        }
        finally {
            Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
        }

        if ($adminExit -eq 0 -and (Wait-PortFree -Port $MySqlPort -TimeoutSeconds 30)) {
            Write-Ok-Step "MySQL 已优雅关闭，端口 $MySqlPort 已释放。"
            return $true
        }
        Write-Warn-Step "MySQL 优雅关闭未成功（mysqladmin 退出码 $adminExit），改为强制结束进程。"
    }
    else {
        Write-Warn-Step '未取到数据库账号或缺少 mysqladmin，跳过优雅关闭，直接强制结束进程。'
    }

    Write-Step "正在强制关闭 MySQL（PID $targetPid）..."
    Stop-ProcessTree -TargetPid $targetPid

    if (Wait-PortFree -Port $MySqlPort -TimeoutSeconds $TimeoutSeconds) {
        Write-Ok-Step "MySQL 已关闭，端口 $MySqlPort 已释放。"
        return $true
    }
    Write-Warn-Step "MySQL 端口 $MySqlPort 在 $TimeoutSeconds 秒内仍未释放。"
    return $false
}

Write-Step 'novel shutdown started.（按启动的逆序关闭：前端 -> 后端 -> Redis -> MySQL）'

$results = @()
$results += [PSCustomObject]@{ Name = 'Frontend'; Port = $FrontendPort; Ok = (Stop-Frontend) }
$results += [PSCustomObject]@{ Name = 'Backend'; Port = $BackendPort; Ok = (Stop-Backend) }
$results += [PSCustomObject]@{ Name = 'Redis'; Port = $RedisPort; Ok = (Stop-Redis) }
$results += [PSCustomObject]@{ Name = 'MySQL'; Port = $MySqlPort; Ok = (Stop-Mysql) }

Write-Host ''
Write-Host '关闭结果：'
foreach ($item in $results) {
    $state = if ($item.Ok) { 'RELEASED' } else { 'STILL LISTENING' }
    Write-Host ("  {0,-10} port {1,-6} {2}" -f $item.Name, $item.Port, $state)
}

$failed = $results | Where-Object { -not $_.Ok }
if ($failed) {
    Write-Host ''
    Write-Warn-Step '部分端口未能释放，请检查上方告警。'
    exit 1
}

Write-Host ''
Write-Step 'novel shutdown finished. 四个端口均已释放。'
exit 0
