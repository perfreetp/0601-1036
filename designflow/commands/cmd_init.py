import click
import shutil
from pathlib import Path

from ..config import (
    ProjectConfig,
    save_config,
    save_articles,
    get_project_dirs,
    ensure_dirs,
    is_project_directory,
    PROJECT_CONFIG_FILENAME,
)
from ..utils import print_header, print_success, print_error, print_warning, timestamp, console


@click.command()
@click.argument("name", required=False, default="untitled-project")
@click.option("--issue", "-i", default="001", help="期刊编号，如 001、2024-06")
@click.option("--description", "-d", default="", help="项目描述")
@click.option("--author", "-a", default="", help="作者/编辑名称")
@click.option("--dir", "target_dir", default=".", help="项目根目录（默认为当前目录）")
@click.option("--force", "-f", is_flag=True, help="强制覆盖已存在的项目")
def init(name, issue, description, author, target_dir, force):
    """
    初始化一个新的创意设计项目。

    创建项目目录结构、配置文件和示例文章。
    """
    print_header("初始化项目")

    target_path = Path(target_dir).resolve()
    config_path = target_path / PROJECT_CONFIG_FILENAME

    if is_project_directory(target_path) and not force:
        print_error(f"目录 '{target_path}' 已经是一个 DesignFlow 项目")
        print_warning("使用 --force 选项强制覆盖")
        raise click.Abort()

    try:
        target_path.mkdir(parents=True, exist_ok=True)

        dirs = get_project_dirs(target_path)
        ensure_dirs(dirs)

        config = ProjectConfig(
            name=name,
            issue=issue,
            description=description,
            created_at=timestamp(),
            updated_at=timestamp(),
            author=author,
            current_theme="default",
        )
        save_config(target_path, config)

        sample_articles = _create_sample_articles()
        save_articles(target_path, sample_articles)

        _create_sample_titles_file(dirs["source_titles"])
        _create_sample_image(dirs["source_images"])

        print_success(f"项目 '{name}' (第{issue}期) 已创建成功!")
        console.print()
        console.print(f"[cyan]项目位置:[/cyan] {target_path}")
        console.print()
        console.print("[bold]目录结构:[/bold]")
        for dir_name, dir_path in dirs.items():
            rel_path = dir_path.relative_to(target_path)
            icon = "📁"
            console.print(f"  {icon} {rel_path}/")
        console.print()
        console.print("[bold]下一步操作:[/bold]")
        console.print("  1. [cyan]designflow import titles[/cyan] - 导入文章标题")
        console.print("  2. [cyan]designflow import images[/cyan] - 导入图片素材")
        console.print("  3. [cyan]designflow theme list[/cyan]   - 查看可用主题")
        console.print("  4. [cyan]designflow compose[/cyan]        - 开始批量合成")

    except Exception as e:
        print_error(f"初始化失败: {str(e)}")
        raise click.Abort()


def _create_sample_articles():
    from ..config import Article
    from ..utils import generate_id

    return [
        Article(
            id=generate_id("art_"),
            title="数字时代的创意设计革命",
            subtitle="AI 如何重塑内容创作工作流",
            summary="本文探讨人工智能技术如何改变创意设计行业的工作方式，以及设计师如何适应这一变革。",
            quote="创意不会被替代，而是被赋能。",
            author="张明",
            keywords=["AI", "设计", "创意", "未来"],
            image_path="sample_01.jpg",
            order=1,
        ),
        Article(
            id=generate_id("art_"),
            title="品牌视觉的色彩心理学",
            subtitle="如何用色彩传递品牌情感",
            summary="深入解析色彩在品牌设计中的作用，以及如何利用心理学原理提升视觉传播效果。",
            quote="色彩是品牌与用户情感沟通的第一语言。",
            author="李婷",
            keywords=["品牌", "色彩", "心理学", "视觉"],
            image_path="sample_02.jpg",
            order=2,
        ),
        Article(
            id=generate_id("art_"),
            title="移动端设计的十大趋势",
            subtitle="2024年值得关注的界面设计方向",
            summary="从极简主义到沉浸式体验，盘点今年最具影响力的移动端设计趋势。",
            quote="好的设计是隐形的，它让用户专注于内容本身。",
            author="王浩",
            keywords=["移动端", "UI", "趋势", "2024"],
            image_path="sample_03.jpg",
            order=3,
        ),
    ]


def _create_sample_titles_file(titles_dir: Path):
    sample_file = titles_dir / "titles_sample.txt"
    content = """# 文章标题示例文件
# 格式说明：每行以 key: value 形式填写，title 为必填项
# 支持的字段：title, subtitle, summary, quote, author, keywords, image

title: 数字时代的创意设计革命
subtitle: AI 如何重塑内容创作工作流
summary: 本文探讨人工智能技术如何改变创意设计行业的工作方式。
quote: 创意不会被替代，而是被赋能。
author: 张明
keywords: AI, 设计, 创意, 未来
image: sample_01.jpg

title: 品牌视觉的色彩心理学
subtitle: 如何用色彩传递品牌情感
summary: 深入解析色彩在品牌设计中的作用。
quote: 色彩是品牌与用户情感沟通的第一语言。
author: 李婷
keywords: 品牌, 色彩, 心理学
image: sample_02.jpg
"""
    sample_file.write_text(content, encoding="utf-8")


def _create_sample_image(images_dir: Path):
    try:
        from PIL import Image
        import random

        for i, name in enumerate(["sample_01", "sample_02", "sample_03"], 1):
            img = Image.new("RGB", (1920, 1080))
            pixels = img.load()
            colors = [
                [(100, 150, 200), (50, 75, 150)],
                [(200, 150, 100), (150, 75, 50)],
                [(100, 200, 150), (50, 150, 75)],
            ]
            c1, c2 = colors[i - 1]
            for y in range(1080):
                t = y / 1080
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
                for x in range(1920):
                    noise = random.randint(-10, 10)
                    pixels[x, y] = (
                        max(0, min(255, r + noise)),
                        max(0, min(255, g + noise)),
                        max(0, min(255, b + noise)),
                    )
            img.save(images_dir / f"{name}.jpg", "JPEG", quality=90)
    except Exception:
        pass
