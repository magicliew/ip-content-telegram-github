#!/usr/bin/env python3
"""Generate weekly IP content pages from partner YAML profiles.

Production-ish MVP behavior:
- Reads partners/*.yaml
- Generates docs/partners/<id>/index.md
- Generates docs/index.md landing page
- If OPENAI_API_KEY is present and openai package is installed, uses AI.
- Otherwise falls back to a richer deterministic generator so the system can be tested immediately.
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
    "生活小习惯背后的爱",
    "明明关心却假装没事",
    "把好东西留给你",
]

TOPIC_BANK = {
    "嘴硬心软": {
        "hooks": [
            "嘴上说不用的人，其实最容易偷偷开心",
            "有些长辈不是不喜欢，是不敢表现得太想要",
            "你买给他，他骂你；但他会开心很久",
            "他们嘴上讲你浪费，心里其实记很久",
            "最嘴硬的人，常常把开心藏得最深",
            "不是他们不要，是他们不好意思要",
            "长辈的开心，很多时候不是讲出来的",
            "有一种开心，叫嘴上骂你，心里很暖",
        ],
        "detail": "你买一包他平时舍不得买的东西，他第一句可能不是谢谢，而是：又乱花钱。可是隔天他可能会把东西收得好好的，甚至跟邻居讲：这是我孙女买的。",
        "emotion": "嘴硬不是冷淡，很多时候是他们那一代人表达爱的方式比较含蓄。",
    },
    "不想麻烦别人": {
        "hooks": [
            "有些人说不用，不是真的不用",
            "他们不是没需要，是习惯了不要麻烦别人",
            "越懂事的人，越常把需要藏起来",
            "你问他要不要，他永远先说不用",
            "有一种客气，其实是怕成为负担",
            "他们说自己可以，其实只是不好意思开口",
            "最让人心疼的，是明明需要却说不用",
            "不是他们坚强，是他们习惯自己忍一忍",
        ],
        "detail": "明明想吃，还是说不用；明明走路慢了，还是说自己可以；明明希望你多陪一下，却先叫你忙你的。",
        "emotion": "他们不是没有期待，只是很怕自己的期待变成别人的麻烦。",
    },
    "长大后才懂": {
        "hooks": [
            "小时候听不懂的话，长大后突然懂了",
            "以前觉得他们很啰嗦，现在才知道那是担心",
            "长大后才发现，很多爱都没有说出口",
            "以前嫌烦的提醒，现在听起来很暖",
            "原来有些话，不是控制，是怕你吃亏",
            "小时候觉得他们不懂我，长大后才知道他们很爱我",
            "有些爱，要长大一点才看得见",
            "以前听不进去的话，现在变成最想念的声音",
        ],
        "detail": "小时候觉得那些提醒很烦：吃饱了吗、不要太晚回、钱够不够用。长大后才发现，每一句背后其实都是担心。",
        "emotion": "很多亲情不是突然变深，是我们终于长大到看得懂。",
    },
    "节俭不是小气": {
        "hooks": [
            "他们不是小气，是以前真的苦过",
            "有些节俭，不是舍不得给你，是舍不得浪费",
            "一代人的省，是因为他们记得以前的不容易",
            "你以为他们很省，其实他们只是怕浪费",
            "为什么长辈总是不舍得丢东西？",
            "他们的节俭背后，藏着一整个年代的记忆",
            "不是每个省钱的人都小气",
            "有一种节俭，是苦日子留下来的习惯",
        ],
        "detail": "一张纸要用两面、剩菜舍不得倒、灯一定要关、塑料袋要收起来再用。我们看起来觉得麻烦，可是他们是真的经历过不够用的日子。",
        "emotion": "节俭不是小气，是他们对生活有一种很深的珍惜。",
    },
    "陪伴感": {
        "hooks": [
            "有时候他们要的不是礼物，是你坐下来陪一下",
            "陪伴这件事，越简单越珍贵",
            "你以为只是吃一餐饭，他们可能期待了一整天",
            "有些人嘴上说不用陪，心里其实很想你留下来",
            "最普通的一餐饭，可能是他们最开心的时刻",
            "他们不一定要你买东西，只想你多坐一下",
            "有一种幸福，是你愿意听他们讲重复的故事",
            "你的一点时间，可能是他们的一整天期待",
        ],
        "detail": "你只是坐下来吃一餐饭，听他讲重复讲过的故事，陪他看一会儿电视，他可能嘴上没说什么，但那天心情会特别好。",
        "emotion": "陪伴不一定要很隆重，很多时候，人在就够了。",
    },
    "不说爱但一直做": {
        "hooks": [
            "有些人一辈子不说爱，但一辈子都在做",
            "他们不会讲甜的话，只会把饭留给你",
            "不是所有爱都会说出口，有些爱会出现在餐桌上",
            "他不说想你，但会问你吃饱了吗",
            "有一种爱，没有拥抱，只有多夹一块肉",
            "他们不会表达，却一直在行动",
            "不是不爱，是他们那一代人真的不会说",
            "你以为他冷，其实他只是不会讲",
        ],
        "detail": "他不会突然说我很想你，但会问你几时回来吃饭；不会说我担心你，但会提醒你路上小心；不会说我爱你，但会把最好的先留给你。",
        "emotion": "有些爱不是语言型的，是行动型的。",
    },
    "代际差异": {
        "hooks": [
            "我们嫌他们啰嗦，他们怕我们吃亏",
            "两代人的表达不同，但关心是真的",
            "有些误会，不是不爱，是表达方式不一样",
            "我们在讲感受，他们在讲经验",
            "你觉得他不懂你，他其实只是用自己的方式担心你",
            "很多吵架不是不爱，是两代人讲爱的语言不一样",
            "他们不是要控制你，是怕你走错路",
            "代沟最难的地方，是大家都在关心，却听起来像责备",
        ],
        "detail": "我们想要被理解，他们想要我们平安；我们在讲感受，他们在讲经验。很多时候不是谁错了，是两代人用不同方式表达同一件事：我在乎你。",
        "emotion": "代沟不是没有爱，而是爱翻译错了。",
    },
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
    data.setdefault("tone", "自然、有共鸣、像真人讲话")
    return data


def clean_tag(text: Any, max_len: int = 14) -> str:
    tag = str(text or "").strip().replace(" ", "").replace("/", "")
    for ch in "，,。.!！?？：:；;（）()[]【】\"'":
        tag = tag.replace(ch, "")
    return tag[:max_len]


def hashtags_for(partner: dict[str, Any], value: str) -> str:
    role = clean_tag(partner.get("ip_role", "IP"), 10)
    audience = clean_tag(partner.get("audience", "目标受众"), 12)
    relationship = clean_tag(partner.get("relationship", "角色关系"), 12)
    directions = partner.get("content_directions", []) or []
    direction_tags = [f"#{clean_tag(x, 10)}" for x in directions[:3] if clean_tag(x, 10)]
    base = [
        f"#{role}日常",
        f"#{role}IP",
        f"#{relationship}",
        f"#{audience}",
        f"#{clean_tag(value)}",
        "#起号文案",
        "#短视频文案",
        "#内容创作",
        "#真实生活",
        "#共鸣文案",
        "#家庭日常",
        "#马来西亚生活",
    ] + direction_tags
    return " ".join(dict.fromkeys([x for x in base if x != "#"]))


def recommended_hooks_md(hooks: list[str]) -> str:
    lines = ["#### 最推荐 3 个"]
    reasons = [
        "情绪直接，前三秒容易让同类型受众停下来。",
        "有反差感，可以带出评论区共鸣。",
        "有具体关系冲突，适合短视频开头使用。",
    ]
    for i in range(3):
        lines.append(f"{i+1}. {hooks[i]}")
        lines.append(f"原因：{reasons[i]}")
        lines.append("")
    lines.append("#### 其他可测试标题")
    for i, hook in enumerate(hooks[3:8], start=4):
        lines.append(f"{i}. {hook}")
    return "\n".join(lines)


def caption_block(hook: str, partner: dict[str, Any], value: str) -> str:
    role = partner.get("ip_role", "这个角色")
    audience = partner.get("audience", "你")
    if partner.get("audience_perspective") == "direct_elder_parent":
        return f"""#### 通用版
{hook}。  
有时候不是你不想表达，是你习惯先替孩子、孙子女想。  
如果你也是嘴上常说不用、心里其实很开心的人，这一篇可能会像在讲你。

