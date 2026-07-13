---
name: docker-local-deploy-cn
description: This skill should be used when deploying ANY service locally via Docker Compose on a mainland-China Windows + WSL2 + Docker Desktop machine, or diagnosing related failures — e.g. `docker pull` errors like "unexpected commit digest / failed precondition", "short read: expected N bytes but got N-1", or Docker Hub timeouts; Docker daemon not running / config changes not taking effect; or verifying a freshly deployed containerized service's web console. It provides the verified daocloud mirror fix, the full-restart procedure for Docker Desktop, and the correct localhost verification method (`curl.exe 127.0.0.1`). Applies to any project (Dify, Nextcloud, GitLab, WordPress, etc.); Dify-specific steps live under `examples/dify/`.
agent_created: true
---

# 大陆 Windows + WSL2 + Docker Desktop 本地部署（通用）

## Overview

在大陆网络环境下，于 Windows + WSL2 + Docker Desktop 通过 Docker Compose 本地部署**任意服务**。本技能固化了从镜像源修复、部署文件获取、容器启动到首次访问验证的通用流程，并精确给出几类高频坑的解法，避免重复踩雷。具体项目（如 Dify）的专属步骤见 `examples/` 子目录。

## 适用环境假设

- Windows 10/11，Docker Desktop 已安装，WSL2 后端
- 部署目录含官方 `docker-compose.yaml` + `.env`（及项目所需的挂载卷）
- 网络位于中国大陆，Docker Hub 直连被墙

## 工作流

### 阶段 0：确认 Docker 守护进程在线

- 使用 **PowerShell**（真实 Windows 进程，可连主机 daemon）执行 `docker ps`。
- 若守护进程未运行：用 PowerShell `Start-Process` 拉起 Docker Desktop，等待约 15 秒就绪。
- 环境注意：WorkBuddy 的 Bash 沙箱对带网络访问的命令（`git clone` / `docker pull`）会套覆盖层，命令结束后写入被丢弃；但 **docker 守护进程位于主机 WSL 卷，持久**。排障与拉取优先用 PowerShell 直跑。

### 阶段 1：修复镜像源（最关键，先做）

症状：`docker pull` 报 `unexpected commit digest ... failed precondition`，或 `short read: expected N bytes but got N-1`（镜像层被精确破坏 1 字节），或 Docker Hub 直连超时 `dial tcp ... failed to respond`。

根因：Docker Hub 在大陆直连被墙；Docker Desktop 按本机区域自动注入的镜像源（如 hpcloud 返回损坏层 / aliyun 个人源 403 / ustc DNS 死）常常全部失效。

解法：配置 daocloud 单源。运行 `scripts/set_daocloud_mirror.ps1`（写入 daemon.json + 杀后端进程 + `wsl --shutdown`），随后**手动重启 Docker Desktop**，再用 `docker pull busybox` 验证。

- 验证通过标志：拿到有效 digest（如 `sha256:fd8d9aa...`），且 `docker info` 的 Registry Mirrors 显示 `https://docker.m.daocloud.io/`。
- 注意：Docker Desktop 会按区域动态把镜像源注入 dockerd，改 `~/.docker/daemon.json` 后**必须完整重启**（杀 `com.docker.backend` / `vpnkit` + `wsl --shutdown` + 重开 DD）才生效；仅 `wsl --shutdown` 不够。
- 后续任何 `docker pull` 都依赖该镜像源，勿删。
- 其他可选源：Azure `https://dockerhub.icu`、腾讯云（需登录）、中科大（DNS 常不稳）——daocloud 在实测中最稳。`ghproxy` 等 GitHub 代理对 Docker 镜像无效，勿混用。

### 阶段 2：获取部署文件

从项目官方仓库取 `docker-compose.yaml` + `.env`（按需设密钥 / 口令），以及 compose 中挂载的**所有配置卷目录**（常见如 `nginx/`、`ssrf_proxy/`、各服务的 `conf/` 等）。

- 易错点：官方 compose 常依赖挂载的配置文件（如 `volumes/<svc>/conf/config.yaml`）。只取 compose 而漏取这些目录，会导致对应容器因「找不到配置文件」而 panic 重启（见阶段 4 排障）。
- 若只取到 compose 而缺少某配置卷，按报错从官方仓对应 `docker/volumes/...` 路径取回该文件即可。

### 阶段 3：拉取镜像并启动

在部署目录用 PowerShell **前台直跑**（后台任务跟踪在本环境不稳定，但镜像缓存在主机 WSL 卷持久）：

```
docker compose pull            # 增量拉取，已拉过的自动跳过
docker compose up -d
docker compose ps              # 核对 STATUS 是否 healthy
```

镜像源限流时 `docker compose pull` 可能失败，加重试：循环最多 4 次、每次间隔 20 秒。

### 阶段 4：验证与排障

- **验证可达性必须使用 `curl.exe 127.0.0.1`**（原生）。PowerShell 的 `Invoke-WebRequest` 会走系统代理挂死超时——属假阴性，并非服务未启动。
- 正常首次访问 `http://localhost` 通常重定向到初始化向导（如 `/install`），这是标准首次行为。
- 某容器 `Restarting` / panic，报错 `open .../config.yaml` 或 `open .../*.txt`：补对应文件后 `docker rm -f <容器>` + `docker compose up -d <服务>` **recreate**。recreate 还能恢复 entrypoint 解压后删掉的运行时 tar 包（否则报 `tar: ...tar.xz Cannot open`，非致命但状态不干净）。
- 端口监听自检：`Test-NetConnection -ComputerName 127.0.0.1 -Port 80` 的 `TcpTestSucceeded` 应为 `True`。

## 资源

- `scripts/set_daocloud_mirror.ps1`：一键配置 daocloud 镜像源并触发完整重启所需的前置步骤。
- `references/docker_pits.md`：通用坑的完整症状 / 根因 / 解法与精确命令。
- `examples/dify/`：以 Dify 1.x 为具体示例，演示本技能在真实项目上的落地（含 Dify 专属的 `volumes/sandbox` 配置坑）。

## 注意事项

- 本技能聚焦「部署跑通」的通用环节。项目特有的后续配置（如接入模型 / 初始化管理员）在控制台内完成，通常无需重启。
- 后台任务跟踪在本环境不稳定，重跑用前台 PowerShell 直跑最稳。
