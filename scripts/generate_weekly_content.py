#!/usr/bin/env python3
"""Generate weekly IP content pages from partner YAML profiles.

MVP behavior:
- Reads partners/*.yaml
- Generates docs/partners/<id>/index.md
- If OPENAI_API_KEY is present and openai package is installed, uses AI.
- Otherwise falls back to deterministic template content so the repo can be tested immediately.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Missing dependency: pyyaml. Run: pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
PARTNERS_DIR = ROOT / "partners"
DOCS_DIR = ROOT / "docs"
PROMPT_PATH = ROOT / "prompts" / "weekly_content.md"

VALUE_ROTATION = [
    "嘴硬心软",
    "不想麻烦别人",
    "长大后才懂",
    "节俭不是小气",
    "陪伴感",
    "不说爱但一直做",
    "代际差异",
]

HOOK_LIBRARY = {
    "嘴硬心软": ["嘴上说不用的人，其实最容易偷偷开心", "有些长辈不是不喜欢，是不敢表现得太想要", "你买给他，他骂你；但他会开心很久"],
    "不想麻烦别人": ["有些人说不用，不是真的不用", "他们不是没需要，是习惯了不要麻烦别人", "越懂事的人，越常把需要藏起来"],
    "长大后才懂": ["小时候听不懂的话，长大后突然懂了", "以前觉得他们很啰嗦，现在才知道那是担心", "长大后才发现，很多爱都没有说出口"],
    "节俭不是小气": ["他们不是小气，是以前真的苦过", "有些节俭，不是舍不得给你，是舍不得浪费", "一代人的省，是因为他们记得以前的不容易"],
    "陪伴感": ["有时候他们要的不是礼物，是你坐下来陪一下", "陪伴这件事，越简单越珍贵", "你以为只是吃一餐饭，他们可能期待了一整天"],
    "不说爱但一直做": ["有些人一辈子不说爱，但一辈子都在做", "他们不会讲甜的话，只会把饭留给你", "不是所有爱都会说出口，有些爱会出现在餐桌上"],
    "代际差异": ["我们嫌他们啰嗦，他们怕我们吃亏", "两代人的表达不同，但关心是真的", "有些误会，不是不爱，是表达方式不一样"],
}

DETAIL_LIBRARY = {
    "嘴硬心软": "你买一包他平时舍不得买的东西，他嘴上会念你乱花钱，可是隔天可能会跟邻居讲很久。",
    "不想麻烦别人": "明明想吃，还是说不用；明明需要帮忙，还是说自己可以。",
    "长大后才懂": "小时候觉得那些提醒很烦，长大后才知道，每一句其实都是怕你吃亏。",
    "节俭不是小气": "一张纸要用两面、剩菜舍不得倒、灯一定要关，因为他们真的经历过不够用的年代。",
    "陪伴感": "你只是坐下来吃一餐饭、听他讲重复讲过的故事，他可能已经开心一整天。",
    "不说爱但一直做": "他不会说想你，但会问你吃饱了吗；不会说担心，但会把东西先留给你。",
    "代际差异": "我们想要被理解，他们想要我们平安；我们在讲感受，他们在讲经验。",
}


def this_week_label() -> str:
    today = dt.date.today()
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"


def read_partner(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("telegram_user_id", path.stem)
    data.setdefault("name", path.stem)
    data.setdefault("posts_per_week", 7)
    data.setdefault("platforms", ["Instagram", "TikTok", "Facebook"])
    data.setdefault("language", "华文")
    return data


def hashtags_for(partner: dict[str, Any], value: str) -> str:
    role = str(partner.get("ip_role", "IP")).replace(" ", "")
    audience = str(partner.get("audience", "目标受众")).replace(" ", "")[:12]
    base = [
        f"#{role}日常",
        f"#{role}IP",
        "#起号文案",
        "#短视频文案",
        "#内容创作",
        "#真实生活",
        "#共鸣文案",
        f"#{value}",
        f"#{audience}",
        "#马来西亚生活",
    ]
    return " ".join(dict.fromkeys(base))


def fallback_post(partner: dict[str, Any], day: int, value: str) -> str:
    role = partner.get("ip_role", "这个角色")
    audience = partner.get("audience", "目标受众")
    relationship = partner.get("relationship", "角色关系")
    hooks = HOOK_LIBRARY.get(value, HOOK_LIBRARY["长大后才懂"])
    detail = DETAIL_LIBRARY.get(value, DETAIL_LIBRARY["长大后才懂"])
    hook_lines = "\n".join(f"{i+1}. {h}" for i, h in enumerate(hooks))

    return f"""## Day {day}｜价值观：{value}

