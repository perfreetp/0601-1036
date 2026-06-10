import click
import shutil
from pathlib import Path

from ..config import (
    find_project_root,
    load_config,
    save_config,
    load_articles,
    save_articles,
    Article,
    get_project_dirs,
    ensure_dirs,
)
from ..utils import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    parse_title_file,
    parse_csv_titles,
    parse_json_titles,
    find_images,
    get_image_info,
    generate_id,
    timestamp,
    slugify,
    console,
)


@click.group()
def import_cmd():
    """
    导入标题和图片素材。
    """
    pass


@import_cmd.command("titles")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--format", "-f", "fmt", default="auto",
              type=click.Choice(["auto", "txt", "csv", "json"]),
              help="文件格式（自动检测或指定）")
@click.option("--merge", "-m", is_flag=True, help="合并到现有文章列表（默认替换）")
@click.option("--dry-run", "-n", is_flag=True, help="预览导入结果，不实际保存")
def import_titles(file_path, fmt, merge, dry_run):
    """
    从文件导入文章标题和元数据。

    支持 TXT、CSV、JSON 格式。
    """
    print_header("导入文章标题")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目，请先在项目目录中操作或使用 init 命令创建项目")
        raise click.Abort()

    if fmt == "auto":
        ext = file_path.suffix.lower()
        if ext == ".csv":
            fmt = "csv"
        elif ext == ".json":
            fmt = "json"
        else:
            fmt = "txt"

    print_info(f"解析文件: {file_path} (格式: {fmt})")

    try:
        if fmt == "txt":
            imported = parse_title_file(file_path)
        elif fmt == "csv":
            imported = parse_csv_titles(file_path)
        else:
            imported = parse_json_titles(file_path)
    except Exception as e:
        print_error(f"解析文件失败: {str(e)}")
        raise click.Abort()

    if not imported:
        print_warning("未解析到任何文章数据")
        return

    imported_articles = [Article.from_dict(a) for a in imported]

    existing = load_articles(project_root)

    if merge and existing:
        existing_by_id = {a.id: a for a in existing}
        existing_by_title = {a.title: a for a in existing}
        for art in imported_articles:
            if art.id in existing_by_id:
                existing_by_id[art.id] = art
            elif art.title in existing_by_title:
                art.id = existing_by_title[art.title].id
                existing_by_id[art.id] = art
            else:
                art.order = max(existing_by_id.values(), key=lambda x: x.order).order + 1 if existing_by_id else 1
                existing_by_id[art.id] = art
        final_articles = sorted(existing_by_id.values(), key=lambda x: x.order)
    else:
        final_articles = imported_articles
        for i, art in enumerate(final_articles, 1):
            art.order = i

    if dry_run:
        print_info("预览导入结果（不保存）:")
    else:
        save_articles(project_root, final_articles)
        config = load_config(project_root)
        config.updated_at = timestamp()
        save_config(project_root, config)
        shutil.copy2(file_path, project_root / "source" / "titles" / file_path.name)
        print_success(f"成功导入 {len(final_articles)} 篇文章")

    rows = []
    for art in final_articles:
        rows.append([
            str(art.order),
            art.title[:40] + ("..." if len(art.title) > 40 else ""),
            art.subtitle[:30] if art.subtitle else "-",
            art.author or "-",
            art.image_path or "-",
        ])
    print_table(["#", "标题", "副标题", "作者", "配图"], rows, f"文章列表 ({len(final_articles)} 篇)")


@import_cmd.command("images")
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("--recursive/--no-recursive", default=True, help="是否递归扫描子目录")
@click.option("--move", is_flag=True, help="移动文件而不是复制")
@click.option("--pattern", "-p", default="", help="文件名过滤模式（支持通配符）")
def import_images(source, recursive, move, pattern):
    """
    导入图片素材到项目。

    SOURCE 可以是单个图片文件或包含图片的目录。
    """
    print_header("导入图片素材")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    dirs = get_project_dirs(project_root)
    ensure_dirs(dirs)
    target_dir = dirs["source_images"]

    if source.is_file():
        images = [source]
    else:
        images = find_images(source, recursive)
        if pattern:
            import fnmatch
            images = [img for img in images if fnmatch.fnmatch(img.name, pattern)]

    if not images:
        print_warning("未找到任何图片文件")
        return

    print_info(f"找到 {len(images)} 张图片，{'移动' if move else '复制'}到 {target_dir}")

    articles = load_articles(project_root)
    article_titles = {slugify(a.title): a for a in articles}

    imported = []
    skipped = []

    with click.progressbar(images, label="导入中", show_pos=True) as bar:
        for img_path in bar:
            try:
                info = get_image_info(img_path)
                if "error" in info:
                    skipped.append((img_path.name, info["error"]))
                    continue

                target_name = img_path.name
                target_path = target_dir / target_name
                counter = 1
                while target_path.exists():
                    stem = img_path.stem
                    suffix = img_path.suffix
                    target_path = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                if move:
                    shutil.move(str(img_path), str(target_path))
                else:
                    shutil.copy2(str(img_path), str(target_path))

                img_slug = slugify(img_path.stem)
                matched_article = article_titles.get(img_slug)
                if matched_article and not matched_article.image_path:
                    matched_article.image_path = target_path.name

                imported.append({
                    "name": target_path.name,
                    "size": f"{info['width']}x{info['height']}",
                    "kb": info.get("size_kb", 0),
                })

            except Exception as e:
                skipped.append((img_path.name, str(e)))

    if matched_article:
        save_articles(project_root, articles)

    if imported:
        print_success(f"成功导入 {len(imported)} 张图片")
        rows = [[i["name"], i["size"], f"{i['kb']:.1f} KB"] for i in imported[:10]]
        if len(imported) > 10:
            rows.append(["...", "...", f"... 共 {len(imported)} 个文件"])
        print_table(["文件名", "尺寸", "大小"], rows, "已导入的图片")

    if skipped:
        print_warning(f"跳过 {len(skipped)} 个文件:")
        for name, reason in skipped[:5]:
            console.print(f"  • {name}: {reason}")
        if len(skipped) > 5:
            console.print(f"  ... 还有 {len(skipped) - 5} 个文件")


@import_cmd.command("article")
@click.option("--title", "-t", required=True, help="文章标题")
@click.option("--subtitle", "-s", default="", help="副标题")
@click.option("--summary", default="", help="摘要")
@click.option("--quote", "-q", default="", help="引语")
@click.option("--author", "-a", default="", help="作者")
@click.option("--keywords", "-k", default="", help="关键词（逗号分隔）")
@click.option("--image", "-i", default="", help="配图文件名")
def add_article(title, subtitle, summary, quote, author, keywords, image):
    """
    手动添加单篇文章。
    """
    print_header("添加文章")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    articles = load_articles(project_root)

    new_article = Article(
        id=generate_id("art_"),
        title=title,
        subtitle=subtitle,
        summary=summary,
        quote=quote,
        author=author,
        keywords=[k.strip() for k in keywords.split(",")] if keywords else [],
        image_path=image,
        order=len(articles) + 1,
    )

    articles.append(new_article)
    save_articles(project_root, articles)

    config = load_config(project_root)
    config.updated_at = timestamp()
    save_config(project_root, config)

    print_success(f"文章已添加: {title}")
    print_table(
        ["字段", "内容"],
        [
            ["ID", new_article.id],
            ["标题", title],
            ["副标题", subtitle or "-"],
            ["作者", author or "-"],
            ["引语", quote or "-"],
            ["配图", image or "-"],
        ],
        "文章详情"
    )
