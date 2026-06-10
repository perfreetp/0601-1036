import click
from pathlib import Path

from ..config import (
    find_project_root,
    load_config,
    save_config,
    load_articles,
    load_themes,
    get_project_dirs,
    SIZE_PRESETS,
    save_history,
)
from ..composer import compose_article_images
from ..utils import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    timestamp,
    slugify,
)


@click.command()
@click.option("--theme", "-t", help="使用的主题（默认使用当前主题）")
@click.option("--articles", "-a", help="指定文章 ID 或序号，逗号分隔（如 1,3,5）")
@click.option("--sizes", "-s", help="输出尺寸预设，逗号分隔（如 wechat,weibo,xiaohongshu）")
@click.option("--all-sizes", is_flag=True, help="输出所有预设尺寸")
@click.option("--no-quote", is_flag=True, help="不生成引语卡片")
@click.option("--numbering/--no-numbering", default=True, help="添加自动编号")
@click.option("--overlay-position",
              type=click.Choice(["top", "center", "bottom"]),
              default="bottom",
              help="文字遮罩位置")
@click.option("--dry-run", "-n", is_flag=True, help="预览要生成的内容，不实际生成")
def compose(theme, articles, sizes, all_sizes, no_quote, numbering, overlay_position, dry_run):
    """
    批量合成封面图和引语卡片。

    根据当前主题和文章内容，为每篇文章生成多种尺寸的配图。
    """
    print_header("批量合成配图")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    articles_list = load_articles(project_root)
    themes = load_themes(project_root)
    dirs = get_project_dirs(project_root)

    if not articles_list:
        print_error("没有文章数据，请先使用 'designflow import titles' 导入文章")
        raise click.Abort()

    theme_name = theme or config.current_theme or "default"
    if theme_name not in themes:
        print_error(f"主题 '{theme_name}' 不存在")
        available = ", ".join(themes.keys())
        print_info(f"可用主题: {available}")
        raise click.Abort()

    theme_obj = themes[theme_name]

    if articles:
        try:
            selected_ids = [a.strip() for a in articles.split(",")]
            filtered = []
            for art in articles_list:
                if str(art.order) in selected_ids or art.id in selected_ids or art.title in selected_ids:
                    filtered.append(art)
            articles_list = filtered
        except Exception:
            pass

    if not articles_list:
        print_error("没有匹配的文章")
        raise click.Abort()

    if all_sizes:
        selected_presets = list(SIZE_PRESETS.values())
    elif sizes:
        size_list = [s.strip() for s in sizes.split(",")]
        selected_presets = []
        for s in size_list:
            if s in SIZE_PRESETS:
                selected_presets.append(SIZE_PRESETS[s])
            else:
                print_warning(f"未知尺寸预设: {s}")
    else:
        selected_presets = [
            SIZE_PRESETS["wechat"],
            SIZE_PRESETS["weibo"],
            SIZE_PRESETS["xiaohongshu"],
            SIZE_PRESETS["cover"],
        ]

    if not selected_presets:
        print_error("没有有效的尺寸预设")
        raise click.Abort()

    print_info(f"主题: {theme_obj.display_name or theme_name}")
    print_info(f"文章: {len(articles_list)} 篇")
    print_info(f"尺寸: {', '.join([p.name for p in selected_presets])}")
    print_info(f"引语卡片: {'否' if no_quote else '是'}")
    print_info(f"自动编号: {'是' if numbering else '否'}")

    if dry_run:
        print()
        print_info("预览生成计划:")
        rows = []
        for i, art in enumerate(articles_list, 1):
            output_count = len(selected_presets) * (1 if no_quote else 2)
            rows.append([
                str(i),
                art.title[:50] + ("..." if len(art.title) > 50 else ""),
                str(output_count),
            ])
        print_table(["#", "标题", "将生成"], rows)
        total = len(articles_list) * len(selected_presets) * (1 if no_quote else 2)
        print_info(f"总计将生成 {total} 张图片")
        return

    total_generated = []
    output_dir = dirs["composed"]

    with click.progressbar(articles_list, label="合成中", show_pos=True) as bar:
        for i, article in enumerate(bar, 1):
            try:
                num_tuple = (i, len(articles_list)) if numbering else None
                generated = compose_article_images(
                    article=article,
                    theme=theme_obj,
                    presets=selected_presets,
                    source_dir=dirs["source_images"],
                    output_dir=output_dir,
                    fonts_dir=dirs["fonts"],
                    include_quote=not no_quote,
                    numbering=num_tuple,
                    overlay_position=overlay_position,
                )
                total_generated.extend(generated)
            except Exception as e:
                print_error(f"生成失败 '{article.title}': {str(e)}")

    config.updated_at = timestamp()
    save_config(project_root, config)

    history_entry = {
        "action": "compose",
        "timestamp": timestamp(),
        "theme": theme_name,
        "articles_count": len(articles_list),
        "sizes": [p.name for p in selected_presets],
        "generated_count": len(total_generated),
    }
    save_history(project_root, history_entry)

    print_success(f"成功生成 {len(total_generated)} 张图片")
    print_info(f"输出目录: {output_dir}")

    if total_generated:
        rows = []
        type_counts = {}
        preset_counts = {}
        for g in total_generated:
            type_counts[g["type"]] = type_counts.get(g["type"], 0) + 1
            preset_counts[g["preset"]] = preset_counts.get(g["preset"], 0) + 1

        summary_rows = [[k, str(v)] for k, v in type_counts.items()]
        print_table(["类型", "数量"], summary_rows, "按类型统计")

        preset_rows = [[k, str(v)] for k, v in preset_counts.items()]
        print_table(["尺寸", "数量"], preset_rows, "按尺寸统计")

        sample_rows = []
        for g in total_generated[:5]:
            art = next((a for a in articles_list if a.id == g["article_id"]), None)
            title = art.title[:30] if art else "未知"
            sample_rows.append([
                title + ("..." if art and len(art.title) > 30 else ""),
                g["preset"],
                g["type"],
                Path(g["path"]).name,
            ])
        print_table(["文章", "尺寸", "类型", "文件名"], sample_rows, "生成的文件 (前5个)")
