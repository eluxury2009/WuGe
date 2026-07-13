# Docker 本地部署避坑（大陆 Windows + WSL2 + Docker Desktop）

通用技能：在本机用 Docker Compose 部署任意服务时，固化「镜像源被墙 / 守护进程 / 拉取限流 / 验证假阴性」这一类大陆特有坑的解法。

## 这是什么

一个固化了「大陆 Win+WSL2+Docker Desktop 本地部署通用避坑」的 WorkBuddy 技能。无论你部署 Dify、Nextcloud、GitLab、WordPress 还是别的，凡是 `docker compose up -d` 这条路，踩的坑都高度雷同——本技能把通用那层一次性抽出来写清，处处复用。

Dify 这类具体项目的专属步骤，作为示例放在 `examples/dify/` 下，不污染通用主体。

## 适用场景

- 大陆 Windows + WSL2 + Docker Desktop 环境
- `docker pull` 报 `unexpected commit digest` / `short read` / Docker Hub 超时
- Docker 守护进程没起 / 改了 daemon.json 不生效
- 容器起来了但浏览器/脚本访问不了（实为验证方式错）
- 某容器因缺配置文件反复重启

## 怎么用

**方式 A（WorkBuddy 技能触发）**：满足上述场景时技能自动加载，按 `SKILL.md` 四阶段走。

**方式 B（手动照命令跑）**：

1. 阶段0：PowerShell 跑 `docker ps` 确认守护进程在线。
2. 阶段1：跑 `scripts/set_daocloud_mirror.ps1` → 手动重启 Docker Desktop → `docker pull busybox` 验证。
3. 阶段2：取官方 `docker-compose.yaml` + `.env` + 所有挂载配置卷。
4. 阶段3：`docker compose pull`（失败重试）→ `docker compose up -d` → `docker compose ps`。
5. 阶段4：用 `curl.exe 127.0.0.1` 验证，别用 PowerShell `Invoke-WebRequest`。

## 文件结构

```
docker-local-deploy-cn/
├── SKILL.md                        # 通用四阶段工作流
├── README.md                       # 本说明
├── scripts/set_daocloud_mirror.ps1 # 一键配 daocloud 镜像源 + 完整重启前置
├── references/docker_pits.md       # 通用坑详解
└── examples/dify/                  # 具体示例：Dify 1.x 落地
    ├── README.md
    └── references/dify_pits.md
```

## 注意事项

- 镜像源用 daocloud 单源最稳；ghproxy 等 GitHub 代理对 Docker 镜像无效。
- 改 daemon.json 后必须「杀后端 + wsl --shutdown + 重开 DD」完整重启。
- 验证一律 `curl.exe 127.0.0.1`，PowerShell 的 `Invoke-WebRequest` 会走代理假死。
