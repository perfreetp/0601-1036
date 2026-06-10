import click
from pathlib import Path
import json
from collections import Counter

from ..config import (
    find_project_root,
    load_config,
    save_config,
    load_articles,
    save_articles,
    load_themes,
    load_history,
    get_project_dirs,
    SIZE_PRESETS,
    save_history,
)
from ..utils import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    find_images,
    get_image_info,
    is_low_resolution,
    timestamp,
    console,
)
from PIL import Image


@click.group()
def check():
    """
    检查低清图、预览目录、记录每期配置。
    """
    pass


@check.command("images")
@click.option("--min-width", type=int, default=1920, help="最小宽度（像素）")
@click.option("--min-height", type=int, default=1080, help="最小高度（像素）")
@click.option("--source-only", is_flag=True, help="只检查源图片目录")
@click.option("--fix", is_flag=True, help="尝试修复（锐化低清图）")
def check_images(min_width, min_height, source_only, fix):
    """
    检查低清图片。
    """
    print_header("检查图片质量")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    dirs = get_project_dirs(project_root)

    check_dirs = [dirs["source_images"]] if source_only else [
        dirs["source_images"],
        dirs["composed"],
        dirs["resized"],
        dirs["captions"],
    ]

    all_low_res = []
    all_errors = []

    for check_dir in check_dirs:
        if not check_dir.exists():
            continue

        images = find_images(check_dir, recursive=True)
        if not images:
            continue

        print_info(f"检查目录: {check_dir.relative_to(project_root)} ({len(images)} 张)")

        for img_path in images:
            is_low, info = is_low_resolution(img_path, min_width, min_height)

            if "error" in info:
                all_errors.append((check_dir, img_path.name, info["error"]))
            elif is_low:
                all_low_res.append((check_dir, img_path, info))

                if fix:
                    try:
                        with Image.open(img_path) as img:
                            from PIL import ImageFilter
                            fixed = img.filter(ImageFilter.SHARPEN)
                            fixed = fixed.filter(ImageFilter.EDGE_ENHANCE)
                            if img_path.suffix.lower() in (".jpg", ".jpeg"):
                                fixed.save(img_path, "JPEG", quality=95)
                            else:
                                fixed.save(img_path, "PNG", optimize=True)
                    except Exception as e:
                        print_warning(f"修复失败 '{img_path.name}': {e}")

    if not all_low_res and not all_errors:
        print_success("所有图片质量达标！")
        return

    if all_low_res:
        print_warning(f"发现 {len(all_low_res)} 张低清图片（< {min_width}x{min_height}）:")
        rows = []
        for check_dir, img_path, info in all_low_res:
            rel_dir = check_dir.relative_to(project_root)
            rows.append([
                str(rel_dir),
                img_path.name,
                f"{info['width']}x{info['height']}",
                f"{info['size_kb']:.0f} KB",
            ])
        print_table(["目录", "文件名", "实际尺寸", "大小"], rows, "低清图片列表")

    if all_errors:
        print_error(f"发现 {len(all_errors)} 个错误文件:")
        for check_dir, name, error in all_errors:
            console.print(f"  • [{check_dir.name}] {name}: {error}")

    history_entry = {
        "action": "check_images",
        "timestamp": timestamp(),
        "min_width": min_width,
        "min_height": min_height,
        "low_res_count": len(all_low_res),
        "errors_count": len(all_errors),
        "fixed": fix,
    }
    save_history(project_root, history_entry)


