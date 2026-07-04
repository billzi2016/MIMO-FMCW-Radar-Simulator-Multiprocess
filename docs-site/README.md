# Docs Site

This directory contains the MkDocs documentation site for `MIMO-FMCW-Radar-Simulator-Multiprocess`.

The content is split from the beginning:

- Chinese: `docs/zh/`
- English: `docs/en/`

Build locally:

```bash
cd docs-site
pip install -r requirements.txt
mkdocs serve
```

Build static files:

```bash
mkdocs build --strict
```
