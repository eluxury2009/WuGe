# 示例：用通用技能部署 Dify 1.x

把 `docker-local-deploy-cn` 通用技能落到 Dify 这个具体项目上的步骤。Dify 专属坑见 `references/dify_pits.md`。

## 部署目录准备

从官方仓 `langgenius/dify` 取（注意用 `main` 分支或对应 tag 的 `docker/` 目录）：

- `docker-compose.yaml`（如 1.16.0-rc1 或对应版本）
- `.env`（务必设 64 位 `SECRET_KEY`）
- `nginx/`、`ssrf_proxy/`
- **`volumes/sandbox/` 整棵目录树**（含 `conf/config.yaml` 与 `dependencies/*.txt`）——漏取会导致 sandbox 容器 panic，详见 `dify_pits.md`

> 通用技能「阶段 2」强调的「别漏挂载配置卷」在这里就是 `volumes/sandbox/` 这一整棵。

## 启动

照通用技能阶段 3：

```
docker compose pull            # daocloud 源；失败加重试
docker compose up -d
docker compose ps              # 核对 api/db/redis/sandbox 等 healthy
```

## 访问与初始化

- 验证：`curl.exe 127.0.0.1`（通用技能阶段 4）。
- 浏览器开 `http://localhost` 会跳 `/install` 建管理员账号（标准首次行为）。
- 模型接入（硅基流动 / DeepSeek / 千问）在「设置 → 模型供应商」填 Key，无需重启。
