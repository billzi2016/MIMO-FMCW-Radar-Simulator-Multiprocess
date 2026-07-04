# 文档站点

本目录是 `MIMO-FMCW-Radar-Simulator-Multiprocess` 的 MkDocs 双语文档站点工程。

文档从第一版开始拆成两套目录：

- 中文内容：`docs/zh/`
- 英文内容：`docs/en/`

本地预览：

```bash
cd docs-site
pip install -r requirements.txt
mkdocs serve
```

构建静态站点：

```bash
mkdocs build --strict
```
