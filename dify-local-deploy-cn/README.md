# dify-local-deploy-cn

> 大陆 Windows + WSL2 + Docker Desktop 环境下，用 Docker Compose 本地部署 Dify（1.x）的**避坑技能**。
> 固化了从「镜像源修复 → 部署文件获取 → 容器启动 → 首次访问验证」的完整流程，并精确给出三类高频坑的解法，避免重复踩雷。

---

## 一、这是什么（What）

这是一个 **WorkBuddy 技能（Skill）**，用于把 Dify 跑在本地 Docker 里。它本身不写代码、不编译，而是把一套**已被实测验证过的部署流程 + 排障手册**固化下来，让 AI 在你动手部署时直接照章办事，跳过环境特有的坑。

核心价值：把一次耗时数小时的排障经验，压缩成「触发即按流程走」的可复用资产。换机器、换时间、换人操作，都能复现正确路径。

> 适用 WorkBuddy 的 Skill 体系（user 级，跨项目可用）。非 WorkBuddy 用户也可直接参考 `references/dify_pits.md` 与下方命令清单手动操作。

---

## 二、适用场景（When / Scenario）

满足以下任意一条，就应当加载本技能：

| 场景 | 典型信号 |
|---|---|
| **大陆网络部署 Dify** | Windows + WSL2 + Docker Desktop，想本地跑 Dify 控制台 |
| **docker pull 报错** | `unexpected commit digest ... failed precondition`（digest mismatch）、`short read: expected N bytes but got N-1`（镜像层被精确破坏 1 字节）、Docker Hub 直连超时 |
| **sandbox 容器重启循环** | `dify-deploy-sandbox-1` 状态 `Restarting (2)`，日志报 `open conf/config.yaml` 或 `open dependencies/python-requirements.txt` |
| **部署完验证超时** | 容器都 `Up`/healthy，但 `Invoke-WebRequest http://localhost` 超时，怀疑没起来 |

---

## 三、怎么用（How）

### 方式 A：作为 WorkBuddy 技能（推荐）

把本目录放到 `~/.workbuddy/skills/dify-local-deploy-cn/`（user 级）或 `{项目}/.workbuddy/skills/`（项目级），重启/刷新 WorkBuddy 后生效。

之后你只需说一句，例如：

> 「帮我在本地用 Docker 部署 Dify」
> 「docker pull 一直报 digest mismatch 怎么办」
> 「sandbox 容器一直在重启」

AI 会自动加载本技能，按 `SKILL.md` 的四阶段流程执行，并在遇到三类坑时直接套用 `references/dify_pits.md` 的解法。

### 方式 B：手动照命令跑（无 WorkBuddy 也行）

#### 阶段 1：修复镜像源（最关键，先做）

```powershell
# 用脚本一键配置 daocloud 单源 + 杀后端 + wsl --shutdown
# 脚本：scripts/set_daocloud_mirror.ps1
# 执行后需「手动」重启 Docker Desktop，再验证：
docker info | findstr /C:"docker.m.daocloud.io"
docker pull busybox      # 成功拿到有效 digest 即生效
```

> 根因与完整说明见 `references/dify_pits.md`「坑一」。要点：Docker Hub 大陆被墙 + Docker Desktop 自动注入的镜像源（hpcloud 返回损坏层 / aliyun 403 / ustc DNS 死）全部失效；改 `~/.docker/daemon.json` 后必须**完整重启**（杀后端 + `wsl --shutdown` + 重开 DD）才生效。

#### 阶段 2：获取 Dify 部署文件（勿漏 volumes/sandbox）

从官方仓取 `docker-compose.yaml` + `.env`（设 `SECRET_KEY`）+ `nginx/` + `ssrf_proxy/`，**还必须取 `volumes/sandbox/` 整棵目录树**（含 `conf/config.yaml` 与 `dependencies/*.txt`）。

漏取会导致阶段 4 的 sandbox panic。补救见 `references/dify_pits.md`「坑二」。

#### 阶段 3：拉取镜像并启动

```powershell
# 在部署目录（如 Z:\dify-deploy）用 PowerShell 前台直跑
docker compose pull            # 增量拉取，已拉过的自动跳过（daocloud 限流失败可加重试）
docker compose up -d
docker compose ps              # 核对 STATUS 是否 healthy
```

#### 阶段 4：验证

```powershell
# 必须用原生 curl.exe 直连 127.0.0.1（PowerShell 的 Invoke-WebRequest 走系统代理会假阴性超时）
curl.exe -s -o nul -w "HTTP:%{http_code}\n" --max-time 15 http://127.0.0.1/
# 正常返回 200 并带 Dify 前端 HTML；浏览器开 http://localhost 会重定向到 /install（首次初始化向导）
```

sandbox 重启循环修复：

```powershell
docker rm -f dify-deploy-sandbox-1
docker compose up -d sandbox
docker logs dify-deploy-sandbox-1 --tail 30
```

---

## 四、核心避坑三连（精简版）

1. **镜像源**：Docker Hub 被墙 + DD 自动注入源全坏 → 设 `daocloud` 单源 + 完整重启，`busybox` 验证。
2. **sandbox 配置缺失**：拼部署目录漏了 `volumes/sandbox/` 整树（conf/config.yaml + 空 dependencies/*.txt）→ 补文件 + `docker rm` + `compose up -d sandbox` recreate 恢复 node 包。
3. **验证超时假阴性**：`Invoke-WebRequest` 走系统代理挂死 → 改用 `curl.exe 127.0.0.1` 验证，正常会重定向 `/install`。

完整症状 / 根因 / 解法与精确命令，见 [`references/dify_pits.md`](references/dify_pits.md)。

---

## 五、文件结构

```
dify-local-deploy-cn/
├── SKILL.md                          # 技能入口：四阶段工作流（触发即加载）
├── README.md                         # 本文档
├── references/
│   └── dify_pits.md                  # 三类坑完整症状/根因/解法与命令清单
└── scripts/
    └── set_daocloud_mirror.ps1       # 一键配 daocloud 镜像源 + 触发完整重启前置步骤
```

---

## 六、注意事项

- 本技能聚焦「部署跑通」。模型接入（硅基流动 / DeepSeek / 千问）在 `http://localhost/install` 初始化后，于「设置 → 模型供应商」添加 Key 即可，**无需重启**。
- 后续任何 `docker pull` 都依赖 daocloud 镜像源，**勿删**该源；本机 DNS 对 163/腾讯云等公共镜像域名解析失败，不可用。
- 后台任务跟踪在此类环境不稳定，重跑拉取 / 启动用**前台 PowerShell 直跑**最稳（镜像缓存在主机 WSL 卷持久）。

---

## 七、环境注记（2026-07-12 实测）

- 可用镜像源仅 `daocloud`（无需鉴权、层完整）与 aliyun 个人源（需 `docker login` 鉴权）。
- Docker Desktop 会按区域动态注入镜像源 / 代理到 dockerd，命令行改不动这些显示项，只能改 `~/.docker/daemon.json` 后完整重启。
- WorkBuddy 的 Bash 沙箱对 `git`/`docker pull` 等网络写命令套覆盖层、结束即丢；排障与拉取优先用 **PowerShell 真实进程**直跑。
