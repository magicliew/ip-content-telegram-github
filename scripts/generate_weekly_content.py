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
import html
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

DIRECT_ELDER_HOOKS = {
    "嘴硬心软": [
        "阿公阿嬷，你嘴上说不用，其实心里是开心的吧？",
        "你每次骂孩子乱花钱，东西却收得很好",
        "阿嬷说不要买，其实收到的时候会偷偷开心",
        "阿公阿嬷最常讲不用，但心里最容易感动",
        "嘴上念两句，心里暖很久，说的是不是你？",
        "你不是不喜欢孩子买给你，是怕孩子花钱",
        "有些开心，阿公阿嬷真的不太会讲出口",
        "阿嬷骂你乱花钱，可是东西收得比谁都好",
    ],
    "不想麻烦别人": [
        "阿公阿嬷，你说不用，不一定是真的不用吧？",
        "你不是没有需要，是不想麻烦孩子",
        "越懂事的长辈，越常把需要藏起来",
        "你每次讲自己可以，其实是不想别人担心",
        "有一种客气，是怕自己变成孩子的负担",
        "明明想要人陪，却先叫孩子去忙",
        "阿公阿嬷，你们是不是最常讲：我不用啦",
        "你说没关系的时候，心里真的没关系吗？",
    ],
    "长大后才懂": [
        "阿公阿嬷，以前你讲的话，我现在慢慢懂了",
        "小时候听不懂，长大后才知道你们是为我好",
        "以前觉得你啰嗦，现在才知道你是在担心",
        "阿嬷以前讲的老话，现在越来越有道理",
        "有些老人家的话，要长大一点才听得懂",
        "以前嫌你烦，现在最想听你再讲一次",
        "阿公阿嬷讲的不是老派，是人生经验",
        "原来你们以前不是管太多，是怕我们吃亏",
    ],
    "节俭不是小气": [
        "阿公阿嬷，你们不是小气，是以前真的苦过",
        "你什么都舍不得丢，其实不是因为小气",
        "阿嬷那句还能用，我现在才懂",
        "阿公阿嬷省了一辈子，最后都花在家里人身上",
        "你不是不喜欢好的东西，是习惯先想别人",
        "老人家的节俭，藏着以前不容易的日子",
        "你舍不得浪费，是因为你知道东西来得不容易",
        "阿嬷不是舍不得花钱，是舍不得乱花钱",
    ],
    "陪伴感": [
        "阿公阿嬷，其实你要的不是礼物，是我们坐下来陪一下吧？",
        "一餐饭而已，你可能已经期待了一整天",
        "你嘴上叫孩子忙自己的，心里其实想他多坐一下",
        "陪你看一下电视，可能就是你今天最开心的事",
        "阿公阿嬷最开心的，不一定是收到东西",
        "有时候我们人在，你们就很开心了",
        "你一直讲不用陪，其实很想有人听你聊天吧？",
        "阿嬷重复讲的故事，其实是在找人陪",
    ],
    "不说爱但一直做": [
        "阿公阿嬷不会说爱，可是一直在做给我们看",
        "你不会讲想我，只会问我吃饱了吗",
        "阿嬷的爱不是我爱你，是锅里留着的饭",
        "阿公不说担心，但会一直叫你路上小心",
        "你们那一代人，爱都藏在动作里",
        "不说爱的人，其实常常做最多",
        "阿公阿嬷不会讲甜话，但会把好的留给你",
        "有一种爱，没有抱抱，只有多夹一块肉",
    ],
    "代际差异": [
        "阿公阿嬷，我们不是不爱听，是有时候真的听不懂你们的担心",
        "你们讲经验，我们讲感受，所以才常常误会",
        "有些吵架不是不爱，是两代人表达不一样",
        "我们嫌你啰嗦，你怕我们吃亏",
        "阿公阿嬷的关心，听起来有时候像责备",
        "不是你们老派，是我们还没听懂你们的爱",
        "代沟最难的地方，是大家明明都在关心",
        "你用你的方式疼我们，我们用我们的方式学着懂你",
    ],
}


def hooks_for_partner(partner: dict[str, Any], value: str) -> list[str]:
    if partner.get("audience_perspective") == "direct_elder_parent":
        return DIRECT_ELDER_HOOKS.get(value, TOPIC_BANK.get(value, TOPIC_BANK["长大后才懂"])["hooks"])
    return TOPIC_BANK.get(value, TOPIC_BANK["长大后才懂"])["hooks"]


def this_week_label() -> str:
    today = dt.date.today()
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"


