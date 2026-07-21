# IP Content Telegram → GitHub Pages MVP

这个 MVP 做的事情：

1. 伙伴在 Telegram bot 里输入：`启动 IP 起号文案助手模式`
2. Bot 一次问一个问题，收集 IP 角色、受众、关系、平台、语气、禁忌、每周篇数
3. Bot 把伙伴资料保存成 `partners/<telegram_user_id>.yaml`
4. 每周 GitHub Actions 自动运行 `scripts/generate_weekly_content.py`
5. 系统生成 `docs/partners/<telegram_user_id>/index.md`
6. GitHub Pages 把 `docs/` 发布成网站，伙伴打开链接就能看到本周每天要拍什么

> 第一版为了方便验证，如果没有 `OPENAI_API_KEY`，脚本会用内建模板生成示例文案；之后加 API key 就能接真实 AI。

## 本地测试

```bash
python3 scripts/generate_weekly_content.py
```

输出会在：

```text
docs/partners/demo/index.md
```

## GitHub Secrets 需要设置

如果要接 Telegram bot：

- `TELEGRAM_BOT_TOKEN`

如果要接 AI：

- `OPENAI_API_KEY`

## GitHub Pages 设置

进入 GitHub repo：

Settings → Pages → Build and deployment → Source 选择 `GitHub Actions`

然后使用 `.github/workflows/pages.yml` 发布。