@check.command("articles")
@click.option("--fix-order", is_flag=True, help="修复序号")
def check_articles(fix_order):
    """
    检查文章数据完整性。
    """
    print_header("检查文章数据")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    articles = load_articles(project_root)
    dirs = get_project_dirs(project_root)

    if not articles:
        print_warning("没有文章数据")
        return

    issues = []
    titles = Counter()
    orders = set()

    for art in articles:
        titles[art.title] += 1
        if art.order in orders:
            issues.append(("重复序号", art.title, f"序号 {art.order} 重复"))
        orders.add(art.order)

        if not art.title:
            issues.append(("缺少标题", art.id, "标题为空"))

        if not art.image_path:
            issues.append(("缺少配图", art.title, "未指定配图"))
        else:
            img_path = dirs["source_images"] / art.image_path
            if not img_path.exists():
                img_path2 = Path(art.image_path)
                if not img_path2.exists():
                    issues.append(("配图不存在", art.title, art.image_path))

        if not art.quote:
            issues.append(("缺少引语", art.title, "未设置引语"))

    dup_titles = [t for t, c in titles.items() if c > 1]
    for dt in dup_titles:
        issues.append(("重复标题", dt, f"出现 {titles[dt]} 次"))

    expected_orders = set(range(1, len(articles) + 1))
    missing_orders = expected_orders - orders
    if missing_orders:
        issues.append(("序号缺失", "", f"缺少序号: {sorted(missing_orders)}"))

    if fix_order and (any("序号" in i[0] for i in issues) or missing_orders):
        for i, art in enumerate(sorted(articles, key=lambda x: (x.order, x.id)), 1):
            art.order = i
        save_articles(project_root, articles)
        print_success("已修复文章序号")

    if not issues:
        print_success(f"{len(articles)} 篇文章数据完整！")
        return

    print_warning(f"发现 {len(issues)} 个问题:")
    rows = [[i[0], i[1][:40] if len(i[1]) > 40 else i[1], i[2]] for i in issues]
    print_table(["问题类型", "文章", "详情"], rows)

    history_entry = {
        "action": "check_articles",
        "timestamp": timestamp(),
        "articles_count": len(articles),
        "issues_count": len(issues),
        "fixed_order": fix_order,
    }
    save_history(project_root, history_entry)


@check.command("preview")
@click.option("--limit", "-l", type=int, default=20, help="显示文件数量上限")
@click.option("--by-type", is_flag=True, help="按类型分组显示")
def preview_directory(limit, by_type):
    """
    预览项目目录和文件。
    """
    print_header("项目目录预览")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    articles = load_articles(project_root)
    dirs = get_project_dirs(project_root)

    print_info(f"项目: {config.name} (第{config.issue}期)")
    print_info(f"主题: {config.current_theme}")
    print_info(f"文章: {len(articles)} 篇")
    print_info(f"创建: {config.created_at}")
    print_info(f"更新: {config.updated_at}")
    console.print()

    all_files = []
    for dir_name, dir_path in dirs.items():
        if not dir_path.exists():
            continue
        images = find_images(dir_path, recursive=True)
        for img in images:
            info = get_image_info(img)
            all_files.append({
                "dir": dir_name,
                "path": img,
                "name": img.name,
                "size": f"{info.get('width', '?')}x{info.get('height', '?')}",
                "kb": info.get("size_kb", 0),
            })

    if not all_files:
        print_warning("项目中没有图片文件")
        return

    print_info(f"共找到 {len(all_files)} 个图片文件")

    if by_type:
        dir_counts = Counter(f["dir"] for f in all_files)
        rows = [[k, str(v)] for k, v in dir_counts.items()]
        print_table(["目录", "文件数"], rows, "按目录统计")

    rows = []
    for f in all_files[:limit]:
        rel_path = f["path"].relative_to(project_root)
        rows.append([
            f["dir"],
            str(rel_path),
            f["size"],
            f"{f['kb']:.0f} KB",
        ])
    if len(all_files) > limit:
        rows.append(["...", f"... 还有 {len(all_files) - limit} 个文件", "...", "..."])
    print_table(["目录", "路径", "尺寸", "大小"], rows, f"文件列表 (前{limit}个)")


@check.command("history")
@click.option("--limit", "-l", type=int, default=10, help="显示记录数")
@click.option("--clear", is_flag=True, help="清空历史记录")
def check_history(limit, clear):
    """
    查看或清除操作历史记录。
    """
    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    if clear:
        history_path = project_root / "history.yaml"
        if history_path.exists():
            history_path.unlink()
            print_success("历史记录已清空")
        else:
            print_info("没有历史记录")
        return

    history = load_history(project_root)

    if not history:
        print_info("没有历史记录")
        return

    print_header(f"操作历史 (最近 {min(limit, len(history))} 条)")

    rows = []
    for i, entry in enumerate(history[:limit]):
        action = entry.get("action", "unknown")
        ts = entry.get("timestamp", "")
        details = []
        for k, v in entry.items():
            if k not in ("action", "timestamp"):
                details.append(f"{k}={v}")
        rows.append([
            str(i + 1),
            action,
            ts,
            "; ".join(details)[:80],
        ])
    print_table(["#", "操作", "时间", "详情"], rows)


