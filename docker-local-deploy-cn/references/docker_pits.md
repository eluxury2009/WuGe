# 通用坑详解（大陆 Win + WSL2 + Docker Desktop）

## 坑一：镜像源损坏 / Docker Hub 被墙

**症状**
- `docker pull` 报 `unexpected commit digest ... failed precondition`
- 或 `short read: expected N bytes but got N-1`（镜像层被精确破坏 1 字节）
- 或直连超时 `dial tcp 20.205.243.xx:443: i/o timeout`

**根因**
Docker Hub 在大陆直连被墙。Docker Desktop 会按本机区域自动注入镜像源，但这些源常常全部失效：hpcloud 返回损坏层（digest mismatch 真凶）、aliyun 个人源 403 需鉴权、ustc DNS 死、163/腾讯云 DNS 解析不了。

**解法**
设 daocloud 单源。运行 `scripts/set_daocloud_mirror.ps1`（写 `~/.docker/daemon.json` + 杀后端 + `wsl --shutdown`），随后**手动重启 Docker Desktop**，再 `docker pull busybox` 验证。
- 验证标志：拿到有效 digest（`sha256:...`），`docker info` 的 Registry Mirrors 显示 `https://docker.m.daocloud.io/`。
- daocloud 在实测中最稳；其他可选 Azure `https://dockerhub.icu`、腾讯云（需登录）。`ghproxy` 等 GitHub 代理对 Docker 镜像无效。

---

## 坑二：改 daemon.json 不生效（重启不彻底）

**症状**
配了镜像源，`docker info` 仍没显示；或 pull 依旧超时。

**根因**
Docker Desktop 把镜像源按区域动态注入 dockerd。仅 `wsl --shutdown` 只关了 WSL，DD 后端进程（`com.docker.backend` / `vpnkit`）仍缓存旧源。

**解法**
杀后端进程 + `wsl --shutdown` + 重开 DD，**三步缺一不可**。
`set_daocloud_mirror.ps1` 已做前两步（杀进程 + shutdown），第三步（重开 DD）需手动。

---

## 坑三：验证超时假阴性（PowerShell 代理）

**症状**
容器 `Up`、端口监听正常，但 `Invoke-WebRequest http://localhost` 超时；容易误判「服务没起来」。

**根因**
PowerShell 的 `Invoke-WebRequest` 走系统代理，连 localhost 也被代理挂死，是假阴性。

**解法**
用原生 `curl.exe 127.0.0.1` 直连验证：
```
curl.exe -s -o $null -w "HTTP:%{http_code}\n" --max-time 15 http://127.0.0.1/
```
返回 200 / 重定向 HTML 即正常。端口自检：`Test-NetConnection -ComputerName 127.0.0.1 -Port 80` 的 `TcpTestSucceeded` 应为 `True`。

---

## 坑四：拉取限流 / 中断

**症状**
pull 中途失败、偶发 digest 校验失败。

**根因**
免费镜像源限流。

**解法**
`docker compose pull` 加重试循环（最多 4 次，间隔 20s）。镜像缓存在主机 WSL 卷，重跑只拉剩余，已拉的不重复。

---

## 坑五（项目相关）：漏挂载配置卷致容器 panic

**症状**
某容器 `Restarting`，日志 `open <path>/config.yaml: no such file or directory`。

**根因**
只取了 compose，漏了它挂载的配置卷目录（如 `volumes/<svc>/conf/`）。

**解法**
1. 从官方仓对应 `docker/volumes/...` 取回缺失文件。
2. 补到主机挂载点。
3. `docker rm -f <容器>` + `docker compose up -d <服务>` **recreate**。
   recreate 同时恢复 entrypoint 解压后删掉的运行时 tar 包（否则报 `tar: ...tar.xz Cannot open`，非致命但状态不干净）。
