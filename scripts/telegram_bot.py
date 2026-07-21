#!/usr/bin/env python3
"""Telegram onboarding bot for IP profiles.

Run locally:
  export TELEGRAM_BOT_TOKEN=xxx
  pip install python-telegram-bot pyyaml
  python3 scripts/telegram_bot.py

This MVP saves partner profiles to partners/<telegram_user_id>.yaml.
Then GitHub Actions can generate the weekly pages.
"""
from __future__ import annotations

import datetime as dt
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

ROOT = Path(__file__).resolve().parents[1]
PARTNERS_DIR = ROOT / "partners"
PARTNERS_DIR.mkdir(exist_ok=True)

QUESTIONS = [
    ("ip_role", """你的 IP 角色是什么？
例如：孙女、妈妈、老板、营养师、朋友、老师、女儿、专业人士。

你可以直接回答：我是 ____ 角色。"""),
    ("audience", """明白。那你的内容主要是讲给谁看的？
不要写“大众”就好，可以具体一点。

你的目标受众是谁？"""),
    ("relationship", """好，那你这个角色跟受众是什么关系？
例如：孙女对阿公阿嬷、妈妈对妈妈、专业人士对普通人。

你跟受众的关系是什么？"""),
    ("platform_facebook", """接下来我需要你的平台链接。请先给我 Facebook 账号 / 页面链接。
如果没有 Facebook，可以回复：没有。"""),
    ("platform_instagram", """收到。接下来请给我 Instagram 链接。
如果没有 Instagram，可以回复：没有。"""),
    ("platform_tiktok", """好，接下来请给我 TikTok 链接。
如果没有 TikTok，可以回复：没有。"""),
    ("platform_wechat", """收到。接下来请给我 WeChat / 微信 / 视频号资料。
可以给账号名、链接或截图说明；如果没有，可以回复：没有。"""),
    ("platform_xiaohongshu", """最后，请给我小红书链接。
如果没有小红书，可以回复：没有。"""),
    ("tone", """你的内容语气想要怎样？
例如：温柔、有共鸣、像朋友聊天、搞笑、专业但不硬。"""),
    ("content_directions", """你希望内容方向是什么？
例如：亲情、健康、生活观察、创业、教育、产品分享。"""),
    ("avoid", """有什么不要写的吗？
例如：不要太像广告、不要太夸张、不要像 AI、不要太官方。"""),
    ("posts_per_week", """每个星期要生成几篇文案？
你可以回答：3、5 或 7。"""),
]

START_TEXT = """哈咯～我是你的 IP 起号文案助手。

我不会一开始就直接帮你乱写文案，因为每个 IP 的角色、受众和流量问题都不一样。

我会先简单了解你的 IP，之后每周帮你自动生成：

1. 标题 / Hook
2. 口播文案
3. 视频发布文案 / Caption
4. Hashtag

我们一步一步来就好。

第一个问题：你的 IP 角色是什么？
例如：孙女、妈妈、老板、营养师、朋友、老师、女儿、专业人士等等。

你可以直接回答：我是 ____ 角色。
"""


def profile_path(user_id: int) -> Path:
    return PARTNERS_DIR / f"{user_id}.yaml"


def load_profile(user_id: int) -> dict[str, Any]:
    path = profile_path(user_id)
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {"telegram_user_id": str(user_id)}


def save_profile(user_id: int, profile: dict[str, Any]) -> None:
    profile_path(user_id).write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")


def parse_list(text: str) -> list[str]:
    for sep in ["、", ",", "，", "/", "|"]:
        text = text.replace(sep, "\n")
    return [x.strip(" -•\t") for x in text.splitlines() if x.strip(" -•\t")]



PLATFORM_KEY_MAP = {
    "platform_facebook": ("facebook", "Facebook"),
    "platform_instagram": ("instagram", "Instagram"),
    "platform_tiktok": ("tiktok", "TikTok"),
    "platform_wechat": ("wechat", "WeChat / 微信视频号"),
    "platform_xiaohongshu": ("xiaohongshu", "小红书"),
}