def parse_date(value: Any) -> dt.date:
    """Parse partner start_date; fallback to today for old profiles."""
    if isinstance(value, dt.date):
        return value
    text = str(value or "").strip()
    if text:
        try:
            return dt.date.fromisoformat(text[:10])
        except ValueError:
            pass
    return dt.date.today()


def partner_timeline(partner: dict[str, Any], count: int) -> dict[str, Any]:
    """Compute rolling dashboard week from onboarding date or an explicit content start date.

    `content_start_date` lets Magic collect onboarding now but schedule the generated
    Week 1 content for a future week when this week's videos are already prepared.
    """
    today = dt.date.today()
    onboarding_date = parse_date(partner.get("start_date") or partner.get("created_at"))
    start_date = parse_date(partner.get("content_start_date") or onboarding_date)

    if partner.get("content_start_date"):
        current_week = 1 if today <= start_date else ((today - start_date).days // 7) + 1
        week_start = start_date + dt.timedelta(days=(current_week - 1) * 7)
    else:
        if start_date > today:
            start_date = today
        days_since_start = (today - start_date).days
        current_week = (days_since_start // 7) + 1
        week_start = start_date + dt.timedelta(days=(current_week - 1) * 7)

    week_end = week_start + dt.timedelta(days=count - 1)
    return {
        "today": today,
        "start_date": onboarding_date,
        "content_start_date": start_date,
        "current_week": current_week,
        "week_start": week_start,
        "week_end": week_end,
    }


def fmt_date(date_value: dt.date) -> str:
    return f"{date_value.month}月{date_value.day}日"


def weekday_zh(date_value: dt.date) -> str:
    names = ["一", "二", "三", "四", "五", "六", "日"]
    return f"星期{names[date_value.weekday()]}"


def publish_status(post_date: dt.date, today: dt.date) -> str:
    if post_date < today:
        return "待复盘"
    if post_date == today:
        return "今日发布"
    return "待发布"


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
{hook}  
有时候不是你不想表达，是你习惯先替孩子、孙子女想。  
如果你也是嘴上常说不用、心里其实很开心的人，这一篇可能会像在讲你。

#### Facebook 微调版
很多阿公阿嬷、爸爸妈妈都一样。  
嘴上说不用、不麻烦、不需要，心里其实很在意孩子有没有想到自己。  
你是不是也是这样？嘴上念，心里暖。

#### Instagram 微调版
{hook}  
有些爱不是不会有感觉，只是不习惯讲出来。  
你是不是也常常这样？

#### TikTok 微调版
{hook}  
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
    hooks = hooks_for_partner(partner, value)
    detail = data["detail"]
    emotion = data["emotion"]
    role = partner.get("ip_role", "这个角色")
    audience = partner.get("audience", "目标受众")
    relationship = partner.get("relationship", "角色关系")
    tone = partner.get("tone", "自然、有共鸣")

    if partner.get("audience_perspective") == "direct_elder_parent":
        direct_detail = (
            detail
            .replace("你买一包他平时舍不得买的东西", "孩子买一包你平时舍不得买的东西")
            .replace("他第一句可能不是谢谢", "你第一句可能不是谢谢")
            .replace("他可能会把东西收得好好的", "你可能会把东西收得好好的")
            .replace("这是我孙女买的", "这是我孩子 / 孙女买的")
        )
        script = f"""{hooks[0]}

很多爸爸妈妈、阿公阿嬷，其实都很像。孩子问你要不要，你第一句一定是“不用啦”；孩子买东西给你，你第一句也不是谢谢，是“又乱花钱”。

但你真的不开心吗？其实不是。{direct_detail}

你只是习惯了先替孩子想。怕孩子花钱，怕孩子麻烦，怕自己开口以后变成负担。所以明明心里有一点开心，嘴巴还是先忍不住念两句。

我做孙女这个角色，最想讲的不是“长辈很可爱”这么简单。我想讲的是：很多父母和阿公阿嬷不是没有感受，是一辈子都没学过怎样直接表达感受。你们那一代人，爱孩子的方式常常不是说“我想你”，而是问“吃饱了吗”；不是说“我很开心”，而是把孩子买的东西收得好好的。

所以这一篇不是要笑你嘴硬，是想替你讲一句心里话：你不是不需要被关心，你只是不好意思承认自己也会期待。

{emotion} 其实孩子和孙子女很多时候都看得出来。你嘴上骂，心里暖；你嘴上说不用，东西却舍不得丢；你嘴上叫他们忙自己的，心里却希望他们多坐一下。

如果你也是这种爸爸妈妈或阿公阿嬷，留言讲一句你最常对孩子说的“反话”。是“不要买啦”、还是“我不用啦”、还是“你忙你的”？"""
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


def platform_analysis_block(partner: dict[str, Any]) -> str:
    links = partner.get("platform_links", {}) or {}
    platforms = partner.get("platforms", []) or []
    direct_elder = partner.get("audience_perspective") == "direct_elder_parent"
    viewer_note = "主要打中阿公阿嬷和父母本人，让他们听了觉得被理解，而不是只写给孩子/孙子女看。" if direct_elder else "主要打中目标受众的共鸣，让他们看到自己和身边人的关系。"

    def link_line(key: str, label: str) -> str:
        value = links.get(key)
        if not value:
            return f"- **{label}：** 暂无链接 / 资料"
        return f"- **{label}：** {value}"

    return "\n".join([
        "## 平台账号分析",
        "",
        "### 已收集的平台资料",
        link_line("facebook", "Facebook"),
        link_line("instagram", "Instagram"),
        link_line("tiktok", "TikTok"),
        link_line("wechat", "WeChat / 微信"),
        link_line("xiaohongshu", "小红书"),
        "",
        "### 初步账号判断",
        f"- **核心人设：** {partner.get('ip_role', '')}，用晚辈视角讲长辈 / 父母关系。",
        f"- **主要受众：** {partner.get('audience', '')}。{viewer_note}",
        f"- **角色关系：** {partner.get('relationship', '')}。这个关系适合用真实生活细节、反话、嘴硬心软、陪伴感来起号。",
        f"- **语气方向：** {partner.get('tone', '')}",
        "",
        "### 各平台文案方向",
        "- **Facebook：** 适合情绪完整一点的 caption，重点放在家庭共鸣、父母心声、长辈真实想法，适合引导留言分享家庭故事。",
        "- **Instagram：** 适合短一点、更有共鸣金句感的 caption，Hook 要清楚，留言点要轻。",
        "- **TikTok：** 适合强 Hook、直接刺中情绪，开头第一句话要像观众心里的话。",
        "- **WeChat / 微信：** 适合稍微完整、有温度、有价值观总结的文字，让父母 / 长辈读起来不被冒犯。",
        "- **小红书：** 适合真实分享口吻，标题要像生活观察，不要太官方。",
        "",
        "### 过去内容文案架构观察",
        "目前系统已收集平台链接，但还没有接 dashboard / API 自动读取每支影片表现，所以这一版先不乱编播放量、点赞、留言数据。",
        "正式分析时会比较：过去表现较好内容的开头 Hook、口播结构、caption 语气、留言点、平台差异，再决定下周方向。",
        "",
        "### 本周先测试方向",
        "先测试「被长辈 / 父母本人听懂的共鸣型文案」：不是叫年轻人理解长辈，而是让阿公阿嬷、爸爸妈妈自己觉得：这篇是在讲我。",
        "",
    ])


def account_diagnosis_block(partner: dict[str, Any]) -> str:
    direct_elder = partner.get("audience_perspective") == "direct_elder_parent"
    if direct_elder:
        core_issue = "现在最容易卡住的地方，是内容如果写成『年轻人看长辈』，就会吸引到孩子/孙子女；但你的真正受众是阿公阿嬷和父母本人，所以文案必须让他们觉得：这篇是在讲我。"
        breakthrough = "Week 先测试『替父母/长辈说出不好意思讲出口的话』，用温柔、不冒犯的方式讲嘴硬、节俭、不想麻烦孩子、不会表达爱。"
    else:
        core_issue = "很多账号不起号，不一定是内容不好，而是观众还没有一秒看懂：你是谁、你代表什么、为什么我要持续看你。"
        breakthrough = "Week 先测试『把目标受众心里的那句话讲出来』，让 Hook 更像内心独白，而不是普通分享开场。"

    return "\n".join([
        "## 起号诊断",
        "",
        "### 为什么账号现在可能还没起号",
        f"1. **IP 记忆点需要更清楚：** {partner.get('ip_role', '这个角色')} 不能只是一个身份，要变成观众记得住的内容立场。",
        f"2. **受众要更精准：** 内容要明确讲给「{partner.get('audience', '目标受众')}」，不要让算法和观众都觉得太散。",
        "3. **Hook 要更像心里话：** 开头不能只是记录生活，要像观众刷到时心里突然被讲中的一句话。",
        "4. **留言点要更具体：** 不要只问『你觉得呢？』，要问观众很容易回答的真实生活细节。",
        f"5. **目前关键问题：** {core_issue}",
        "",
        "### 本周起号突破口",
        breakthrough,
        "",
    ])


def dashboard_calendar_block(partner: dict[str, Any], values: list[str], timeline: dict[str, Any]) -> str:
    today = timeline["today"]
    week_start = timeline["week_start"]
    lines = [
        "## 本周发布 Dashboard",
        "",
        "| 日期 | 星期 | Day | 视频主题 | 主 Hook | 状态 |",
        "|---|---|---:|---|---|---|",
    ]
    for idx, value in enumerate(values, start=1):
        post_date = week_start + dt.timedelta(days=idx - 1)
        hooks = hooks_for_partner(partner, value)
        lines.append(
            f"| {fmt_date(post_date)} | {weekday_zh(post_date)} | {idx} | {value} | {hooks[(idx - 1) % len(hooks)]} | {publish_status(post_date, today)} |"
        )
    lines.extend([
        "",
        "### 状态说明",
        "- **今日发布：** 今天优先拍/发这一支。",
        "- **待发布：** 之后几天的内容，可以先准备。",
        "- **待复盘：** 日期已过，之后可以把视频链接/表现发回 Telegram 做复盘。",
        "",
    ])
    return "\n".join(lines)


def fallback_generate(partner: dict[str, Any]) -> str:
    count = max(1, min(int(partner.get("posts_per_week", 7)), 14))
    platforms = "、".join(partner.get("platforms", []))
    timeline = partner_timeline(partner, count)
    week_no = timeline["current_week"]
    # Rotate values by partner week so Week 2/3 do not repeat Week 1 exactly.
    values = [VALUE_ROTATION[(week_no - 1 + i) % len(VALUE_ROTATION)] for i in range(count)]

    if partner.get("audience_perspective") == "direct_elder_parent":
        direction_text = f"Week {week_no} 用「{partner.get('ip_role', 'IP角色')}视角」讲给阿公阿嬷和父母本人听。重点不是叫孩子理解长辈，而是让长辈/父母自己听了觉得：对，我就是这样，我嘴上说不用，其实心里有感觉。"
        interaction_text = "这套内容适合测试长辈/父母共鸣型起号，因为它容易让观众留言：『我也是这样』、『我每次都说不用』、『做父母的真的会这样』。"
    else:
        direction_text = f"Week {week_no} 先用「{partner.get('relationship', '角色关系')}」里的真实生活细节来建立 IP 记忆点。重点不是硬讲道理，而是把目标受众熟悉、但平时不会特别说出口的情绪讲出来。"
        interaction_text = "这套内容适合测试共鸣型起号，因为它容易让观众留言、分享给同类受众，或 tag 身边的人。"

    parts = [
        f"# {partner.get('name')}｜IP 起号 Dashboard",
        "",
        "## 当前进度",
        "",
        f"- **伙伴开始日期：** {fmt_date(timeline['start_date'])}  ",
        f"- **内容开始日期：** {fmt_date(timeline['content_start_date'])}  ",
        f"- **当前周数：** Week {week_no}  ",
        f"- **本周日期：** {fmt_date(timeline['week_start'])} - {fmt_date(timeline['week_end'])}  ",
        f"- **今日：** {fmt_date(timeline['today'])}  ",
        "- **Dashboard 规则：** 若已设定内容开始日期，Week 1 Day 1 会从内容开始日期算起；之后每 7 天自动进入下一周。  ",
        "",
        "## IP 档案",
        "",
        f"**IP 角色：** {partner.get('ip_role', '')}  ",
        f"**目标受众：** {partner.get('audience', '')}  ",
        f"**角色关系：** {partner.get('relationship', '')}  ",
        f"**主要平台：** {platforms}  ",
        f"**内容语气：** {partner.get('tone', '')}  ",
        "",
        platform_analysis_block(partner),
        "",
        account_diagnosis_block(partner),
        "",
        "## 本周起号方向",
        "",
        direction_text,
        "",
        interaction_text,
        "",
        dashboard_calendar_block(partner, values, timeline),
        "",
        "## 本周价值观轮换",
        "",
    ]
    for i, value in enumerate(values, start=1):
        post_date = timeline["week_start"] + dt.timedelta(days=i - 1)
        parts.append(f"- Day {i}（{fmt_date(post_date)}）：{value}")
    parts.append("")
    parts.append("## 快速进入每日文案")
    parts.append("")
    for day in range(1, count + 1):
        post_date = timeline["week_start"] + dt.timedelta(days=day - 1)
        parts.append(f"- [Day {day}｜{fmt_date(post_date)}](#day-{day})")
    parts.append("")
    parts.append("## 每天完整文案")
    parts.append("")
    for day, value in enumerate(values, start=1):
        parts.append(fallback_post(partner, day, value))
    parts.append("\n---\n\n## 下周自动更新说明")
    parts.append(f"到 {fmt_date(timeline['week_start'] + dt.timedelta(days=7))}，系统会自动进入 Week {week_no + 1}，同一个 Dashboard 链接会更新成下一周内容。")
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


def partner_hero_html(partner: dict[str, Any] | None) -> str:
    if not partner:
        return ""
    name = html.escape(str(partner.get("name") or "IP Partner"))
    role = html.escape(str(partner.get("ip_role") or "IP 角色"))
    audience = html.escape(str(partner.get("audience") or "目标受众"))
    relationship = html.escape(str(partner.get("relationship") or "角色关系"))
    avatar_url = str(partner.get("avatar_url") or "").strip()
    initial = html.escape((str(partner.get("name") or "IP").strip() or "IP")[0])
    if avatar_url:
        avatar = f'<img src="{html.escape(avatar_url)}" alt="{name} avatar">'
    else:
        avatar = f'<span>{initial}</span>'

    labels = {
        "facebook": "f",
        "instagram": "◎",
        "tiktok": "♪",
        "wechat": "微",
        "xiaohongshu": "小红书",
    }
    links = partner.get("platform_links", {}) or {}
    platform_html = []
    for key, label in labels.items():
        if links.get(key):
            platform_html.append(f'<span class="platform-logo platform-{key}">{label}</span>')
    platforms = "".join(platform_html) or '<span class="platform-logo muted-logo">平台待补</span>'

    return f"""
<section class="hero-card">
  <div class="hero-glow"></div>
  <div class="hero-topline">IP 起号自动化 Dashboard</div>
  <div class="hero-content">
    <div class="avatar">{avatar}</div>
    <div class="hero-main">
      <h1>{name}</h1>
      <p class="hero-role">{role}</p>
      <p class="hero-audience">讲给：{audience}</p>
      <p class="hero-relation">{relationship}</p>
      <div class="platform-row" aria-label="connected platforms">{platforms}</div>
      <div class="hero-actions">
        <a class="primary-cta" href="content/">查看文案</a>
        <a class="secondary-cta" href="analysis/">账号分析</a>
      </div>
    </div>
  </div>
</section>
"""


def markdown_to_html(markdown: str, title: str, partner: dict[str, Any] | None = None) -> str:
    """Small self-contained renderer for the dashboard pages.

    Keeps the repo dependency-light while making GitHub Pages serve real HTML.
    """
    css = """
    :root { --mint:#63e6be; --mint2:#9ff5dc; --mint-dark:#0f766e; --ink:#0b0f14; --charcoal:#111827; --gray:#6b7280; --soft:#eefcf7; --line:#d9eee7; --card:#ffffff; }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.65; max-width: 1180px; margin: 0 auto; padding: 24px 16px 80px; color: #1f2937; background: radial-gradient(circle at top left, rgba(99,230,190,.28) 0, transparent 34%), linear-gradient(180deg, #f8fffc 0%, #f4f7f6 46%, #ffffff 100%); }
    .hero-card { min-height: 86vh; display:flex; flex-direction:column; justify-content:center; padding:38px; border-radius:34px; background:linear-gradient(135deg,#070a0f 0%,#111827 48%,#1f2937 100%); color:#fff; box-shadow:0 28px 80px rgba(6,78,59,.22); margin-bottom:30px; position:relative; overflow:hidden; border:1px solid rgba(99,230,190,.18); }
    .hero-glow { position:absolute; inset:auto -120px -120px auto; width:360px; height:360px; background:radial-gradient(circle, rgba(99,230,190,.42), transparent 68%); border-radius:999px; filter:blur(4px); }
    .hero-card:before { content:""; position:absolute; inset:0; background:linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px), linear-gradient(180deg, rgba(255,255,255,.045) 1px, transparent 1px); background-size:42px 42px; mask-image:linear-gradient(180deg,#000,transparent 76%); }
    .hero-topline { position:relative; z-index:1; color:var(--mint2); font-size:.86rem; letter-spacing:.12em; text-transform:uppercase; font-weight:800; margin-bottom:18px; }
    .hero-content { position:relative; z-index:1; display:flex; align-items:center; gap:28px; }
    .avatar { width:128px; height:128px; border-radius:36px; background:linear-gradient(135deg, rgba(99,230,190,.28), rgba(255,255,255,.08)); display:flex; align-items:center; justify-content:center; flex:0 0 auto; border:1px solid rgba(159,245,220,.38); overflow:hidden; font-size:3.5rem; font-weight:900; box-shadow:0 18px 44px rgba(0,0,0,.28); }
    .avatar img { width:100%; height:100%; object-fit:cover; }
    .hero-main h1 { color:#fff; border:0; padding:0; margin:.15rem 0 .2rem; font-size:clamp(2.1rem,5vw,4.4rem); letter-spacing:-.06em; line-height:1; }
    .hero-role { display:inline-block; margin:.35rem 0 .7rem; color:#06251e; background:var(--mint); font-weight:900; padding:7px 14px; border-radius:999px; }
    .hero-audience { color:#d1fae5; font-size:1.08rem; margin:.2rem 0; }
    .hero-relation { color:#a7f3d0; margin:.25rem 0 1rem; max-width:780px; }
    .platform-row { display:flex; flex-wrap:wrap; gap:9px; margin:16px 0 22px; }
    .platform-logo { min-width:40px; height:40px; padding:0 12px; border-radius:14px; display:inline-flex; align-items:center; justify-content:center; background:rgba(255,255,255,.08); border:1px solid rgba(159,245,220,.26); color:#ecfdf5; font-weight:900; box-shadow:inset 0 1px 0 rgba(255,255,255,.08); }
    .platform-facebook { color:#93c5fd; } .platform-instagram { color:#f9a8d4; } .platform-tiktok { color:#67e8f9; } .platform-wechat { color:#86efac; } .platform-xiaohongshu { color:#fecaca; font-size:.78rem; } .muted-logo { color:#9ca3af; }
    .hero-actions { display:flex; flex-wrap:wrap; gap:12px; }
    .primary-cta, .secondary-cta { display:inline-flex; align-items:center; justify-content:center; text-decoration:none; border-radius:999px; font-weight:950; padding:13px 22px; transition:.16s ease; }
    .primary-cta { background:var(--mint); color:#052e2b; box-shadow:0 18px 45px rgba(99,230,190,.26); }
    .primary-cta:after { content:" →"; margin-left:4px; }
    .secondary-cta { color:#d1fae5; background:rgba(255,255,255,.06); border:1px solid rgba(159,245,220,.22); }
    .primary-cta:hover, .secondary-cta:hover { transform:translateY(-2px); }
    body > h1 { display:none; }
    h1, h2, h3, h4 { color: var(--ink); line-height: 1.25; }
    h2 { margin-top: 34px; border-left: 6px solid var(--mint); padding: 12px 14px; background: rgba(238,252,247,.82); border-radius: 0 16px 16px 0; }
    h2[id^="day-"] { background:linear-gradient(90deg,#d9fff2,#fff); border-radius:18px; border-left:0; box-shadow:0 10px 30px rgba(15,118,110,.10); }
    h3 { margin-top: 24px; }
    p, li { font-size:1.02rem; }
    table { border-collapse: collapse; width: 100%; background: white; margin: 14px 0 22px; box-shadow: 0 12px 34px rgba(15,23,42,.08); border-radius:18px; overflow:hidden; }
    th, td { border: 1px solid var(--line); padding: 12px 14px; vertical-align: top; }
    th { background: #eafff7; text-align: center; color:#075e54; }
    tr:nth-child(even) td { background: #f8fffc; }
    code, pre { background: #f3f4f6; border-radius: 6px; }
    pre { padding: 14px; overflow-x: auto; }
    blockquote { border-left: 4px solid #ddd; margin-left: 0; padding-left: 14px; color: #555; }
    hr { border: 0; border-top: 1px solid #e5e7eb; margin: 34px 0; }
    a { color: #0f766e; }
    #content-dashboard { scroll-margin-top:18px; }
    a[href^="#day-"] { display:inline-flex; align-items:center; text-decoration:none; color:#064e3b; background:#eafff7; border:1px solid #b6f4de; padding:11px 16px; border-radius:999px; font-weight:900; box-shadow:0 8px 20px rgba(15,118,110,.10); transition:.15s ease; }
    a[href^="#day-"]:hover { transform:translateY(-1px); background:#d9fff2; }
    details.day-card { background:#fff; border:1px solid #b6f4de; border-radius:22px; margin:18px 0; box-shadow:0 12px 30px rgba(15,23,42,.06); overflow:hidden; }
    details.day-card summary { cursor:pointer; padding:17px 20px; font-weight:950; color:#064e3b; background:linear-gradient(90deg,#d9fff2,#f8fffc); list-style:none; }
    details.day-card summary::-webkit-details-marker { display:none; }
    details.day-card summary:after { content:"打开 / 收起"; float:right; font-size:.82rem; color:#075e54; background:#fff; padding:3px 9px; border-radius:999px; border:1px solid #b6f4de; }
    .day-body { padding:4px 18px 22px; }
    li:has(a[href^="#day-"]) { display:inline-block; margin:6px 6px 6px 0; }
    ul:has(a[href^="#day-"]) { padding-left:0; }
    details.account-notes { background:rgba(255,255,255,.72); border:1px solid var(--line); border-radius:20px; margin:18px 0 28px; box-shadow:0 10px 28px rgba(15,23,42,.05); overflow:hidden; }
    details.account-notes summary { cursor:pointer; font-weight:950; color:#111827; padding:16px 18px; background:#f8fffc; }
    .account-notes-body { padding:0 18px 18px; }
    .meta { color: var(--gray); font-size: .95rem; }
    @media (max-width: 760px) { body { padding:14px 10px 70px; } .hero-card { min-height:76vh; padding:24px; border-radius:28px; } .hero-content { align-items:flex-start; gap:16px; } .avatar { width:84px; height:84px; border-radius:24px; font-size:2.3rem; } .platform-logo { height:36px; min-width:36px; border-radius:12px; } table { font-size:.88rem; display:block; overflow-x:auto; } th,td { padding:9px; } }
    """
    def inline(text: str) -> str:
        safe = html.escape(text)
        import re
        safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
        safe = re.sub(r"`(.+?)`", r"<code>\1</code>", safe)
        safe = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', safe)
        url_re = re.compile(r"(?<!href=\")(https?://[^\s<]+)")
        safe = url_re.sub(r'<a href="\1">\1</a>', safe)
        return safe

    out: list[str] = []
    in_ul = False
    in_table = False
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if in_table and not (stripped.startswith("|") and stripped.endswith("|")):
            out.append("</tbody></table>")
            in_table = False
        if in_ul and not stripped.startswith("- "):
            out.append("</ul>")
            in_ul = False

        if not stripped:
            i += 1
            continue
        if stripped == "---":
            out.append("<hr>")
        elif stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            is_sep = all(set(c) <= {"-", ":"} for c in cells)
            if not in_table and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                out.append("<table><tbody>")
                in_table = True
            if not is_sep:
                tag = "th" if i + 1 < len(lines) and set("".join([c.strip() for c in lines[i + 1].strip().strip("|").split("|")])) <= {"-", ":"} else "td"
                out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
        elif stripped.startswith("#### "):
            out.append(f"<h4>{inline(stripped[5:])}</h4>")
        elif stripped.startswith("### "):
            out.append(f"<h3>{inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            heading_text = stripped[3:]
            import re
            m = re.match(r"Day\s+(\d+)", heading_text)
            if m:
                heading_id = f' id="day-{m.group(1)}"'
            elif heading_text == "本周发布 Dashboard":
                heading_id = ' id="content-dashboard"'
            elif heading_text == "当前进度":
                heading_id = ' id="account-notes"'
            else:
                heading_id = ""
            out.append(f"<h2{heading_id}>{inline(heading_text)}</h2>")
        elif stripped.startswith("# "):
            out.append(f"<h1>{inline(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(stripped[2:])}</li>")
        else:
            out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    if in_ul:
        out.append("</ul>")
    if in_table:
        out.append("</tbody></table>")

    day_script = """
<script>
document.addEventListener('DOMContentLoaded', () => {
  const accountStart = document.querySelector('#account-notes');
  const contentStart = document.querySelector('#content-dashboard');
  if (accountStart && contentStart) {
    const details = document.createElement('details');
    details.className = 'account-notes';
    details.id = 'account-notes-panel';
    const summary = document.createElement('summary');
    summary.textContent = '查看账号分析 / IP 档案';
    const body = document.createElement('div');
    body.className = 'account-notes-body';
    accountStart.parentNode.insertBefore(details, accountStart);
    details.appendChild(summary);
    details.appendChild(body);
    let node = accountStart;
    while (node && node !== contentStart) {
      const next = node.nextSibling;
      body.appendChild(node);
      node = next;
    }
  }

  const headings = Array.from(document.querySelectorAll('h2[id^="day-"]'));
  headings.forEach((heading, index) => {
    const details = document.createElement('details');
    details.className = 'day-card';
    details.id = heading.id;
    if (window.location.hash === `#${details.id}`) details.open = true;

    const summary = document.createElement('summary');
    summary.textContent = heading.textContent;
    const body = document.createElement('div');
    body.className = 'day-body';

    let node = heading.nextSibling;
    heading.replaceWith(details);
    details.appendChild(summary);
    details.appendChild(body);

    while (node) {
      const next = node.nextSibling;
      if (node.nodeType === 1 && node.matches && node.matches('h2[id^="day-"], h2')) {
        const text = node.textContent || '';
        if (node.matches('h2[id^="day-"]') || text.includes('下周自动更新说明')) break;
      }
      body.appendChild(node);
      node = next;
    }
  });

  document.querySelectorAll('a[href^="#day-"]').forEach(link => {
    link.addEventListener('click', event => {
      event.preventDefault();
      const target = document.querySelector(link.getAttribute('href'));
      if (!target) return;
      document.querySelectorAll('details.day-card').forEach(card => card.open = false);
      target.open = true;
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
});
</script>
"""
    return f"""<!doctype html>
<html lang=\"zh-Hans\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{html.escape(title)}</title>
<style>{css}</style>
</head>
<body>
{partner_hero_html(partner)}
{chr(10).join(out)}
{day_script}
</body>
</html>
"""


def partner_slug(partner: dict[str, Any]) -> str:
    return str(partner.get("telegram_user_id") or partner.get("name")).replace(" ", "-")


def split_dashboard_content(content: str) -> tuple[str, str]:
    marker = "\n## 本周发布 Dashboard"
    if marker not in content:
        return content, content
    analysis_md, content_md = content.split(marker, 1)
    return analysis_md.strip() + "\n", "## 本周发布 Dashboard" + content_md


def write_partner_page(partner: dict[str, Any], content: str) -> Path:
    out_dir = DOCS_DIR / "partners" / partner_slug(partner)
    out_dir.mkdir(parents=True, exist_ok=True)

    analysis_md, content_md = split_dashboard_content(content)
    partner_name = partner.get("name")

    # Page 1: landing page only. No long scrolling report here.
    landing_md = "\n".join([
        f"# {partner_name}｜IP 起号 Dashboard",
        "",
        "这个页面是你的 IP 起号入口。按 **查看文案** 进入本周 Day 1–Day 7 内容；按 **账号分析** 查看诊断资料。",
        "",
    ])
    out_path = out_dir / "index.md"
    out_path.write_text(landing_md, encoding="utf-8")
    (out_dir / "index.html").write_text(
        markdown_to_html(landing_md, f"{partner_name}｜IP 起号 Dashboard", partner),
        encoding="utf-8",
    )

    # Page 2: content dashboard + Day 1–7 copy.
    content_dir = out_dir / "content"
    content_dir.mkdir(exist_ok=True)
    content_page = "\n".join([
        f"# {partner_name}｜本周文案",
        "",
        "[← 回 Dashboard 首页](../) · [查看账号分析](../analysis/)",
        "",
        content_md.strip(),
        "",
    ])
    (content_dir / "index.md").write_text(content_page, encoding="utf-8")
    (content_dir / "index.html").write_text(
        markdown_to_html(content_page, f"{partner_name}｜本周文案"),
        encoding="utf-8",
    )

    # Page 3: account analysis / IP profile.
    analysis_dir = out_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    analysis_page = "\n".join([
        f"# {partner_name}｜账号分析",
        "",
        "[← 回 Dashboard 首页](../) · [查看本周文案](../content/)",
        "",
        analysis_md.strip(),
        "",
    ])
    (analysis_dir / "index.md").write_text(analysis_page, encoding="utf-8")
    (analysis_dir / "index.html").write_text(
        markdown_to_html(analysis_page, f"{partner_name}｜账号分析"),
        encoding="utf-8",
    )
    return out_path


def write_home_index(generated: list[tuple[dict[str, Any], Path]]) -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# IP 起号内容周报系统",
        "",
        f"最后更新：{now}",
        "",
        "每个伙伴都有自己的独立页面。",
        "",
        "为了避免不同伙伴的 IP 分析、平台资料和文案混在一起，这个首页不会公开列出所有伙伴链接。",
        "",
        "伙伴请使用系统发送给你的专属链接查看自己的周报。",
        "",
        "示例链接格式：",
        "",
        "```text",
        "https://magicliew.github.io/ip-content-telegram-github/partners/你的伙伴ID/",
        "```",
        "",
        "## 目前系统状态",
        "",
        f"- 已建立独立伙伴页面数量：{len(generated)}",
        "- 每个伙伴页面独立生成，不会混合其他伙伴内容",
        "- 每个伙伴页面包含自己的平台分析、起号方向、每日 Hook、口播、Caption、Hashtag",
    ]
    content = "\n".join(lines) + "\n"
    (DOCS_DIR / "index.md").write_text(content, encoding="utf-8")
    (DOCS_DIR / "index.html").write_text(markdown_to_html(content, "IP 起号 Dashboard 系统"), encoding="utf-8")


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
