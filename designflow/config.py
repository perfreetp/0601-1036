import os
import json
import yaml
import copy
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field


PROJECT_CONFIG_FILENAME = "designflow.yaml"
ARTICLES_FILENAME = "articles.yaml"
THEMES_FILENAME = "themes.yaml"
HISTORY_FILENAME = "history.yaml"
PROFILES_FILENAME = "profiles.yaml"
FAILED_TASKS_FILENAME = "failed_tasks.yaml"


@dataclass
class ProjectConfig:
    name: str = "untitled-project"
    issue: str = "001"
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    current_theme: str = "default"
    author: str = ""
    signature: str = ""
    watermark: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class Article:
    id: str
    title: str
    subtitle: str = ""
    summary: str = ""
    quote: str = ""
    author: str = ""
    keywords: list = field(default_factory=list)
    image_path: str = ""
    order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Article":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class Theme:
    name: str
    display_name: str = ""
    description: str = ""
    palette: Dict[str, str] = field(default_factory=dict)
    fonts: Dict[str, str] = field(default_factory=dict)
    layout: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Theme":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class PublishProfile:
    name: str
    display_name: str = ""
    description: str = ""
    theme: str = "default"
    sizes: list = field(default_factory=lambda: ["wechat", "weibo", "xiaohongshu"])
    include_quote: bool = True
    numbering: bool = True
    overlay_position: str = "bottom"
    watermark_text: str = ""
    watermark_position: str = "bottom-right"
    watermark_opacity: float = 0.6
    signature_text: str = ""
    signature_author: str = ""
    export_zip: bool = True
    export_share_formats: list = field(default_factory=lambda: ["markdown"])
    platforms: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PublishProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class SizePreset:
    name: str
    width: int
    height: int
    platform: str = ""
    description: str = ""


SIZE_PRESETS: Dict[str, SizePreset] = {
    "wechat": SizePreset("wechat", 1280, 720, "微信公众号", "微信公众号封面图"),
    "wechat-vertical": SizePreset("wechat-vertical", 1080, 1920, "微信", "微信竖版长图"),
    "weibo": SizePreset("weibo", 1080, 1080, "微博", "微博正方形配图"),
    "xiaohongshu": SizePreset("xiaohongshu", 1080, 1440, "小红书", "小红书3:4竖图"),
    "xiaohongshu-1-1": SizePreset("xiaohongshu-1-1", 1080, 1080, "小红书", "小红书1:1方图"),
    "douyin": SizePreset("douyin", 1080, 1920, "抖音", "抖音竖版视频封面"),
    "bilibili": SizePreset("bilibili", 1146, 717, "B站", "B站视频封面"),
    "zhihu": SizePreset("zhihu", 1920, 1080, "知乎", "知乎文章封面"),
    "twitter": SizePreset("twitter", 1600, 900, "Twitter/X", "Twitter/X 配图"),
    "linkedin": SizePreset("linkedin", 1200, 628, "LinkedIn", "LinkedIn 分享图"),
    "cover": SizePreset("cover", 1920, 1080, "通用", "通用横版封面"),
    "square": SizePreset("square", 1080, 1080, "通用", "通用正方形"),
    "story": SizePreset("story", 1080, 1920, "通用", "通用竖版故事"),
    "card": SizePreset("card", 800, 600, "通用", "引语卡片"),
}