def normalize_platform_value(text: str) -> str | None:
    value = text.strip()
    if not value or value.lower() in {"没有", "no", "none", "nil", "n/a", "na", "不要"}:
        return None
    return value


def generate_and_publish_dashboard(user_id: int) -> tuple[bool, str]:
    """Generate dashboard pages, commit changes, and push to GitHub Pages."""
    site_base_url = os.getenv("SITE_BASE_URL", "https://magicliew.github.io/ip-content-telegram-github").rstrip("/")
    page_url = f"{site_base_url}/partners/{user_id}/"
    try:
        subprocess.run(["python3", "scripts/generate_weekly_content.py"], cwd=ROOT, check=True, text=True, capture_output=True)
        subprocess.run(["git", "add", "partners", "docs"], cwd=ROOT, check=True, text=True, capture_output=True)
        status = subprocess.run(["git", "status", "--short"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        if status:
            subprocess.run(["git", "commit", "-m", f"Add/update dashboard for {user_id}"], cwd=ROOT, check=True, text=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True, text=True, capture_output=True)
        return True, page_url
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        return False, detail[-1200:]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    context.user_data.clear()
    context.user_data["step"] = 0
    context.user_data["profile"] = {
        "telegram_user_id": str(user.id),
        "name": user.full_name or user.username or str(user.id),
        "language": "华文",
        "start_date": dt.date.today().isoformat(),
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    await update.message.reply_text(START_TEXT)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    text = update.message.text or ""
    user_id = update.effective_user.id

    if "启动 IP 起号文案助手模式" in text:
        await start(update, context)
        return

    if "step" not in context.user_data:
        await update.message.reply_text("你可以输入：启动 IP 起号文案助手模式\n我就会开始一步一步帮你建立 IP 档案。")
        return

    step = int(context.user_data["step"])
    profile = context.user_data.get("profile") or load_profile(user_id)

    if step >= len(QUESTIONS):
        await update.message.reply_text("你的 IP 档案已经建立好了。之后系统会每周自动生成文案页面给你。")
        return

    key, _question = QUESTIONS[step]
    if key in PLATFORM_KEY_MAP:
        platform_key, platform_label = PLATFORM_KEY_MAP[key]
        value = normalize_platform_value(text)
        profile.setdefault("platform_links", {})
        profile.setdefault("platforms", [])
        if value:
            profile["platform_links"][platform_key] = value
            if platform_label not in profile["platforms"]:
                profile["platforms"].append(platform_label)
    elif key in {"content_directions", "avoid"}:
        profile[key] = parse_list(text)
    elif key == "posts_per_week":
        digits = "".join(ch for ch in text if ch.isdigit())
        profile[key] = max(1, min(int(digits or 7), 14))
    else:
        profile[key] = text.strip()

    context.user_data["step"] = step + 1
    context.user_data["profile"] = profile
    save_profile(user_id, profile)

    if step + 1 < len(QUESTIONS):
        await update.message.reply_text(QUESTIONS[step + 1][1])
    else:
        await update.message.reply_text("""好了，我已经收集完你的 IP 资料。

我现在会帮你生成专属 IP 起号 Dashboard，里面会有 Week 1 的 Day 1–Day 7 文案。
请等我一下下。""")
        success, result = generate_and_publish_dashboard(user_id)
        if success:
            await update.message.reply_text(
                f"""你的 IP 起号 Dashboard 已经生成：
{result}

里面会有：
1. 本周发布 Dashboard
2. Day 1–Day 7 快速按钮
3. 每天 Hook / 口播 / Caption / Hashtag

之后每周会自动更新同一个链接。
如果你之后要重新设定 IP，只要再输入：启动 IP 起号文案助手模式"""
            )
        else:
            await update.message.reply_text(
                f"""你的 IP 档案已经保存了，但我刚刚生成 / 发布 Dashboard 时遇到问题。

我会通知 Magic / 管理员检查。错误摘要：
{result}"""
            )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Please set TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
