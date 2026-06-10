import click
import zipfile
import json
import csv
from pathlib import Path
from typing import List

from ..config import (
    find_project_root,
    load_config,
    load_articles,
    get_project_dirs,
    SIZE_PRESETS,
    save_history,
    load_themes,
    load_history,
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
    timestamp,
    timestamp_short,
)


@click.group()
def export():
    """
    导出压缩包、生成分享清单。
    """
    pass


@export.command("zip")
@click.option("--input", "-i", "input_dir", type=click.Path(exists=True, path_type=Path),
              help="输入目录（默认使用 output/captions）")
@click.option("--output", "-o", "output_path", type=click.Path(path_type=Path),
              help="输出 zip 文件路径")
@click.option("--name", "-n", help="压缩包名称（默认使用项目名+期号）")
@click.option("--include-metadata/--no-metadata", default=True,
              help="是否包含元数据文件")
@click.option("--include-manifest/--no-manifest", default=True,
              help="是否包含文件清单")
def export_zip(input_dir, output_path, name, include_metadata, include_manifest):
    """
    打包导出为压缩包。
    """
    print_header("导出压缩包")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    dirs = get_project_dirs(project_root)

    input_dir = input_dir or dirs["captions"]
    if not input_dir.exists():
        input_dir = dirs["resized"]
    if not input_dir.exists():
        input_dir = dirs["composed"]
    if not input_dir.exists():
        print_error(f"找不到有效的输出目录")
        raise click.Abort()

    images = find_images(input_dir, recursive=True)
    if not images:
        print_error(f"在 {input_dir} 中未找到图片")
        raise click.Abort()

    default_name = f"{config.name}_issue{config.issue}_{timestamp_short()}"
    zip_name = name or default_name

    if output_path is None:
        output_dir = dirs["export"]
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir / f"{zip_name}.zip"
    elif output_path.suffix.lower() == ".zip":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path = output_path
    else:
        output_dir = output_path
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir / f"{zip_name}.zip"

    print_info(f"打包 {len(images)} 个文件")
    print_info(f"输入目录: {input_dir}")
    print_info(f"输出: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for img_path in images:
                arcname = img_path.relative_to(input_dir)
                zf.write(img_path, arcname=arcname)

            if include_metadata:
                metadata = {
                    "project": config.name,
                    "issue": config.issue,
                    "generated_at": timestamp(),
                    "theme": config.current_theme,
                    "files": [],
                }
                for img_path in images:
                    info = get_image_info(img_path)
                    metadata["files"].append({
                        "filename": img_path.name,
                        "path": str(img_path.relative_to(input_dir)),
                        "width": info.get("width"),
                        "height": info.get("height"),
                        "size_kb": info.get("size_kb"),
                    })
                metadata_content = json.dumps(metadata, indent=2, ensure_ascii=False)
                zf.writestr("metadata.json", metadata_content)

            if include_manifest:
                articles = load_articles(project_root)
                articles_by_slug = {}
                for a in articles:
                    from ..utils import slugify
                    articles_by_slug[slugify(a.title)] = a

                article_groups = {}
                from ..config import SIZE_PRESETS
                preset_names = list(SIZE_PRESETS.keys())

                for img_path in sorted(images):
                    stem = img_path.stem
                    matched_art = None
                    matched_preset = None

                    for p_name in preset_names:
                        if f"_{p_name}" in stem:
                            matched_preset = p_name
                            break

                    for slug, art in articles_by_slug.items():
                        if slug in stem:
                            matched_art = art
                            break

                    art_id = matched_art.id if matched_art else "unknown"
                    if art_id not in article_groups:
                        article_groups[art_id] = {
                            "title": matched_art.title if matched_art else "未分类",
                            "files": [],
                        }
                    info = get_image_info(img_path)
                    article_groups[art_id]["files"].append({
                        "filename": img_path.name,
                        "path": str(img_path.relative_to(input_dir)),
                        "preset": matched_preset or "",
                        "width": info.get("width"),
                        "height": info.get("height"),
                        "size_kb": info.get("size_kb"),
                    })

                manifest = {
                    "project": config.name,
                    "issue": config.issue,
                    "generated_at": timestamp(),
                    "theme": config.current_theme,
                    "total_files": len(images),
                    "articles_count": len([k for k in article_groups if k != "unknown"]),
                    "articles": list(article_groups.values()),
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

                md_lines = [f"# {config.name} - 第{config.issue}期 素材清单",
                            f"",
                            f"- **生成时间**: {timestamp()}",
                            f"- **主题**: {config.current_theme}",
                            f"- **总文件数**: {len(images)}",
                            f"",
                            f"---",
                            f""]
                for i, (aid, grp) in enumerate(
                    [(k, v) for k, v in article_groups.items() if k != "unknown"], 1
                ):
                    md_lines.append(f"## {i}. {grp['title']}")
                    md_lines.append("")
                    md_lines.append("| 平台/类型 | 文件名 | 尺寸 | 大小 |")
                    md_lines.append("|-----------|--------|------|------|")
                    for f in grp["files"]:
                        size_str = f"{f['width']}×{f['height']}"
                        kb = f.get("size_kb", 0)
                        md_lines.append(f"| {f['preset'] or '封面'} | {f['filename']} | {size_str} | {kb:.1f} KB |")
                    md_lines.append("")
                if "unknown" in article_groups:
                    md_lines.append("## 其他文件")
                    md_lines.append("")
                    for f in article_groups["unknown"]["files"]:
                        size_str = f"{f['width']}×{f['height']}"
                        md_lines.append(f"- {f['filename']} ({size_str})")
                    md_lines.append("")
                zf.writestr("MANIFEST.md", "\n".join(md_lines))

    except Exception as e:
        print_error(f"打包失败: {str(e)}")
        if zip_path.exists():
            zip_path.unlink()
        raise click.Abort()

    zip_size_kb = zip_path.stat().st_size / 1024
    if zip_size_kb > 1024:
        size_str = f"{zip_size_kb / 1024:.1f} MB"
    else:
        size_str = f"{zip_size_kb:.1f} KB"

    history_entry = {
        "action": "export_zip",
        "timestamp": timestamp(),
        "output": str(zip_path),
        "file_count": len(images),
        "size_kb": round(zip_size_kb, 2),
    }
    save_history(project_root, history_entry)

    print_success(f"压缩包已导出: {zip_path}")
    print_info(f"大小: {size_str}, 包含 {len(images)} 个文件")


@export.command("share")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["markdown", "html", "csv", "json", "txt"]),
              default="markdown",
              help="清单格式")
