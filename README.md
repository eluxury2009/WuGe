# WuGe · 五哥的 WorkBuddy 技能库

本仓库集中存放五哥（eluxury2009）自用的 WorkBuddy 技能。每个技能独立成目录，可直接复制到 `~/.workbuddy/skills/` 使用。

## 技能清单

| 目录 | 技能 | 说明 |
|---|---|---|
| `SKILL.md` / `README-知识库锻造.md`（仓库根） | obsidian-knowledge-forge「知识库锻造」 | Obsidian 知识库自动管道：inbox 监听 → AI 处理 → 分类 → 双链 → 质量审计（WSL2/Ubuntu，vault 在 I:\ObsidianVaults\MyBrain） |
| `dify-local-deploy-cn/` | dify-local-deploy-cn「Dify 本地部署避坑」 | 大陆 Win+WSL2+Docker Desktop 本地部署 Dify 的流程与排障手册（镜像源被墙 / sandbox 配置缺失 / 验证假阴性 三连坑） |

## 使用方法

1. 克隆本仓库：`git clone https://github.com/eluxury2009/WuGe.git`
2. 把需要的技能目录（或根目录 SKILL.md 对应的技能）复制到 WorkBuddy 的 user 级技能目录：
   - User 级：`C:\Users\<你>\.workbuddy\skills\`
3. 重启 WorkBuddy 或重新加载技能，即可触发使用。

> 注意：根目录的 `SKILL.md` 对应「知识库锻造」技能本体；`dify-local-deploy-cn/` 是其独立子技能目录。