DEFAULT_THEMES: Dict[str, Theme] = {
    "default": Theme(
        name="default",
        display_name="默认简约",
        description="简洁大气的现代风格，适合大多数内容",
        palette={
            "primary": "#2D3436",
            "secondary": "#636E72",
            "accent": "#0984E3",
            "background": "#FFFFFF",
            "text": "#2D3436",
            "text_light": "#FFFFFF",
        },
        fonts={
            "title": "Microsoft YaHei Bold",
            "subtitle": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "quote": "Georgia Italic",
        },
        layout={
            "title_size": 72,
            "subtitle_size": 36,
            "padding": 60,
            "overlay_opacity": 0.3,
        },
    ),
    "elegant": Theme(
        name="elegant",
        display_name="典雅商务",
        description="优雅精致的商务风格，适合专业内容",
        palette={
            "primary": "#1E272E",
            "secondary": "#485460",
            "accent": "#C0392B",
            "background": "#FAFAFA",
            "text": "#1E272E",
            "text_light": "#FAFAFA",
        },
        fonts={
            "title": "SimHei Bold",
            "subtitle": "SimHei",
            "body": "SimSun",
            "quote": "KaiTi",
        },
        layout={
            "title_size": 64,
            "subtitle_size": 32,
            "padding": 80,
            "overlay_opacity": 0.4,
        },
    ),
    "vibrant": Theme(
        name="vibrant",
        display_name="活力亮色",
        description="充满活力的渐变色彩，适合年轻化内容",
        palette={
            "primary": "#6C5CE7",
            "secondary": "#A29BFE",
            "accent": "#FD79A8",
            "background": "#FDCB6E",
            "text": "#2D3436",
            "text_light": "#FFFFFF",
        },
        fonts={
            "title": "Microsoft YaHei Bold",
            "subtitle": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "quote": "Comic Sans MS",
        },
        layout={
            "title_size": 80,
            "subtitle_size": 40,
            "padding": 50,
            "overlay_opacity": 0.2,
        },
    ),
    "dark": Theme(
        name="dark",
        display_name="暗黑模式",
        description="深色背景搭配亮色文字，适合科技内容",
        palette={
            "primary": "#00B894",
            "secondary": "#55EFC4",
            "accent": "#E17055",
            "background": "#2D3436",
            "text": "#DFE6E9",
            "text_light": "#FFFFFF",
        },
        fonts={
            "title": "Microsoft YaHei Bold",
            "subtitle": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "quote": "Consolas",
        },
        layout={
            "title_size": 72,
            "subtitle_size": 36,
            "padding": 60,
            "overlay_opacity": 0.6,
        },
    ),
    "warm": Theme(
        name="warm",
        display_name="温暖治愈",
        description="暖色调搭配，适合生活方式类内容",
        palette={
            "primary": "#E17055",
            "secondary": "#FDCB6E",
            "accent": "#00B894",
            "background": "#FFF5E6",
            "text": "#2D3436",
            "text_light": "#FFFFFF",
        },
        fonts={
            "title": "KaiTi",
            "subtitle": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "quote": "KaiTi",
        },
        layout={
            "title_size": 68,
            "subtitle_size": 34,
            "padding": 70,
            "overlay_opacity": 0.25,
        },
    ),
}


def is_project_directory(path: Path) -> bool:
    config_path = path / PROJECT_CONFIG_FILENAME
    return config_path.exists() and config_path.is_file()


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    if start_path is None:
        start_path = Path.cwd()
    current = start_path.resolve()
    while current != current.parent:
        if is_project_directory(current):
            return current
        current = current.parent
    return None


def load_config(project_root: Path) -> ProjectConfig:
    config_path = project_root / PROJECT_CONFIG_FILENAME
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return ProjectConfig.from_dict(data.get("project", {}))


