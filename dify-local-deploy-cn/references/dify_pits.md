# Dify 本地部署 — 三类高频坑详解

本文件沉淀 2026-07-12 在大陆 Windows + WSL2 + Docker Desktop 实测踩坑与最终正确解法。每条含「症状 → 根因 → 解法 → 验证」。

---

## 坑一：镜像源（Docker Hub 被墙 + DD 自动注入源全坏）

### 症状
`docker pull` 任意公开镜像失败，典型两类报错：
- `unexpected commit digest ... failed precondition`（digest mismatch）
- `short read: expected N bytes but got N-1`（镜像层被精确破坏 1 字节）
- 或 Docker Hub 直连超时：`dial tcp 128.242.240.180:443 ... failed to respond`

### 根因（分层定位，最终版）
1. **Docker Hub 在大陆直连被墙 → 超时**，必须走国内镜像源。
2. Docker Desktop 按本机区域（中国）自动注入一组镜像源到 dockerd：`aliyun 个人源(26nfzd82.mirror.aliyuncs.com)`、`ustc(docker.mirrors.ustc.edu.cn)`、`hpcloud(docker.hpcloud.cloud)`。
   - aliyun 个人源：返回 **403**（需鉴权，不服务公开镜像）
   - ustc：**DNS 解析失败**（域名死）
   - **hpcloud：能连通但返回损坏的层** → 这就是 `digest mismatch` 的真凶
3. 其他公共镜像源在本机 DNS 也解析不了：`hub-mirror.c.163.com`、`mirror.ccs.tencentyun.com` 实测 NXDOMAIN。

### 旧理论（已证伪，勿再走）
曾误判为 Docker Desktop 的 `:5555` Docker Hub 代理损坏（依据 `quay.io` 成功而 `busybox` 失败）。实际 `quay.io` 是独立 registry、不经过 Docker Hub 镜像源，其成功与 Docker Hub 代理无关；腾讯电脑管家也只是干扰项（杀掉后主机直连变干净，但 dockerd 走 DD 后端链路，根因仍在镜像源）。

### 解法（已用 busybox 验证）
1. 把 `~/.docker/daemon.json` 设为单源：
   ```json
   {
     "registry-mirrors": ["https://docker.m.daocloud.io"]
   }
   ```
2. **完整重启 Docker**（关键，否则不生效）：
   - 杀进程 `com.docker.backend` / `vpnkit` 等
   - `wsl --shutdown`
   - 重新启动 Docker Desktop
3. 验证：
   - `docker info` 的 Registry Mirrors 应显示 `https://docker.m.daocloud.io/`
   - `docker pull busybox` 成功，拿到有效 digest（如 `sha256:fd8d9aa...`）

### DD 配置注入机制（复用价值高）
- dockerd 实际读 `/run/config/docker/daemon.json`（空文件）。
- `docker info` 里的 `:3128`/`:5555` 代理、`Registry Mirrors` 全是 DD Windows 后端按区域**动态注入**，不在任何 daemon.json；`settings-store.json` 的 `ProxyHTTPMode/proxies` 改了也会被 DD 启动即还原 → 命令行改不动这些显示项。
- 改 `~/.docker/daemon.json` 后，必须做「完整重启」才会被 DD 读取并重注入；只 `wsl --shutdown` 不杀后端进程则 DD 缓存的旧状态仍在，镜像源不更新。

---

## 坑二：sandbox 配置缺失（拼部署目录时漏了 volumes/sandbox 整树）

### 症状
`docker compose up -d` 后，`dify-deploy-sandbox-1` 状态 `Restarting (2)` 并反复 panic，日志两类报错：
- `failed to init config, err: open conf/config.yaml: no such file or directory`
- `failed to setup runner dependencies, err: open dependencies/python-requirements.txt: no such file or directory`

### 根因
- 用 WebFetch 之类拼部署目录时，只取了 `docker-compose.yaml` + `.env` + `nginx/` + `ssrf_proxy/`，**漏了官方仓的 `docker/volumes/sandbox/` 整棵目录树**。
- sandbox 进程以 CWD=`/app/storage` 去找 `conf/config.yaml` 与 `dependencies/*.txt`，而挂载卷 `./volumes/sandbox:/app/storage` 里这两个目录是空的 → panic。
- 官方镜像里 `dependencies/python-requirements.txt` 与 `node-requirements.txt` 默认就是 **0 字节空文件**（repo 不存这两文件，GitHub tree 里 `docker/volumes/sandbox/` 只有 `conf/config.yaml`）。所以补全时建**空文件**即可。