@click.option("--output", "-o", "output_path", type=click.Path(path_type=Path),
              help="输出文件路径")
@click.option("--input", "-i", "input_dir", type=click.Path(exists=True, path_type=Path),
              help="图片目录")
def generate_share_list(fmt, output_path, input_dir):
    """
    生成分享清单（适合社交媒体发布）。
    """
    print_header(f"生成分享清单 ({fmt})")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    articles = load_articles(project_root)
    dirs = get_project_dirs(project_root)

    input_dir = input_dir or dirs["captions"]
    if not input_dir.exists():
        input_dir = dirs["resized"]
    if not input_dir.exists():
        input_dir = dirs["composed"]
    if not input_dir.exists():
        print_error(f"找不到有效的输出目录")
        raise click.Abort()

    images = find_images(input_dir, recursive=True)
    if not images:
        print_error(f"在 {input_dir} 中未找到图片")
        raise click.Abort()

    articles_by_id = {a.id: a for a in articles}
    articles_by_slug = {}
    for a in articles:
        from ..utils import slugify
        articles_by_slug[slugify(a.title)] = a

    grouped = {}
    for img_path in images:
        matched_art = None
        matched_preset = None
        img_stem = img_path.stem

        from ..config import SIZE_PRESETS
        for p in SIZE_PRESETS:
            p_name = p.name
            if f"_{p_name}" in img_stem:
                matched_preset = p_name
                break

        for slug, art in articles_by_slug.items():
            if slug in img_stem:
                matched_art = art
                break

        art_id = matched_art.id if matched_art else "unknown"
        if art_id not in grouped:
            grouped[art_id] = []
        grouped[art_id].append({
            "path": img_path,
            "preset": matched_preset,
        })

    output_dir = output_path.parent if output_path else dirs["export"]
    output_dir.mkdir(parents=True, exist_ok=True)

    default_name = f"share_list_{timestamp_short()}"
    ext_map = {"markdown": ".md", "html": ".html", "csv": ".csv", "json": ".json", "txt": ".txt"}
    output_path = output_path or (output_dir / f"{default_name}{ext_map[fmt]}")

    content = _generate_share_content(config, articles, grouped, fmt)

    output_path.write_text(content, encoding="utf-8")

    history_entry = {
        "action": "export_share",
        "timestamp": timestamp(),
        "format": fmt,
        "output": str(output_path),
        "articles_count": len([k for k in grouped if k != "unknown"]),
    }
    save_history(project_root, history_entry)

    print_success(f"分享清单已生成: {output_path}")