def save_config(project_root: Path, config: ProjectConfig) -> None:
    config_path = project_root / PROJECT_CONFIG_FILENAME
    data = {"project": config.to_dict()}
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def load_articles(project_root: Path) -> list[Article]:
    articles_path = project_root / ARTICLES_FILENAME
    if not articles_path.exists():
        return []
    with open(articles_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    articles_data = data.get("articles", [])
    return [Article.from_dict(a) for a in articles_data]


def save_articles(project_root: Path, articles: list[Article]) -> None:
    articles_path = project_root / ARTICLES_FILENAME
    data = {"articles": [a.to_dict() for a in articles]}
    with open(articles_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def load_themes(project_root: Path) -> Dict[str, Theme]:
    themes_path = project_root / THEMES_FILENAME
    themes = {k: copy.deepcopy(v) for k, v in DEFAULT_THEMES.items()}
    if themes_path.exists():
        with open(themes_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        custom_themes = data.get("themes", [])
        for t in custom_themes:
            theme = Theme.from_dict(t)
            themes[theme.name] = theme
    return themes


def save_themes(project_root: Path, themes: Dict[str, Theme]) -> None:
    themes_path = project_root / THEMES_FILENAME
    themes_to_save = []
    for name, theme_obj in themes.items():
        if name in DEFAULT_THEMES:
            default = DEFAULT_THEMES[name]
            if theme_obj.to_dict() != default.to_dict():
                themes_to_save.append(theme_obj)
        else:
            themes_to_save.append(theme_obj)
    with open(themes_path, "w", encoding="utf-8") as f:
        yaml.dump({"themes": [t.to_dict() for t in themes_to_save]}, f, default_flow_style=False, allow_unicode=True)


def save_history(project_root: Path, entry: Dict[str, Any]) -> None:
    history_path = project_root / HISTORY_FILENAME
    history = []
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            history = yaml.safe_load(f) or []
    history.insert(0, entry)
    history = history[:50]
    with open(history_path, "w", encoding="utf-8") as f:
        yaml.dump(history, f, default_flow_style=False, allow_unicode=True)


def load_history(project_root: Path) -> list:
    history_path = project_root / HISTORY_FILENAME
    if not history_path.exists():
        return []
    with open(history_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def get_project_dirs(project_root: Path) -> Dict[str, Path]:
    dirs = {
        "root": project_root,
        "source_images": project_root / "source" / "images",
        "source_titles": project_root / "source" / "titles",
        "composed": project_root / "output" / "composed",
        "resized": project_root / "output" / "resized",
        "captions": project_root / "output" / "captions",
        "export": project_root / "output" / "export",
        "preview": project_root / "output" / "preview",
        "assets": project_root / "assets",
        "templates": project_root / "assets" / "templates",
        "fonts": project_root / "assets" / "fonts",
    }
    return dirs


def ensure_dirs(dirs: Dict[str, Path]) -> None:
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)


DEFAULT_PROFILES: Dict[str, PublishProfile] = {
    "wechat": PublishProfile(
        name="wechat",
        display_name="微信公众号",
        description="针对微信公众号优化的发布配置",
        theme="default",
        sizes=["wechat", "cover"],
        include_quote=True,
        numbering=False,
        overlay_position="bottom",
        watermark_text="",
        watermark_position="bottom-right",
        watermark_opacity=0.5,
        export_zip=True,
        export_share_formats=["markdown"],
    ),
    "xiaohongshu": PublishProfile(
        name="xiaohongshu",
        display_name="小红书",
        description="针对小红书3:4竖图优化的发布配置",
        theme="warm",
        sizes=["xiaohongshu", "xiaohongshu-1-1"],
        include_quote=True,
        numbering=True,
        overlay_position="center",
        watermark_text="",
        watermark_position="bottom-right",
        watermark_opacity=0.4,
        export_zip=True,
        export_share_formats=["markdown", "txt"],
    ),
    "weibo": PublishProfile(
        name="weibo",
        display_name="微博",
        description="微博正方形配图和长图配置",
        theme="vibrant",
        sizes=["weibo", "wechat-vertical"],
        include_quote=False,
        numbering=False,
        overlay_position="bottom",
        watermark_text="",
        watermark_position="top-right",
        watermark_opacity=0.6,
        export_zip=True,
        export_share_formats=["txt"],
    ),
    "all": PublishProfile(
        name="all",
        display_name="全平台",
        description="所有平台尺寸一次性生成",
        theme="default",
        sizes=["wechat", "weibo", "xiaohongshu", "xiaohongshu-1-1", "douyin", "bilibili", "zhihu", "twitter", "linkedin", "cover"],
        include_quote=True,
        numbering=True,
        overlay_position="bottom",
        watermark_text="",
        watermark_position="bottom-right",
        watermark_opacity=0.6,
        export_zip=True,
        export_share_formats=["markdown", "html", "csv", "json"],
    ),
}


def load_profiles(project_root: Path) -> Dict[str, PublishProfile]:
    profiles_path = project_root / PROFILES_FILENAME
    profiles = {k: copy.deepcopy(v) for k, v in DEFAULT_PROFILES.items()}
    if profiles_path.exists():
        with open(profiles_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        custom_profiles = data.get("profiles", [])
        for p in custom_profiles:
            profile = PublishProfile.from_dict(p)
            profiles[profile.name] = profile
    return profiles


def save_profiles(project_root: Path, profiles: Dict[str, PublishProfile]) -> None:
    profiles_path = project_root / PROFILES_FILENAME
    profiles_to_save = []
    for name, profile in profiles.items():
        if name in DEFAULT_PROFILES:
            default = DEFAULT_PROFILES[name]
            if profile.to_dict() != default.to_dict():
                profiles_to_save.append(profile)
        else:
            profiles_to_save.append(profile)
    with open(profiles_path, "w", encoding="utf-8") as f:
        yaml.dump({"profiles": [p.to_dict() for p in profiles_to_save]}, f, default_flow_style=False, allow_unicode=True)


def load_failed_tasks(project_root: Path) -> list:
    tasks_path = project_root / FAILED_TASKS_FILENAME
    if not tasks_path.exists():
        return []
    with open(tasks_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save_failed_tasks(project_root: Path, failed: list) -> None:
    tasks_path = project_root / FAILED_TASKS_FILENAME
    with open(tasks_path, "w", encoding="utf-8") as f:
        yaml.dump(failed, f, default_flow_style=False, allow_unicode=True)


def clear_failed_tasks(project_root: Path) -> None:
    tasks_path = project_root / FAILED_TASKS_FILENAME
    if tasks_path.exists():
        tasks_path.unlink()
