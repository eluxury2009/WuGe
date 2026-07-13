# Dify 专属坑：sandbox 配置缺失

## 症状

`sandbox` 容器 `Restarting (2)` / panic，日志出现：

- `open conf/config.yaml: no such file or directory`
- `open dependencies/python-requirements.txt: no such file or directory`
- 或 `tar: node...tar.xz Cannot open`（recreate 后消失，非致命）

## 根因

官方 compose 依赖挂载的 `volumes/sandbox/` 整棵目录树（`conf/` + `dependencies/`）。拼部署目录时若只取 `docker-compose.yaml` / `.env` / `nginx/` / `ssrf_proxy/` 而漏掉它，容器因缺配置文件反复重启。

> 这正是通用技能「坑五：漏挂载配置卷致容器 panic」在 Dify 上的具体表现。

## 解法

1. 从官方仓 `docker/volumes/sandbox/` 取回（注意：`1.16.0` tag 在 raw 上返回 404，用 `main` 分支）：
   - `conf/config.yaml`（官方默认配置，sandbox 挂载点为 `/app/storage/conf/config.yaml`）
   - 空的 `dependencies/python-requirements.txt`、`node-requirements.txt`（官方默认即为空；sandbox 进程以 CWD=`/app/storage` 去找 `dependencies/...`，缺目录即报错）
2. 落到主机 `volumes/sandbox/conf/config.yaml` 与 `volumes/sandbox/dependencies/*.txt`。
3. `docker rm -f <sandbox容器>` + `docker compose up -d sandbox` **recreate**（恢复 entrypoint 解压后删掉的 node tar 包）。

## 验证

`docker logs <sandbox容器>` 出现 `config init success`、走完 python dependencies 阶段、状态 `health: starting` → 正常。
