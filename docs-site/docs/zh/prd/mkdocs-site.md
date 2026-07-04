# MkDocs 站点 PRD 摘要

文档站点必须作为独立 MkDocs 工程放在 `docs-site/` 下。

核心要求：

- 使用 MkDocs 作为文档框架。
- 使用 i18n 插件支持双语文档。
- 中文内容放在 `docs-site/docs/zh/`。
- 英文内容放在 `docs-site/docs/en/`。
- 第一版实现时就同时创建两套语言目录。
- 尽量保持中英文导航结构一致。
- 支持 GitHub Actions 构建和 GitHub Pages 部署。

完整源 PRD 保存在 `docs-site/mkdocs_prd.md`。
