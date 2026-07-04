# GitHub Actions PRD 摘要

文档部署工作流必须聚焦静态文档构建和 GitHub Pages 部署。

核心要求：

- 只在文档相关内容变更时触发。
- 触发路径同时包含 `docs-site/docs/en/**` 和 `docs-site/docs/zh/**`。
- 支持手动 `workflow_dispatch`。
- 从 `docs-site/requirements.txt` 安装依赖。
- 使用 MkDocs strict 模式构建。
- 上传并部署生成后的静态站点到 GitHub Pages。

完整源 PRD 保存在 `docs-site/github_action_prd.md`。