def _generate_share_content(config, articles, grouped, fmt: str) -> str:
    articles_by_id = {a.id: a for a in articles}
    known_articles = [(aid, grouped[aid]) for aid in grouped if aid in articles_by_id]
    known_articles.sort(key=lambda x: articles_by_id[x[0]].order)

    def _get_file_info(item):
        path = item["path"]
        preset = item.get("preset", "")
        try:
            info = get_image_info(path)
            w = info.get("width", "?")
            h = info.get("height", "?")
            size_str = f"{w}×{h}"
        except Exception:
            size_str = "未知"
        return {
            "name": path.name,
            "preset": preset,
            "size": size_str,
        }

    if fmt == "markdown":
        lines = [
            f"# {config.name} · 第{config.issue}期",
            "",
            f"> 生成时间: {timestamp()}",
            f"> 主题: {config.current_theme}",
            "",
            "## 本期目录",
            "",
        ]
        for i, (aid, items) in enumerate(known_articles, 1):
            art = articles_by_id[aid]
            lines.append(f"### {i}. {art.title}")
            if art.subtitle:
                lines.append(f"> {art.subtitle}")
            if art.author:
                lines.append(f"**作者**: {art.author}")
            lines.append("")
            lines.append("| 平台/类型 | 文件名 | 尺寸 |")
            lines.append("|-----------|--------|------|")
            for item in items:
                finfo = _get_file_info(item)
                preset = finfo["preset"] or "封面"
                lines.append(f"| {preset} | {finfo['name']} | {finfo['size']} |")
            lines.append("")

        if "unknown" in grouped:
            lines.append("### 其他图片")
            lines.append("")
            lines.append("| 文件名 | 尺寸 |")
            lines.append("|--------|------|")
            for item in grouped["unknown"]:
                finfo = _get_file_info(item)
                lines.append(f"| {finfo['name']} | {finfo['size']} |")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*由 DesignFlow 创意设计平台生成*")

        return "\n".join(lines)

    elif fmt == "html":
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{config.name} · 第{config.issue}期</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #0984E3; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .article {{ margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 8px; }}
        .article h3 {{ margin: 0 0 10px 0; color: #333; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 0.9em; }}
        th {{ background: #0984E3; color: white; }}
        footer {{ margin-top: 40px; color: #999; text-align: center; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>{config.name} · 第{config.issue}期</h1>
    <p style="color:#999;">生成时间: {timestamp()} | 主题: {config.current_theme}</p>
    <h2>本期目录</h2>
"""
        for i, (aid, items) in enumerate(known_articles, 1):
            art = articles_by_id[aid]
            html += f"""
    <div class="article">
        <h3>{i}. {art.title}</h3>
        {f'<p class="meta">{art.subtitle}</p>' if art.subtitle else ''}
        {f'<p class="meta">作者: {art.author}</p>' if art.author else ''}
        <table>
            <tr><th>平台/类型</th><th>文件名</th><th>尺寸</th></tr>
"""
            for item in items:
                finfo = _get_file_info(item)
                preset = finfo["preset"] or "封面"
                html += f"            <tr><td>{preset}</td><td>{finfo['name']}</td><td>{finfo['size']}</td></tr>\n"
            html += "        </table>\n    </div>\n"

        if "unknown" in grouped:
            html += f"<h2>其他图片 ({len(grouped['unknown'])} 张)</h2><table>"
            for item in grouped["unknown"]:
                finfo = _get_file_info(item)
                html += f"<tr><td>{finfo['name']}</td><td>{finfo['size']}</td></tr>"
            html += "</table>"

        html += """
    <footer>由 DesignFlow 创意设计平台生成</footer>
</body>
</html>"""
        return html

    elif fmt == "csv":
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["文章", "平台/类型", "文件名", "尺寸"])
        for aid, items in known_articles:
            art = articles_by_id[aid]
            for item in items:
                finfo = _get_file_info(item)
                writer.writerow([art.title, finfo["preset"] or "封面", finfo["name"], finfo["size"]])
        if "unknown" in grouped:
            for item in grouped["unknown"]:
                finfo = _get_file_info(item)
                writer.writerow(["其他", "", finfo["name"], finfo["size"]])
        return output.getvalue()

    elif fmt == "json":
        data = {
            "project": config.name,
            "issue": config.issue,
            "generated_at": timestamp(),
            "theme": config.current_theme,
            "total_files": sum(len(v) for v in grouped.values()),
            "articles": [],
        }
        for i, (aid, items) in enumerate(known_articles, 1):
            art = articles_by_id[aid]
            files_data = []
            for item in items:
                finfo = _get_file_info(item)
                files_data.append({
                    "filename": finfo["name"],
                    "preset": finfo["preset"] or "",
                    "size": finfo["size"],
                })
            data["articles"].append({
                "order": i,
                "title": art.title,
                "subtitle": art.subtitle,
                "author": art.author,
                "quote": art.quote,
                "keywords": art.keywords,
                "file_count": len(items),
                "files": files_data,
            })
        if "unknown" in grouped:
            data["other_files"] = [_get_file_info(item) for item in grouped["unknown"]]
        return json.dumps(data, indent=2, ensure_ascii=False)

    else:
        lines = [
            f"{config.name} · 第{config.issue}期",
            f"{'=' * 50}",
            f"生成时间: {timestamp()}",
            f"主题: {config.current_theme}",
            f"总图片数: {sum(len(v) for v in grouped.values())}",
            "",
            "本期目录:",
            "-" * 50,
        ]
        for i, (aid, items) in enumerate(known_articles, 1):
            art = articles_by_id[aid]
            lines.append(f"{i:2d}. {art.title}")
            if art.subtitle:
                lines.append(f"    {art.subtitle}")
            if art.author:
                lines.append(f"    作者: {art.author}")
            for item in items:
                finfo = _get_file_info(item)
                preset = finfo["preset"] or "封面"
                lines.append(f"       [{preset}] {finfo['name']} ({finfo['size']})")
            lines.append("")
        if "unknown" in grouped:
            lines.append(f"其他图片 ({len(grouped['unknown'])} 张):")
            for item in grouped["unknown"]:
                finfo = _get_file_info(item)
                lines.append(f"  • {finfo['name']} ({finfo['size']})")
            lines.append("")
        lines.append("-" * 50)
        lines.append("由 DesignFlow 生成")
        return "\n".join(lines)


@export.command("config")
@click.option("--output", "-o", "output_path", type=click.Path(path_type=Path),
              help="输出文件路径")
def export_config(output_path):
    """
    导出当前项目配置（便于复现和分享）。
    """
    print_header("导出项目配置")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    articles = load_articles(project_root)
    themes = load_themes(project_root)
    history = load_history(project_root)
    dirs = get_project_dirs(project_root)

    theme = themes.get(config.current_theme, {})

    export_data = {
        "project": config.to_dict(),
        "theme": theme.to_dict() if hasattr(theme, "to_dict") else {},
        "articles": [a.to_dict() for a in articles],
        "history": history[:10],
        "exported_at": timestamp(),
    }

    output_dir = output_path.parent if output_path else dirs["export"]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path or (output_dir / f"config_{config.name}_issue{config.issue}.json")

    output_path.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print_success(f"配置已导出: {output_path}")
    print_info(f"包含 {len(articles)} 篇文章，最近 {min(10, len(history))} 条操作记录")


@export.command("batch")
@click.option("--platforms", "-p", help="平台分组，逗号分隔（如 wechat,weibo,xiaohongshu）")
@click.option("--all-platforms", is_flag=True, help="按所有平台分组导出")
@click.option("--separate-zips/--single-zip", default=True, help="是否分别打包")
def batch_export(platforms, all_platforms, separate_zips):
    """
    按平台批量导出。
    """
    print_header("按平台批量导出")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    dirs = get_project_dirs(project_root)

    input_dir = dirs["captions"]
    if not input_dir.exists():
        input_dir = dirs["resized"]
    if not input_dir.exists():
        print_error("找不到处理后的图片")
        raise click.Abort()

    images = find_images(input_dir, recursive=True)
    if not images:
        print_error("未找到图片")
        raise click.Abort()

    if all_platforms:
        target_platforms = list(SIZE_PRESETS.keys())
    elif platforms:
        target_platforms = [p.strip() for p in platforms.split(",")]
    else:
        target_platforms = ["wechat", "weibo", "xiaohongshu", "douyin", "bilibili"]

    grouped = {}
    for img in images:
        for platform in target_platforms:
            if platform in img.name:
                if platform not in grouped:
                    grouped[platform] = []
                grouped[platform].append(img)
                break
        else:
            if "other" not in grouped:
                grouped["other"] = []
            grouped["other"].append(img)

    output_dir = dirs["export"]
    output_dir.mkdir(parents=True, exist_ok=True)

    if separate_zips:
        for platform, files in grouped.items():
            if not files:
                continue
            zip_path = output_dir / f"{config.name}_issue{config.issue}_{platform}_{timestamp_short()}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, arcname=f.name)
            size_kb = zip_path.stat().st_size / 1024
            print_success(f"{platform}: {len(files)} 张 → {zip_path.name} ({size_kb:.0f} KB)")
    else:
        zip_path = output_dir / f"{config.name}_issue{config.issue}_all_{timestamp_short()}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for platform, files in grouped.items():
                for f in files:
                    zf.write(f, arcname=f"{platform}/{f.name}")
        size_kb = zip_path.stat().st_size / 1024
        print_success(f"全部平台: {len(images)} 张 → {zip_path.name} ({size_kb:.0f} KB)")

    total = sum(len(v) for v in grouped.values())
    print_info(f"共处理 {total} 张图片，按 {len(grouped)} 个平台分组")