#### Facebook 微调版
很多阿公阿嬷、爸爸妈妈都一样。  
嘴上说不用、不麻烦、不需要，心里其实很在意孩子有没有想到自己。  
你是不是也是这样？嘴上念，心里暖。

#### Instagram 微调版
{hook}。  
有些爱不是不会有感觉，只是不习惯讲出来。  
你是不是也常常这样？

#### TikTok 微调版
{hook}。  
嘴上说不用，心里其实开心。  
这是不是你，还是你家里的爸爸妈妈 / 阿公阿嬷？

#### WeChat / 微信微调版
很多父母和长辈不是不需要关心，只是不习惯开口说需要。  
一句“我不用”，有时候不是拒绝，而是不想孩子麻烦。  
如果你也常常这样，这一篇写给你。

#### 小红书微调版
今天这个点真的很像很多阿公阿嬷、爸爸妈妈：{value}。  
不是没有感觉，只是嘴上习惯说不用；不是不开心，只是不知道怎样表达开心。  
你是不是也这样？"""

    return f"""#### 通用版
{hook}。  
有些关系，真的要长大一点才看得懂。  
如果你家里也有这样的阿公阿嬷或爸爸妈妈，你应该会明白这种感觉。你家里有没有一个这样的人？

#### Facebook 微调版
以前不懂的事，长大后突然懂了。  
原来很多爱不是没有出现，只是它出现的方式很普通。  
你家里有没有一个嘴上不说、但一直默默做的人？

