# set_daocloud_mirror.ps1
# 配置 Docker Desktop 的 daocloud 镜像源，并触发「完整重启」所需的前置步骤。
# 用法（PowerShell 中执行）：  .\set_daocloud_mirror.ps1
# 适用：大陆 Windows + WSL2 + Docker Desktop，Docker Hub 直连被墙、pull 报
#       digest mismatch / short read / 超时 时。
# 说明：杀后端进程 + wsl --shutdown 后，需「手动」重启 Docker Desktop 才生效。

$mirror = "https://docker.m.daocloud.io"
$daemonDir = Join-Path $env:USERPROFILE ".docker"
$daemonPath = Join-Path $daemonDir "daemon.json"

# 1. 写 daemon.json（单源 daocloud）
$json = @{ "registry-mirrors" = @($mirror) } | ConvertTo-Json -Compress
New-Item -ItemType Directory -Force -Path $daemonDir | Out-Null
Set-Content -Path $daemonPath -Value $json -Encoding UTF8
Write-Host "[ok] 已写入 $daemonPath -> $mirror"

# 2. 杀 Docker Desktop 后端进程（丢弃 DD 缓存的旧镜像源状态）
$names = @("com.docker.backend", "vpnkit", "Docker Desktop")
foreach ($n in $names) {
    Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "[kill] $($_.Name) (pid $($_.Id))"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

# 3. 关闭 WSL（释放 dockerd 所在发行版）
Write-Host "[wsl] wsl --shutdown"
wsl --shutdown 2>&1 | Out-Null

Write-Host ""
Write-Host "================ 下一步（必须手动） ================"
Write-Host "1. 重新启动 Docker Desktop（开始菜单 / 任务栏图标）。"
Write-Host "2. 等待守护进程就绪（约 15 秒）。"
Write-Host "3. 验证配置是否生效："
Write-Host "     docker info | findstr /C:""docker.m.daocloud.io"""
Write-Host "     docker pull busybox"
Write-Host "   成功拿到有效 digest（如 sha256:...）即生效。"
Write-Host "====================================================="
