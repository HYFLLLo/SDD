<#
.SYNOPSIS
  字节码对拍检查：只有 app/ 有改动时才需要跑（用 Python 3.8）。

.DESCRIPTION
  对拍要求 Python 3.8：_src/_pyc/*.pyc 是 3.8 字节码，3.11+ 的 marshal
  格式不兼容，读了会直接报 bad marshal data。

  默认行为：
    - app/ 与 _src/ 均无改动 -> 跳过（打印原因），退出码 0
    - 否则用 3.8 跑 verify_bytecode.py，并比对 total 是否退化

.PARAMETER Force
  即使 app/ 没改也强制跑一次。

.PARAMETER Python38
  3.8 解释器路径。默认从 py -3.8 或常见安装目录探测。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\audit\check_bytecode.ps1
#>
param(
  [switch]$Force,
  [string]$Python38 = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

function Find-Python38 {
  param([string]$Explicit)
  if ($Explicit -and (Test-Path -LiteralPath $Explicit)) { return $Explicit }
  $launcher = Join-Path $env:LOCALAPPDATA "Programs\Python\Launcher\py.exe"
  if (Test-Path -LiteralPath $launcher) {
    $found = & $launcher -3.8 -c "import sys;print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $found) { return $found.Trim() }
  }
  $candidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python38\python.exe"),
    "C:\Program Files\Python38\python.exe",
    "D:\Program Files\Python38\python.exe"
  )
  foreach ($c in $candidates) { if (Test-Path -LiteralPath $c) { return $c } }
  return ""
}

if (-not $Force) {
  $changed = git status --porcelain -- app _src
  if (-not $changed) {
    Write-Host "[skip] app/ 与 _src/ 无改动，字节码对拍无需重跑。" -ForegroundColor DarkGray
    Write-Host "       想强制跑一次：加 -Force" -ForegroundColor DarkGray
    exit 0
  }
  Write-Host "[run ] 检测到后端改动：" -ForegroundColor Yellow
  $changed | ForEach-Object { Write-Host "       $_" -ForegroundColor Yellow }
}

$py = Find-Python38
if (-not $py) {
  Write-Host "[fail] 找不到 Python 3.8。" -ForegroundColor Red
  Write-Host "       安装到：$env:LOCALAPPDATA\Programs\Python\Python38" -ForegroundColor Red
  Write-Host "       或用 -Python38 PATH 指定。" -ForegroundColor Red
  exit 2
}

$ver = & $py -c "import sys;print('%d.%d' % sys.version_info[:2])"
if ($ver -ne "3.8") {
  Write-Host "[fail] 指定的解释器是 Python $ver，对拍必须用 3.8（pyc 是 3.8 字节码）。" -ForegroundColor Red
  exit 2
}
Write-Host "[info] 使用 $py (Python $ver)" -ForegroundColor DarkGray

$before = if (Test-Path "tools\recover\bytecode_match.json") {
  (Get-Content "tools\recover\bytecode_match.json" -Raw -Encoding UTF8 | ConvertFrom-Json).totals
} else { $null }

$out = & $py tools\recover\verify_bytecode.py 2>&1
$out | Select-Object -Last 3 | ForEach-Object { Write-Host $_ }

$after = (Get-Content "tools\recover\bytecode_match.json" -Raw -Encoding UTF8 | ConvertFrom-Json).totals
$failed = $false
if ($after.missing -ne 0) {
  Write-Host "[fail] missing=$($after.missing)，有函数在源码里找不到。" -ForegroundColor Red
  $failed = $true
}
if ($before -and $after.diff -gt $before.diff) {
  Write-Host "[fail] diff 从 $($before.diff) 涨到 $($after.diff)。" -ForegroundColor Red
  $failed = $true
}
if ($before -and $after.exact -lt $before.exact) {
  Write-Host "[fail] exact 从 $($before.exact) 降到 $($after.exact)。" -ForegroundColor Red
  $failed = $true
}

# 对拍会重写 bytecode_match.json；数字没变就把文件还原，避免无意义 diff
git checkout -- tools/recover/bytecode_match.json 2>$null

if ($failed) { exit 1 }
Write-Host "[ ok ] exact $($after.exact) / near $($after.near) / diff $($after.diff) / missing $($after.missing)" -ForegroundColor Green
exit 0
