from __future__ import annotations

PERSONA_POLICY = {
    "allowed": (
        "historical-profile-based simulation",
        "evidence-backed style summary",
        "historical preference analysis",
    ),
    "forbidden": (
        "claiming to be a real KOL",
        "claiming real-time viewpoint",
        "fabricating unsaid statements",
        "direct buy/sell advice",
    ),
}

INVESTMENT_ADVICE_POLICY = {
    "allowed": (
        "historical analysis",
        "risk summary",
        "scenario analysis",
        "educational explanation",
    ),
    "forbidden": (
        "buy now",
        "sell now",
        "open leverage",
        "personalized investment advice",
        "guaranteed returns",
    ),
}

EVIDENCE_POLICY = {
    "allowed": (
        "use existing evidence",
        "state confidence",
        "admit evidence gaps",
    ),
    "forbidden": (
        "fabricated source",
        "fabricated evidence",
        "private raw message export",
        "treat mock data as private live source",
    ),
}

ADMIN_POLICY = {
    "allowed": ("manager-admin in private admin context",),
    "forbidden": (
        "public manager-agent admin mutation",
        "public context admin tools",
        "non-admin maintenance writes",
    ),
}

ADMIN_ONLY_PHRASES = (
    "import pending",
    "process pending",
    "refresh profile",
    "update soul",
    "disable kol",
    "archive kol",
    "promote kol",
    "导入数据",
    "导入待处理",
    "刷新画像",
    "更新 soul",
    "停用 kol",
    "归档 kol",
)

INVESTMENT_ADVICE_PHRASES = (
    "buy now",
    "sell now",
    "should i buy",
    "should i sell",
    "should buy",
    "should sell",
    "you should buy",
    "you should sell",
    "go long",
    "go short",
    "open leverage",
    "梭哈",
    "该买",
    "该卖",
    "要不要买",
    "要不要卖",
    "买入",
    "卖出",
    "开杠杆",
    "开多",
    "开空",
)

IMPERSONATION_PHRASES = (
    "i am kol",
    "pretend to be",
    "impersonate",
    "我是 kol",
    "我是某 kol",
    "冒充",
)

FABRICATED_EVIDENCE_PHRASES = (
    "make up evidence",
    "fabricate evidence",
    "invent evidence",
    "invent a source",
    "fake source",
    "编造证据",
    "伪造证据",
    "虚构来源",
    "私密消息说",
    "private source says",
)

PRIVATE_EXPORT_PHRASES = (
    "raw private",
    "export private",
    "private raw messages",
    "导出原始消息",
    "私密频道原始消息",
)

REALTIME_CLAIM_PHRASES = (
    "real-time view",
    "current live opinion",
    "当前实时观点",
    "他现在的观点",
    "这是他现在的观点",
)