#### Instagram 微调版
{hook}。  
有些爱真的藏在生活细节里。  
留言告诉我：你家里是不是也有这种人？

#### TikTok 微调版
{hook}。  
如果你家里也有这样的人，这支你一定懂。  
留言讲一个你长大后才懂的细节。

#### WeChat / 微信微调版
很多时候，我们不是一开始就看得懂家人的爱。  
小时候觉得啰嗦，长大后才发现，那些提醒、习惯和小动作，其实都是关心。  
这一篇想写给所有慢慢看懂家人表达方式的人。

#### 小红书微调版
今天这个点真的很有感：{value}。  
有些人不会把爱讲得很好听，但你认真看生活细节，就会发现他们其实一直都在做。  
你家里也有这种嘴硬但很暖的人吗？"""


def fallback_post(partner: dict[str, Any], day: int, value: str) -> str:
    data = TOPIC_BANK.get(value) or TOPIC_BANK["长大后才懂"]
    hooks = data["hooks"]
    if partner.get("audience_perspective") == "direct_elder_parent":
        hooks = [
            hooks[0].replace("的人", "的爸爸妈妈和阿公阿嬷"),
            "你是不是嘴上说不用，心里其实很开心？",
            "很多父母不是不想要，是不想麻烦孩子",
            "你每次说不用，其实孩子都看得出来",
            "阿公阿嬷和父母的嘴硬，很多时候是心软",
            "不是你不需要关心，是你习惯先替孩子想",
            "你说不要浪费钱，其实心里已经暖了",
            "有些开心，父母和长辈真的不太会讲出口",
        ]
    detail = data["detail"]
    emotion = data["emotion"]
    role = partner.get("ip_role", "这个角色")
    audience = partner.get("audience", "目标受众")
    relationship = partner.get("relationship", "角色关系")
    tone = partner.get("tone", "自然、有共鸣")

    if partner.get("audience_perspective") == "direct_elder_parent":
        script = f"""{hooks[0]}。

我做孙女这个角色，常常会发现一件事：很多阿公阿嬷、爸爸妈妈不是没有感觉，只是很少把感觉讲出来。你们那一代人，很多时候习惯先忍一忍，先说不用，先讲不要麻烦孩子。

{detail}

可是站在孙女、女儿的角度看，其实我们都看得出来。你嘴上可能说“不要买啦，很浪费钱”，可是东西会收好；嘴上说“我不用啦”，可是孩子回来坐一下，你会开心很久；嘴上说“你忙你的”，可是电话挂了之后，又会希望他下次再打来。

所以这一篇不是要笑你嘴硬，而是想替很多父母、很多阿公阿嬷把心里的话讲出来。你不是不需要被关心，你只是习惯不要开口；你不是不开心，你只是不好意思表现得太明显。

{emotion} 这种爱很安静，但其实很深。也因为这样，很多孩子和孙子女长大后才慢慢看懂：原来以前那些念、那些省、那些“不用”，背后都是爱。

如果你也是这种嘴上常常说不用、心里其实很暖的爸爸妈妈或阿公阿嬷，留言告诉我：你最常对孩子说哪一句“反话”？"""
    else:
        script = f"""{hooks[0]}。

我以前一直觉得，{relationship}之间，很多事情只要讲清楚就好了。可是后来才发现，不是每个人都会很直接地表达自己，尤其是我们家里那些比较传统、比较习惯忍一忍的人。

