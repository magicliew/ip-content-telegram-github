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

import os
from pathlib import Path
from typing import Any

import yaml
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

ROOT = Path(__file__).resolve().parents[1]
PARTNERS_DIR = ROOT / "partners"
PARTNERS_DIR.mkdir(exist_ok=True)

QUESTIONS = [
    ("ip_role", "你的 IP 角色是什么？\n例如：孙女、妈妈、老板、营养师、朋友、老师、女儿、专业人士。\n\n你可以直接回答：我是 ____ 角色。"),
    ("audience", "明白。那你的内容主要是讲给谁看的？\n不要写“大众”就好，可以具体一点。\n\n你的目标受众是谁？"),
    ("relationship", "好，那你这个角色跟受众是什么关系？\n例如：孙女对阿公阿嬷、妈妈对妈妈、专业人士对普通人。\n\n你跟受众的关系是什么？"),
    ("platforms", "接下来请告诉我你主要经营哪些平台？\n例如：Facebook、Instagram、TikTok、小红书、微信。"),
    ("tone", "你的内容语气想要怎样？\n例如：温柔、有共鸣、像朋友聊天、搞笑、专业但不硬。"),
    ("content_directions", "你希望内容方向是什么？\n例如：亲情、健康、生活观察、创业、教育、产品分享。"),
    ("avoid", "有什么不要写的吗？\n例如：不要太像广告、不要太夸张、不要像 AI、不要太官方。"),
    ("posts_per_week", "每个星期要生成几篇文案？\n你可以回答：3、5 或 7。"),
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
    if key in {"platforms", "content_directions", "avoid"}:
        profile[key] = parse_list(text)
    elif key == "posts_per_week":
        digits = "".join(ch for ch in text if ch.isdigit())
        profile[key] = int(digits or 7)
    else:
        profile[key] = text.strip()

    context.user_data["step"] = step + 1
    context.user_data["profile"] = profile
    save_profile(user_id, profile)

    if step + 1 < len(QUESTIONS):
        await update.message.reply_text(QUESTIONS[step + 1][1])
    else:
        url_hint = f"docs/partners/{user_id}/index.md"
        await update.message.reply_text(
            "好了，你的 IP 档案已经建立完成。\n\n"
            "接下来系统每周会根据这个档案生成：标题、口播文案、Caption 和 Hashtag。\n\n"
            f"第一版生成后会出现在：{url_hint}"
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