### 解法
1. 取回 `conf/config.yaml`：官方 `docker/volumes/sandbox/conf/config.yaml`。
   - 用 `main` 分支 raw（`1.16.0` tag 在 raw.githubusercontent 上返回 404）：
     `https://raw.githubusercontent.com/langgenius/dify/main/docker/volumes/sandbox/conf/config.yaml`
   - 内容示例（默认 key 为 `dify-sandbox`，须与 api 容器 `SANDBOX_API_KEY` 默认一致）：
     ```yaml
     app:
       port: 8194
       debug: True
       key: dify-sandbox
     max_workers: 4
     max_requests: 50
     worker_timeout: 5
     enable_network: True
     allowed_syscalls:
     proxy:
       socks5: ''
       http: ''
       https: ''
     ```
2. 在 `volumes/sandbox/dependencies/` 下建两个空文件：`python-requirements.txt`、`node-requirements.txt`。
3. **recreate 容器**（关键）：
   ```
   docker rm -f dify-deploy-sandbox-1
   docker compose up -d sandbox
   ```
   - 原因：sandbox entrypoint 启动时 `tar -xvf $NODE_TAR_XZ -C /opt` 解压 node，随后 `rm -f $NODE_TAR_XZ` 删包。首次成功解压后若再 `docker restart`，旧容器层里 tar 包已删 → 报 `tar: /opt/node-v20.20.0-linux-x64.tar.xz: Cannot open`（非致命，node 软链仍在），但状态不干净。recreate 从镜像重建即可恢复。
4. 验证：日志应出现 `config init success` → `runner dependencies init success` → `installing python dependencies` → `python dependencies installed`，最终 STATUS 变 `healthy`，不再重启。

---

## 坑三：验证可达性（PowerShell 代理假阴性）

### 症状
`docker ps` 显示所有容器 `Up`（api/db/redis/sandbox 均 healthy），但 PowerShell `Invoke-WebRequest -Uri http://localhost` **超时 15~20s 无响应**，误以为 Dify 没起来。

### 根因
PowerShell 的 `Invoke-WebRequest` 会读取系统/环境 HTTP 代理设置（本机曾配代理或 DD 注入），请求被导向挂死的代理而超时。这与 Dify 是否运行无关。

### 解法
- 用原生 `curl.exe` 直连 127.0.0.1 验证：
  ```
  curl.exe -s -o nul -w "HTTP:%{http_code}\n" --max-time 15 http://127.0.0.1/
  ```
  正常应返回 200 并带 Dify 前端 HTML；且访问 `http://localhost` 会重定向到 `/install`（首次初始化向导，标准行为）。
- 端口连通性可先用 `Test-NetConnection -ComputerName 127.0.0.1 -Port 80` 确认 `TcpTestSucceeded: True`。

---

## 附：完整可用命令清单（在部署目录执行）

```powershell
# 阶段1 配镜像源（脚本自动写 daemon.json + 杀后端 + wsl --shutdown，之后手动重启 DD）
# 见 scripts/set_daocloud_mirror.ps1

# 阶段3 拉取+启动（前台直跑）
docker compose pull
docker compose up -d
docker compose ps

# 阶段4 验证
curl.exe -s -o nul -w "HTTP:%{http_code}\n" --max-time 15 http://127.0.0.1/

# sandbox 重启循环修复
docker rm -f dify-deploy-sandbox-1
docker compose up -d sandbox
docker logs dify-deploy-sandbox-1 --tail 30
```

## 附：本机环境注记（2026-07-12 实测）
- 可用镜像源仅 `daocloud`（无需鉴权、层完整）与 aliyun 个人源（需 `docker login` 鉴权）。**后续任何 `docker pull` 都依赖 daocloud，勿删。**
- 本机 DNS 对 163/腾讯云等公共镜像域名解析失败，不可用。
- 后台任务跟踪在本环境不稳定（多次 `TaskOutput` 报 not found），但镜像缓存在主机 WSL 卷持久；重跑用前台 PowerShell 直跑最稳。
