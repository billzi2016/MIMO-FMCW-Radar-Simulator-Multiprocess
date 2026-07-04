# GitHub Actions PRD Summary

The documentation deployment workflow must focus on static documentation build and GitHub Pages deployment.

Key requirements:

- Trigger on documentation-related changes.
- Include both `docs-site/docs/en/**` and `docs-site/docs/zh/**` in path filters.
- Support manual `workflow_dispatch`.
- Install dependencies from `docs-site/requirements.txt`.
- Build with MkDocs in strict mode.
- Upload and deploy the generated static site to GitHub Pages.

The full source PRD is maintained at `docs-site/github_action_prd.md`.