@check.command("config")
@click.option("--save", "-s", is_flag=True, help="保存当前配置为模板")
@click.option("--name", "-n", help="配置名称")
def check_config(save, name):
    """
    查看当前项目配置，或保存为模板。
    """
    print_header("项目配置")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    themes = load_themes(project_root)
    articles = load_articles(project_root)

    theme = themes.get(config.current_theme, {})

    if save:
        template_name = name or f"template_{config.name}_{config.issue}"
        template_data = {
            "name": template_name,
            "project_config": config.to_dict(),
            "theme": theme.to_dict() if hasattr(theme, "to_dict") else {},
            "created_at": timestamp(),
        }

        templates_dir = project_root / "assets" / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        template_path = templates_dir / f"{template_name}.json"
        template_path.write_text(json.dumps(template_data, indent=2, ensure_ascii=False), encoding="utf-8")

        print_success(f"配置模板已保存: {template_path}")
        return

    rows = [
        ["项目名称", config.name],
        ["期号", config.issue],
        ["描述", config.description or "-"],
        ["主题", config.current_theme],
        ["作者", config.author or "-"],
        ["签名", config.signature or "-"],
        ["水印", config.watermark or "-"],
        ["创建时间", config.created_at],
        ["更新时间", config.updated_at],
        ["文章数量", str(len(articles))],
    ]
    print_table(["配置项", "值"], rows, "项目信息")

    if hasattr(theme, "display_name"):
        palette_rows = [[k, v] for k, v in theme.palette.items()]
        print_table(["用途", "颜色"], palette_rows, f"当前主题色板 ({theme.display_name})")


@check.command("all")
@click.option("--fix", is_flag=True, help="自动修复可修复的问题")
def check_all(fix):
    """
    执行所有检查。
    """
    print_header("完整项目检查")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    console.print("[bold]1. 检查文章数据...[/bold]")
    articles = load_articles(project_root)
    if articles and fix:
        for i, art in enumerate(sorted(articles, key=lambda x: (x.order, x.id)), 1):
            art.order = i
        save_articles(project_root, articles)
        print_success("  ✓ 文章序号已排序")

    console.print("[bold]2. 检查图片质量...[/bold]")
    dirs = get_project_dirs(project_root)
    low_res_count = 0
    for check_dir in [dirs["source_images"], dirs["composed"], dirs["resized"]]:
        if check_dir.exists():
            images = find_images(check_dir, recursive=True)
            for img in images:
                is_low, info = is_low_resolution(img)
                if is_low:
                    low_res_count += 1
                    print_warning(f"  ! 低清图: {img.name} ({info.get('width', '?')}x{info.get('height', '?')})")
    if low_res_count == 0:
        print_success("  ✓ 图片质量良好")

    console.print("[bold]3. 检查目录结构...[/bold]")
    all_dirs = get_project_dirs(project_root)
    missing_dirs = []
    for dn, dp in all_dirs.items():
        if not dp.exists():
            missing_dirs.append(dn)
    if missing_dirs:
        print_warning(f"  ! 缺失目录: {', '.join(missing_dirs)}")
        if fix:
            for dn in missing_dirs:
                all_dirs[dn].mkdir(parents=True, exist_ok=True)
            print_success("  ✓ 已创建缺失目录")
    else:
        print_success("  ✓ 目录结构完整")

    console.print("[bold]4. 检查文件关联...[/bold]")
    missing_images = []
    for art in articles:
        if art.image_path:
            img_path = dirs["source_images"] / art.image_path
            if not img_path.exists():
                missing_images.append(art.title)
    if missing_images:
        print_warning(f"  ! {len(missing_images)} 篇文章配图缺失")
        for t in missing_images[:3]:
            console.print(f"    - {t}")
    else:
        print_success("  ✓ 配图关联正常")

    console.print()
    print_success("检查完成！")

    config = load_config(project_root)
    config.updated_at = timestamp()
    save_config(project_root, config)

    history_entry = {
        "action": "check_all",
        "timestamp": timestamp(),
        "articles_count": len(articles),
        "low_res_count": low_res_count,
        "missing_dirs": len(missing_dirs),
        "missing_images": len(missing_images),
        "fixed": fix,
    }
    save_history(project_root, history_entry)
