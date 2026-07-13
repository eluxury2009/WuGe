---
name: dify-local-deploy-cn
description: This skill should be used when deploying Dify locally on a mainland-China Windows + WSL2 + Docker Desktop machine via Docker Compose, or when diagnosing related failures — e.g. `docker pull` errors like "unexpected commit digest / failed precondition", "short read: expected N bytes but got N-1", or Docker Hub timeouts; Dify's `sandbox` container panicking in a restart loop; or verifying a freshly deployed Dify web console. It provides the verified daocloud mirror fix, the often-missed `volumes/sandbox` config files, and the correct localhost verification method.
agent_created: true
---

# Dify 本地部署（大陆 Windows + WSL2 + Docker Desktop）

## Overview

在大陆网络环境下，于 Windows + WSL2 + Docker Desktop 通过 Docker Compose 本地部署 Dify（1.x）。本技能固化了从镜像源修复、部署文件获取、容器启动到首次访问的完整流程，并精确给出三类高频坑的解法，避免重复踩雷。

## 适用环境假设

- Windows 10/11，Docker Desktop 已安装，WSL2 后端
- 部署目录（如 `Z:\dify-deploy`）含官方 `docker-compose.yaml` + `.env`
- 网络位于中国大陆，Docker Hub 直连被墙

## 工作流

### 阶段 0：确认 Docker 守护进程在线

- 使用 **PowerShell**（真实 Windows 进程，可连主机 daemon）执行 `docker ps`。
- 若守护进程未运行：用 PowerShell `Start-Process` 拉起 Docker Desktop，等待约 15 秒就绪。
- 环境注意：WorkBuddy 的 Bash 沙箱对带网络访问的命令（`git clone` / `docker pull`）会套覆盖层，命令结束后写入被丢弃；但 **docker 守护进程位于主机 WSL 卷，持久**。排障与拉取优先用 PowerShell 直跑。

### 阶段 1：修复镜像源（最关键，先做）

症状：`docker pull` 报 `unexpected commit digest ... failed precondition`，或 `short read: expected N bytes but got N-1`（镜像层被精确破坏 1 字节），或 Docker Hub 直连超时 `dial tcp ... failed to respond`。

根因：Docker Hub 在大陆直连被墙；Docker Desktop 按本机区域自动注入的镜像源（hpcloud 返回损坏层 / aliyun 个人源 403 / ustc DNS 死）全部失效。

解法：配置 daocloud 单源。运行 `scripts/set_daocloud_mirror.ps1`（写入 daemon.json + 杀后端进程 + `wsl --shutdown`），随后**手动重启 Docker Desktop**，再用 `docker pull busybox` 验证。

- 验证通过标志：拿到有效 digest（如 `sha256:fd8d9aa...`），且 `docker info` 的 Registry Mirrors 显示 `https://docker.m.daocloud.io/`。
- 注意：Docker Desktop 会按区域动态把镜像源注入 dockerd，改 `~/.docker/daemon.json` 后**必须完整重启**（杀 `com.docker.backend` / `vpnkit` + `wsl --shutdown` + 重开 DD）才生效；仅 `wsl --shutdown` 不够。
- 后续任何 `docker pull` 都依赖 daocloud，勿删该源。

详见 `references/dify_pits.md` 的「镜像源」一节。

### 阶段 2：获取 Dify 部署文件（勿漏 volumes/sandbox）

从官方仓库取 `docker-compose.yaml` + `.env`（设 `SECRET_KEY`）+ `nginx/` + `ssrf_proxy/`，**还必须取 `volumes/sandbox/` 整棵目录树**（含 `conf/config.yaml` 与 `dependencies/*.txt`）。

- 漏取会导致阶段 4 的 sandbox panic 重启（见阶段 4 排障）。
- 若只取到 compose 而缺少 volumes/sandbox，按 `references/dify_pits.md` 的「sandbox 配置缺失」一节，从官方仓 `docker/volumes/sandbox/` 取回 `conf/config.yaml`（`main` 分支；`1.16.0` tag 在 raw 上返回 404）以及空的 `dependencies/python-requirements.txt`、`node-requirements.txt`。

### 阶段 3：拉取镜像并启动

在部署目录用 PowerShell **前台直跑**（后台任务跟踪在本环境不稳定，但镜像缓存在主机 WSL 卷持久）：

```
docker compose pull            # 增量拉取，已拉过的自动跳过
docker compose up -d
docker compose ps              # 核对 STATUS 是否 healthy
```

daocloud 限流时 `docker compose pull` 可能失败，加重试：循环最多 4 次、每次间隔 20 秒。

### 阶段 4：验证与排障

- **验证可达性必须使用 `curl.exe 127.0.0.1`**（原生）。PowerShell 的 `Invoke-WebRequest` 会走系统代理挂死超时——属假阴性，并非 Dify 未启动。
- 正常首次访问 `http://localhost` 会重定向到 `/install`（管理员初始化向导），这是标准首次行为。
- `sandbox` 容器若 `Restarting (2)` / panic，报错 `open conf/config.yaml` 或 `open dependencies/python-requirements.txt`：补文件后执行 `docker rm -f dify-deploy-sandbox-1` + `docker compose up -d sandbox` **recreate**（恢复 entrypoint 解压后删掉的 node tar 包，否则报 `tar: node...tar.xz Cannot open`，非致命但状态不干净）。详见 `references/dify_pits.md`。

## 资源

- `scripts/set_daocloud_mirror.ps1`：一键配置 daocloud 镜像源并触发完整重启所需的前置步骤。
- `references/dify_pits.md`：三类坑的完整症状 / 根因 / 解法与精确命令。

## 注意事项

- 本技能聚焦「部署跑通」。模型接入（硅基流动 / DeepSeek / 千问）在 `http://localhost/install` 初始化后于「设置 → 模型供应商」添加，无需重启。
- 后台任务跟踪在本环境不稳定，重跑用前台 PowerShell 直跑最稳。
