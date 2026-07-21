# IP Content Telegram → GitHub Pages MVP

这是 Magic 的 **IP 起号内容周报系统** MVP。

伙伴在 Telegram bot 完成 IP 资料设定后，系统会每周自动生成一份网页周报，里面包含每天要拍的：

- 标题 / Hook
- 口播文案
- 视频发布文案 / Caption
- Hashtag
- Facebook / Instagram / TikTok / WeChat / 小红书 caption 微调版

网站入口：

https://magicliew.github.io/ip-content-telegram-github/

---

## 系统流程

```text
Telegram bot 收集伙伴 IP 资料
↓
保存成 partners/<telegram_user_id>.yaml
↓
GitHub Actions 每周一自动运行
↓
scripts/generate_weekly_content.py 生成内容
↓
输出到 docs/partners/<telegram_user_id>/index.md
↓
GitHub Pages 发布网页
```

---

## 本地试跑

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_weekly_content.py
```

生成结果：

```text
docs/index.md
docs/partners/demo/index.md
```

---

## GitHub Pages

当前使用：

```text
Settings → Pages → Deploy from a branch → main / docs
```

网页链接：

```text
https://magicliew.github.io/ip-content-telegram-github/
```

---

## GitHub Actions

### 每周自动生成

`.github/workflows/weekly.yml`

默认时间：

```text
每周一 9:00 AM Malaysia time
```

也可以手动运行：

```text
GitHub repo → Actions → Generate Weekly IP Content → Run workflow
```

---

## AI Key

如果没有 `OPENAI_API_KEY`，系统会使用内建模板生成较完整的测试文案。

如果要开启真正 AI 生成：

```text
GitHub repo → Settings → Secrets and variables → Actions → New repository secret
```

新增：

```text
OPENAI_API_KEY=你的 API key
```

可选变量：

```text
OPENAI_MODEL=gpt-4o-mini
```

---

## Telegram Bot

脚本：

```text
scripts/telegram_bot.py
```

本地运行：

```bash
export TELEGRAM_BOT_TOKEN="你的 Telegram bot token"
export SITE_BASE_URL="https://magicliew.github.io/ip-content-telegram-github"
python scripts/telegram_bot.py
```

正式部署时，需要把这个 bot 放在 Render / Railway / VPS 等长期运行环境。

---

## Partner Profile 格式

每个伙伴一个 YAML：

```yaml
name: Demo Partner
telegram_user_id: demo
ip_role: 孙女
audience: 家里有阿公阿嬷的年轻人
relationship: 孙女对阿公阿嬷
platforms:
  - Instagram
  - TikTok
  - Facebook
tone: 温柔、有共鸣、像真人讲话，不要太像 AI
content_directions:
  - 亲情
  - 生活观察
  - 长辈嘴硬心软
avoid:
  - 不要太像广告
  - 不要太官方
posts_per_week: 7
language: 华文
```

---

## 下一阶段可以升级

- Telegram bot 自动把 partner profile commit 回 GitHub
- 加入伙伴登录 / private dashboard
- 加入发布后数据复盘
- 根据播放量、点赞、留言、分享自动调整下周内容方向
- 接真实平台 dashboard 数据