### 标题 / Hook
{hook_lines}

### 口播文案
{hooks[0]}。  
以前我也以为，{relationship}之间，很多事情讲清楚就好了。  
后来才发现，有些人的关心不是直接讲出来的。  
{detail}  
如果你也是{audience}，你可能也会慢慢懂：  
有些爱不是很大声，但它每天都在。  
它可能藏在一句提醒、一个小动作，或者一份明明嘴上说不用、心里却很珍惜的反应里。  
所以我们做{role}这个 IP，不只是讲故事，而是帮大家看见那些平常被忽略的爱。  
你家里也有这种人吗？

### 视频发布文案 / Caption
{hooks[0]}。  
有些关系，真的要长大一点才看得懂。  
你家里有没有一个这样的人？

### Hashtag
{hashtags_for(partner, value)}
"""


def fallback_generate(partner: dict[str, Any]) -> str:
    count = int(partner.get("posts_per_week", 7))
    week = this_week_label()
    platforms = "、".join(partner.get("platforms", []))
    parts = [
        f"# {partner.get('name')}｜{week} IP 起号内容周报",
        "",
        f"**IP 角色：** {partner.get('ip_role', '')}  ",
        f"**目标受众：** {partner.get('audience', '')}  ",
        f"**角色关系：** {partner.get('relationship', '')}  ",
        f"**主要平台：** {platforms}  ",
        "",
        "> 这一版是 MVP 模板生成。接入 OPENAI_API_KEY 后会改用 AI 根据资料生成更自然、更有变化的起号文案。",
        "",
    ]
    for day in range(1, count + 1):
        value = VALUE_ROTATION[(day - 1) % len(VALUE_ROTATION)]
        parts.append(fallback_post(partner, day, value))
    return "\n".join(parts)


def try_ai_generate(partner: dict[str, Any]) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请根据这个 IP 档案生成本周内容周报：\n" + yaml.safe_dump(partner, allow_unicode=True)},
        ],
        temperature=0.8,
    )
    return response.choices[0].message.content


def write_partner_page(partner: dict[str, Any], content: str) -> Path:
    partner_id = str(partner.get("telegram_user_id") or partner.get("name")).replace(" ", "-")
    out_dir = DOCS_DIR / "partners" / partner_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def write_home_index(generated: list[tuple[dict[str, Any], Path]]) -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    lines = ["# IP 起号内容周报入口", ""]
    for partner, path in generated:
        partner_id = str(partner.get("telegram_user_id") or partner.get("name")).replace(" ", "-")
        lines.append(f"- [{partner.get('name', partner_id)}](partners/{partner_id}/)")
    (DOCS_DIR / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    generated: list[tuple[dict[str, Any], Path]] = []
    for path in sorted(PARTNERS_DIR.glob("*.yaml")):
        partner = read_partner(path)
        content = try_ai_generate(partner) or fallback_generate(partner)
        out_path = write_partner_page(partner, content)
        generated.append((partner, out_path))
        print(f"Generated {out_path.relative_to(ROOT)}")
    write_home_index(generated)
    print(f"Generated docs/index.md for {len(generated)} partner(s)")


if __name__ == "__main__":
    main()