{detail}

如果你家里也有这样的阿公阿嬷、爸爸妈妈，或者你自己就是很少把爱说出口的长辈，你可能也懂这种时刻：明明只是一件很小的事，嘴上没有夸，甚至还要念几句，可是心里其实是开心的。

这就是{role}这个角色最适合被记住的地方。不是每天讲大道理，也不是故意煽情，而是把这些很多家庭都有、但平时没说出口的细节讲出来。

{emotion} 所以这一篇想让观众看到：原来我家里那个人也是这样，原来不是只有我经历过这种感觉。

如果你家里也有一个嘴上不说、但行动很诚实的人，留言讲一个他的生活小习惯。"""

    return f"""## Day {day}｜价值观：{value}

### 标题 / Hook
{recommended_hooks_md(hooks)}

### 口播文案
{script}

### 视频发布文案 / Caption
{caption_block(hooks[0], partner, value)}

### Hashtag
{hashtags_for(partner, value)}
"""


def fallback_generate(partner: dict[str, Any]) -> str:
    count = max(1, min(int(partner.get("posts_per_week", 7)), 14))
    week = this_week_label()
    platforms = "、".join(partner.get("platforms", []))
    values = [VALUE_ROTATION[i % len(VALUE_ROTATION)] for i in range(count)]
    if partner.get("audience_perspective") == "direct_elder_parent":
        direction_text = f"本周用「{partner.get('ip_role', 'IP角色')}视角」讲给阿公阿嬷和父母听。重点不是叫孩子理解长辈，而是让长辈/父母自己听了觉得：对，我就是这样，我嘴上说不用，其实心里有感觉。内容会用温柔、不冒犯的方式，把父母和长辈的嘴硬、节俭、不想麻烦孩子、不会表达爱，讲成一种被理解的情绪。"
        interaction_text = "这套内容适合先测试长辈/父母共鸣型起号，因为它容易让观众留言：『我也是这样』、『我每次都说不用』、『做父母的真的会这样』。"
    else:
        direction_text = f"本周先用「{partner.get('relationship', '角色关系')}」里的真实生活细节来建立 IP 记忆点。重点不是硬讲道理，而是把目标受众熟悉、但平时不会特别说出口的情绪讲出来：嘴硬、心软、不想麻烦别人、节俭、陪伴和代际差异。"
        interaction_text = "这套内容适合先测试共鸣型起号，因为它容易让观众留言：『我家也是这样』、『我阿嬷也是』、『看到想到我家人』。"

    parts = [
        f"# {partner.get('name')}｜{week} IP 起号内容周报",
        "",
        f"**IP 角色：** {partner.get('ip_role', '')}  ",
        f"**目标受众：** {partner.get('audience', '')}  ",
        f"**角色关系：** {partner.get('relationship', '')}  ",
        f"**主要平台：** {platforms}  ",
        f"**内容语气：** {partner.get('tone', '')}  ",
        "",
        "## 本周起号方向",
        "",
        direction_text,
        "",
        interaction_text,
        "",
        "## 本周价值观轮换",
        "",
    ]
    for i, value in enumerate(values, start=1):
        parts.append(f"- Day {i}：{value}")
    parts.append("")
    for day, value in enumerate(values, start=1):
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
    week = this_week_label()
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "请根据这个 IP 档案生成本周内容周报。当前周次："
                + week
                + "\n\n"
                + yaml.safe_dump(partner, allow_unicode=True, sort_keys=False),
            },
        ],
        temperature=0.85,
    )
    return response.choices[0].message.content


def partner_slug(partner: dict[str, Any]) -> str:
    return str(partner.get("telegram_user_id") or partner.get("name")).replace(" ", "-")


def write_partner_page(partner: dict[str, Any], content: str) -> Path:
    out_dir = DOCS_DIR / "partners" / partner_slug(partner)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def write_home_index(generated: list[tuple[dict[str, Any], Path]]) -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# IP 起号内容周报入口",
        "",
        f"最后更新：{now}",
        "",
        "这里会列出已经建立 IP 档案的伙伴。点进去就可以看本周每天要拍的标题、口播文案、Caption 和 Hashtag。",
        "",
        "## 伙伴列表",
        "",
    ]
    for partner, _path in generated:
        slug = partner_slug(partner)
        lines.append(f"- [{partner.get('name', slug)}](partners/{slug}/) — {partner.get('ip_role', '')} / {partner.get('audience', '')}")
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
