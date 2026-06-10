import click
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image

from ..config import (
    find_project_root,
    load_config,
    save_config,
    load_articles,
    load_themes,
    load_profiles,
    save_profiles,
    load_failed_tasks,
    save_failed_tasks,
    clear_failed_tasks,
    get_project_dirs,
    SIZE_PRESETS,
    PublishProfile,
    save_history,
)
from ..composer import (
    compose_article_images,
    add_watermark,
    add_signature,
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
    smart_resize,
    timestamp,
    timestamp_short,
    slugify,
    console,
)


@click.group()
def publish():
    """
    批量发布工作流：一条命令完成 compose → resize → caption → export 全流程。

    支持 profile 预设（wechat/xiaohongshu/weibo/all）和自定义 profile。
    """
    pass


@publish.command("run")
@click.option("--profile", "-p", "profile_name", default="all",
              help="使用的发布预设（wechat/xiaohongshu/weibo/all 或自定义）")
@click.option("--theme", "-t", help="覆盖主题（默认使用 profile 中的主题）")
@click.option("--sizes", "-s", help="覆盖尺寸列表，逗号分隔")
@click.option("--watermark", "-w", help="覆盖水印文字")
@click.option("--no-watermark", is_flag=True, help="不添加水印")
@click.option("--no-quote", is_flag=True, help="不生成引语卡")
@click.option("--numbering/--no-numbering", default=None, help="是否添加自动编号")
@click.option("--overlay-position",
              type=click.Choice(["top", "center", "bottom"]),
              help="封面文字区位置")
@click.option("--output", "-o", "output_dir", type=click.Path(path_type=Path),
              help="导出输出目录")
@click.option("--name", "-n", help="导出压缩包名称")
@click.option("--articles", "-a", help="只处理指定文章，逗号分隔（序号或标题关键词）")
@click.option("--dry-run", "-d", is_flag=True, help="预览计划，不实际生成")
@click.option("--retry", is_flag=True, help="只重试上次失败的任务")
def publish_run(profile_name, theme, sizes, watermark, no_watermark, no_quote,
                numbering, overlay_position, output_dir, name, articles, dry_run, retry):
    """
    运行完整发布流程：compose → resize → caption → export。
    """
    print_header("批量发布")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    profiles = load_profiles(project_root)
    if profile_name not in profiles:
        print_error(f"找不到发布预设: {profile_name}")
        print_info(f"可用预设: {', '.join(profiles.keys())}")
        raise click.Abort()

    profile = profiles[profile_name]
    config = load_config(project_root)
    dirs = get_project_dirs(project_root)

    effective_theme = theme or profile.theme
    effective_sizes = sizes.split(",") if sizes else profile.sizes
    effective_watermark = watermark if watermark is not None else profile.watermark_text
    if no_watermark:
        effective_watermark = ""
    effective_include_quote = not no_quote if no_quote else profile.include_quote
    effective_numbering = numbering if numbering is not None else profile.numbering
    effective_overlay = overlay_position or profile.overlay_position

    preset_dict = SIZE_PRESETS
    selected_presets = []
    invalid = []
    for s in effective_sizes:
        s = s.strip()
        if s in preset_dict:
            selected_presets.append(preset_dict[s])
        else:
            invalid.append(s)
    if invalid:
        print_warning(f"未知尺寸预设已忽略: {', '.join(invalid)}")
    if not selected_presets:
        print_error("没有有效的尺寸预设")
        raise click.Abort()

    all_articles = load_articles(project_root)

    target_articles = all_articles
    failed_set = set()
    if retry:
        failed = load_failed_tasks(project_root)
        if not failed:
            print_warning("没有失败任务可重试")
            raise click.Abort()
        failed_set = {f.get("article_id") or f.get("article") for f in failed}
        target_articles = [a for a in all_articles if a.id in failed_set or a.title in failed_set]
        if not target_articles:
            print_warning("未找到匹配失败任务的文章")
            raise click.Abort()
        print_info(f"重试模式：将处理 {len(target_articles)} 篇失败文章")
    elif articles:
        targets = [t.strip() for t in articles.split(",")]
        target_articles = []
        for t in targets:
            if t.isdigit():
                idx = int(t) - 1
                if 0 <= idx < len(all_articles):
                    target_articles.append(all_articles[idx])
            else:
                matched = [a for a in all_articles if t.lower() in a.title.lower()]
                target_articles.extend(matched)
        if not target_articles:
            print_error("没有找到匹配的文章")
            raise click.Abort()

    if not target_articles:
        print_error("没有可处理的文章")
        raise click.Abort()

    print_info(f"预设: {profile.display_name} ({profile_name})")
    print_info(f"主题: {effective_theme}")
    print_info(f"尺寸: {', '.join([p.name for p in selected_presets])}")
    print_info(f"文章: {len(target_articles)} 篇")
    print_info(f"引语卡: {'是' if effective_include_quote else '否'}")
    print_info(f"自动编号: {'是' if effective_numbering else '否'}")
    print_info(f"文字区位置: {effective_overlay}")
    print_info(f"水印: {effective_watermark or '无'}")

    if dry_run:
        print_info("")
        print_info("Dry-run 模式：以下是将要执行的操作")
        print_info(f"  • 合成封面图: {len(target_articles)} 篇 × {len(selected_presets)} 尺寸 = {len(target_articles) * len(selected_presets)} 张")
        if effective_include_quote:
            print_info(f"  • 生成引语卡: {len(target_articles)} 张")
        if effective_watermark:
            print_info(f"  • 添加水印: 全部图片")
        print_info(f"  • 导出压缩包: {'是' if profile.export_zip else '否'}")
        if profile.export_share_formats:
            print_info(f"  • 分享清单: {', '.join(profile.export_share_formats)}")
        return

    themes = load_themes(project_root)
    if effective_theme not in themes:
        print_error(f"找不到主题: {effective_theme}")
        raise click.Abort()
    theme_obj = themes[effective_theme]

    composed_dir = dirs["composed"]
    resized_dir = dirs["resized"]
    captions_dir = dirs["captions"]
    export_dir = output_dir or dirs["export"]
    export_dir.mkdir(parents=True, exist_ok=True)

    composed_dir.mkdir(parents=True, exist_ok=True)
    resized_dir.mkdir(parents=True, exist_ok=True)
    captions_dir.mkdir(parents=True, exist_ok=True)

    total_composed = 0
    total_resized = 0
    total_watermarked = 0
    failed_tasks = []
    generated_files = []

    print_info("")
    console.print("[bold]第 1 步：合成封面图和引语卡[/bold]")
    with click.progressbar(target_articles, label="合成中", show_pos=True) as bar:
        for i, article in enumerate(bar, 1):
            try:
                num_tuple = (i, len(target_articles)) if effective_numbering else None
                generated = compose_article_images(
                    article=article,
                    theme=theme_obj,
                    presets=selected_presets,
                    source_dir=dirs["source_images"],
                    output_dir=composed_dir,
                    fonts_dir=dirs["fonts"],
                    include_quote=effective_include_quote,
                    numbering=num_tuple,
                    overlay_position=effective_overlay,
                )
                total_composed += len(generated)
                for g in generated:
                    generated_files.append({
                        "article_id": article.id,
                        "article_title": article.title,
                        "path": g["path"],
                        "type": g["type"],
                        "preset": g.get("preset", ""),
                    })
            except Exception as e:
                print_error(f"合成失败 '{article.title}': {str(e)}")
                failed_tasks.append({
                    "step": "compose",
                    "article_id": article.id,
                    "article": article.title,
                    "error": str(e),
                    "timestamp": timestamp(),
                })

    print_success(f"合成完成：{total_composed} 张")
    if failed_tasks:
        print_warning(f"失败 {len(failed_tasks)} 项")

    print_info("")
    console.print("[bold]第 2 步：多尺寸裁切[/bold]")
    composed_images = find_images(composed_dir, recursive=True)
    if composed_images:
        with click.progressbar(composed_images, label="裁切中", show_pos=True) as bar:
            for img_path in bar:
                try:
                    for preset in selected_presets:
                        out_path = resized_dir / f"{img_path.stem}_{preset.name}{img_path.suffix}"
                        with Image.open(img_path) as img:
                            resized = smart_resize(img, preset.width, preset.height, crop=True)
                            resized.save(out_path, quality=95)
                        total_resized += 1
                except Exception as e:
                    print_error(f"裁切失败 '{img_path.name}': {str(e)}")
                    failed_tasks.append({
                        "step": "resize",
                        "file": img_path.name,
                        "error": str(e),
                        "timestamp": timestamp(),
                    })
        print_success(f"裁切完成：{total_resized} 张")
    else:
        print_warning("没有可裁切的图片")

    print_info("")
    console.print("[bold]第 3 步：添加水印和署名[/bold]")
    watermark_source = resized_dir if resized_dir.exists() and find_images(resized_dir) else composed_dir
    watermark_images = find_images(watermark_source, recursive=True)

    if effective_watermark and watermark_images:
        with click.progressbar(watermark_images, label="加印中", show_pos=True) as bar:
            for img_path in bar:
                try:
                    with Image.open(img_path) as img:
                        wm_img = add_watermark(
                            image=img,
                            watermark_text=effective_watermark,
                            position=profile.watermark_position,
                            opacity=profile.watermark_opacity,
                        )
                        out_path = captions_dir / img_path.name
                        wm_img.convert("RGB").save(out_path, quality=95)
                    total_watermarked += 1
                except Exception as e:
                    print_error(f"加印失败 '{img_path.name}': {str(e)}")
                    failed_tasks.append({
                        "step": "caption",
                        "file": img_path.name,
                        "error": str(e),
                        "timestamp": timestamp(),
                    })
        print_success(f"加印完成：{total_watermarked} 张")
    elif not effective_watermark:
        print_info("跳过水印（未设置水印文字）")
    else:
        print_warning("没有可加印的图片")

    if profile.signature_text or profile.signature_author:
        print_warning("署名功能暂未在 publish 中启用，可单独使用 caption signature 命令")

    print_info("")
    console.print("[bold]第 4 步：导出[/bold]")

    final_source = captions_dir if captions_dir.exists() and find_images(captions_dir) else resized_dir

    if profile.export_zip:
        try:
            default_name = f"{config.name}_issue{config.issue}_{timestamp_short()}"
            zip_name = name or default_name
            zip_path = export_dir / f"{zip_name}.zip"

            import zipfile
            final_files = find_images(final_source, recursive=True)

            manifest = _build_manifest(final_files, target_articles, selected_presets, config)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in final_files:
                    zf.write(f, f"images/{f.name}")
                import json
                manifest_str = json.dumps(manifest, ensure_ascii=False, indent=2)
                zf.writestr("manifest.json", manifest_str)
                zf.writestr("MANIFEST.md", _manifest_to_markdown(manifest))

            print_success(f"导出压缩包: {zip_path.name} ({len(final_files)} 张图)")
        except Exception as e:
            print_error(f"导出压缩包失败: {str(e)}")
            failed_tasks.append({
                "step": "export-zip",
                "error": str(e),
                "timestamp": timestamp(),
            })

    if profile.export_share_formats:
        try:
            final_files = find_images(final_source, recursive=True)
            manifest = _build_manifest(final_files, target_articles, selected_presets, config)

            for fmt in profile.export_share_formats:
                share_name = name or f"{config.name}_issue{config.issue}"
                if fmt == "markdown":
                    path = export_dir / f"{share_name}_share.md"
                    path.write_text(_manifest_to_markdown(manifest), encoding="utf-8")
                elif fmt == "html":
                    path = export_dir / f"{share_name}_share.html"
                    path.write_text(_manifest_to_html(manifest), encoding="utf-8")
                elif fmt == "csv":
                    path = export_dir / f"{share_name}_share.csv"
                    path.write_text(_manifest_to_csv(manifest), encoding="utf-8-sig")
                elif fmt == "json":
                    path = export_dir / f"{share_name}_share.json"
                    import json
                    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                elif fmt == "txt":
                    path = export_dir / f"{share_name}_share.txt"
                    path.write_text(_manifest_to_txt(manifest), encoding="utf-8")
                print_success(f"生成分享清单: {path.name} ({fmt})")
        except Exception as e:
            print_error(f"生成分享清单失败: {str(e)}")
            failed_tasks.append({
                "step": "export-share",
                "error": str(e),
                "timestamp": timestamp(),
            })

    if failed_tasks:
        save_failed_tasks(project_root, failed_tasks)
        print_warning(f"共 {len(failed_tasks)} 个失败任务，已保存到 failed_tasks.yaml")
        print_info("使用 designflow publish --retry 可重试失败项")
        for t in failed_tasks[:5]:
            step = t.get("step", "")
            item = t.get("article") or t.get("file", "")
            err = t.get("error", "")
            print_info(f"  • [{step}] {item}: {err}")
    else:
        clear_failed_tasks(project_root)

    history_entry = {
        "action": "publish",
        "timestamp": timestamp(),
        "profile": profile_name,
        "theme": effective_theme,
        "sizes": [p.name for p in selected_presets],
        "articles_count": len(target_articles),
        "composed": total_composed,
        "resized": total_resized,
        "watermarked": total_watermarked,
        "failed": len(failed_tasks),
    }
    save_history(project_root, history_entry)

    print_info("")
    if failed_tasks:
        console.print(f"[yellow][bold]发布完成，但有 {len(failed_tasks)} 个失败项[/bold][/yellow]")
    else:
        console.print("[green][bold]发布完成，全部成功！[/bold][/green]")
    console.print(f"  合成配图: {total_composed} 张")
    console.print(f"  尺寸裁切: {total_resized} 张")
    console.print(f"  水印加印: {total_watermarked} 张")
    console.print(f"  导出目录: {export_dir}")


@publish.command("list")
def list_profiles():
    """
    列出所有可用的发布预设。
    """
    print_header("发布预设列表")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    profiles = load_profiles(project_root)
    rows = []
    for name, p in profiles.items():
        rows.append([
            name,
            p.display_name,
            p.theme,
            str(len(p.sizes)),
            "是" if p.include_quote else "否",
            "是" if p.numbering else "否",
        ])
    print_table(
        ["名称", "显示名", "主题", "尺寸数", "引语卡", "编号"],
        rows,
    )
    print_info(f"共 {len(profiles)} 个预设")


@publish.command("show")
@click.argument("name")
def show_profile(name):
    """
    查看指定发布预设的详细配置。
    """
    print_header(f"预设详情: {name}")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    profiles = load_profiles(project_root)
    if name not in profiles:
        print_error(f"找不到预设: {name}")
        raise click.Abort()

    p = profiles[name]
    console.print(f"[bold]显示名:[/bold] {p.display_name}")
    console.print(f"[bold]描述:[/bold] {p.description}")
    console.print(f"[bold]主题:[/bold] {p.theme}")
    console.print(f"[bold]尺寸列表:[/bold] {', '.join(p.sizes)}")
    console.print(f"[bold]生成引语卡:[/bold] {'是' if p.include_quote else '否'}")
    console.print(f"[bold]自动编号:[/bold] {'是' if p.numbering else '否'}")
    console.print(f"[bold]文字区位置:[/bold] {p.overlay_position}")
    console.print(f"[bold]水印文字:[/bold] {p.watermark_text or '(空)'}")
    console.print(f"[bold]水印位置:[/bold] {p.watermark_position}")
    console.print(f"[bold]水印透明度:[/bold] {p.watermark_opacity}")
    console.print(f"[bold]署名文字:[/bold] {p.signature_text or '(空)'}")
    console.print(f"[bold]署名作者:[/bold] {p.signature_author or '(空)'}")
    console.print(f"[bold]导出压缩包:[/bold] {'是' if p.export_zip else '否'}")
    console.print(f"[bold]分享清单格式:[/bold] {', '.join(p.export_share_formats)}")


@publish.command("save")
@click.argument("name")
@click.option("--display-name", help="显示名称")
@click.option("--description", help="描述")
@click.option("--theme", help="主题名称")
@click.option("--sizes", help="尺寸列表，逗号分隔")
@click.option("--quote/--no-quote", default=None, help="是否生成引语卡")
@click.option("--numbering/--no-numbering", default=None, help="是否自动编号")
@click.option("--overlay-position",
              type=click.Choice(["top", "center", "bottom"]),
              help="文字区位置")
@click.option("--watermark", help="水印文字")
@click.option("--watermark-position",
              type=click.Choice(["top-left", "top-right", "bottom-left", "bottom-right", "center"]),
              help="水印位置")
@click.option("--watermark-opacity", type=click.FloatRange(0.1, 1.0), help="水印透明度")
@click.option("--signature", help="署名文字")
@click.option("--author", help="作者署名")
@click.option("--base-on", default="wechat", help="基于哪个预设创建")
def save_profile(name, display_name, description, theme, sizes, quote, numbering,
                 overlay_position, watermark, watermark_position, watermark_opacity,
                 signature, author, base_on):
    """
    创建或修改发布预设。
    """
    print_header(f"保存预设: {name}")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    profiles = load_profiles(project_root)

    if name in profiles:
        base = profiles[name]
    elif base_on in profiles:
        base = profiles[base_on]
    else:
        print_error(f"找不到基础预设: {base_on}")
        raise click.Abort()

    new_profile = PublishProfile(**base.to_dict())
    new_profile.name = name

    if display_name:
        new_profile.display_name = display_name
    if description:
        new_profile.description = description
    if theme:
        new_profile.theme = theme
    if sizes:
        new_profile.sizes = [s.strip() for s in sizes.split(",")]
    if quote is not None:
        new_profile.include_quote = quote
    if numbering is not None:
        new_profile.numbering = numbering
    if overlay_position:
        new_profile.overlay_position = overlay_position
    if watermark is not None:
        new_profile.watermark_text = watermark
    if watermark_position:
        new_profile.watermark_position = watermark_position
    if watermark_opacity:
        new_profile.watermark_opacity = watermark_opacity
    if signature is not None:
        new_profile.signature_text = signature
    if author is not None:
        new_profile.signature_author = author

    profiles[name] = new_profile
    save_profiles(project_root, profiles)

    print_success(f"预设 '{name}' 已保存")


@publish.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="确认删除该预设?")
def delete_profile(name):
    """
    删除自定义发布预设。
    """
    print_header(f"删除预设: {name}")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    from ..config import DEFAULT_PROFILES
    if name in DEFAULT_PROFILES:
        print_error(f"无法删除内置预设: {name}")
        raise click.Abort()

    profiles = load_profiles(project_root)
    if name not in profiles:
        print_error(f"找不到预设: {name}")
        raise click.Abort()

    del profiles[name]
    save_profiles(project_root, profiles)

    print_success(f"预设 '{name}' 已删除")


@publish.command("failed")
@click.option("--clear", is_flag=True, help="清除失败任务记录")
def list_failed(clear):
    """
    查看或清除上次发布的失败任务。
    """
    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    if clear:
        clear_failed_tasks(project_root)
        print_success("已清除失败任务记录")
        return

    failed = load_failed_tasks(project_root)
    if not failed:
        print_info("没有失败任务")
        return

    print_header(f"失败任务 ({len(failed)} 项)")
    for i, t in enumerate(failed, 1):
        step = t.get("step", "")
        item = t.get("article") or t.get("file", "")
        err = t.get("error", "")
        ts = t.get("timestamp", "")
        console.print(f"  {i}. [{step}] {item}")
        console.print(f"     错误: {err}")
        console.print(f"     时间: {ts}")
    print_info("使用 designflow publish run --retry 重试失败项")


def _build_manifest(files, articles, presets, config) -> Dict[str, Any]:
    articles_by_slug = {slugify(a.title): a for a in articles}
    article_groups = {}

    preset_dict = {p.name: p for p in presets}

    for f in files:
        stem = f.stem
        matched_article = None
        matched_preset = None

        for p_name in preset_dict:
            if f"_{p_name}_" in stem or stem.endswith(f"_{p_name}"):
                matched_preset = p_name
                break

        slug_part = stem
        if matched_preset:
            idx = stem.find(f"_{matched_preset}")
            if idx > 0:
                slug_part = stem[:idx]

        for slug, article in articles_by_slug.items():
            if slug in slug_part:
                matched_article = article
                break

        if not matched_article:
            for article in articles:
                art_slug = slugify(article.title)
                if art_slug in stem:
                    matched_article = article
                    break

        key = matched_article.id if matched_article else "unknown"
        if key not in article_groups:
            article_groups[key] = {
                "article_id": matched_article.id if matched_article else "unknown",
                "article_title": matched_article.title if matched_article else "未分类",
                "files": [],
            }

        try:
            info = get_image_info(f)
            w = info.get("width", 0)
            h = info.get("height", 0)
            size_str = f"{w}×{h}"
        except Exception:
            size_str = "未知"

        article_groups[key]["files"].append({
            "filename": f.name,
            "size": size_str,
            "preset": matched_preset or "",
            "path": str(f.relative_to(config.root if hasattr(config, 'root') else f.parent.parent)),
        })

    manifest = {
        "project": config.name,
        "issue": config.issue,
        "author": config.author,
        "generated_at": timestamp(),
        "total_files": len(files),
        "total_articles": len([k for k in article_groups if k != "unknown"]),
        "platforms": [p.name for p in presets],
        "articles": list(article_groups.values()),
    }
    return manifest


def _manifest_to_markdown(manifest: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"# {manifest['project']} 第{manifest['issue']}期 分享清单")
    lines.append("")
    lines.append(f"- **项目**: {manifest['project']}")
    lines.append(f"- **期数**: 第{manifest['issue']}期")
    lines.append(f"- **作者**: {manifest['author']}")
    lines.append(f"- **生成时间**: {manifest['generated_at']}")
    lines.append(f"- **总图片数**: {manifest['total_files']}")
    lines.append(f"- **文章数**: {manifest['total_articles']}")
    lines.append(f"- **平台**: {', '.join(manifest['platforms'])}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, art in enumerate(manifest["articles"], 1):
        lines.append(f"## {i}. {art['article_title']}")
        lines.append("")
        lines.append("| 平台/类型 | 文件名 | 尺寸 |")
        lines.append("|-----------|--------|------|")
        for f in art["files"]:
            preset = f["preset"] or "封面"
            lines.append(f"| {preset} | {f['filename']} | {f['size']} |")
        lines.append("")

    return "\n".join(lines)


def _manifest_to_html(manifest: Dict[str, Any]) -> str:
    md = _manifest_to_markdown(manifest)
    import html
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='zh-CN'>",
        "<head><meta charset='UTF-8'>",
        f"<title>{html.escape(manifest['project'])} 第{manifest['issue']}期 分享清单</title>",
        "<style>body{font-family:sans-serif;max-width:900px;margin:0 auto;padding:20px;}",
        "table{border-collapse:collapse;width:100%;margin:10px 0;}",
        "th,td{border:1px solid #ddd;padding:8px;text-align:left;}",
        "th{background:#f5f5f5;}h1{color:#333;}h2{color:#555;border-bottom:2px solid #eee;padding-bottom:6px;}</style>",
        "</head><body>",
    ]
    for line in md.split("\n"):
        if line.startswith("# "):
            html_parts.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("|"):
            html_parts.append(f"<p>{html.escape(line)}</p>")
        elif line.startswith("- **"):
            html_parts.append(f"<p>{html.escape(line)}</p>")
        elif line == "---":
            html_parts.append("<hr>")
        elif line.strip():
            html_parts.append(f"<p>{html.escape(line)}</p>")
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def _manifest_to_csv(manifest: Dict[str, Any]) -> str:
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["文章", "平台/类型", "文件名", "尺寸"])
    for art in manifest["articles"]:
        for f in art["files"]:
            writer.writerow([art["article_title"], f["preset"] or "封面", f["filename"], f["size"]])
    return output.getvalue()


def _manifest_to_txt(manifest: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"{manifest['project']} 第{manifest['issue']}期 分享清单")
    lines.append("=" * 50)
    lines.append(f"生成时间: {manifest['generated_at']}")
    lines.append(f"总图片数: {manifest['total_files']}")
    lines.append(f"文章数: {manifest['total_articles']}")
    lines.append(f"平台: {', '.join(manifest['platforms'])}")
    lines.append("")

    for i, art in enumerate(manifest["articles"], 1):
        lines.append(f"【{i}】{art['article_title']}")
        for f in art["files"]:
            preset = f["preset"] or "封面"
            lines.append(f"    • {preset}: {f['filename']} ({f['size']})")
        lines.append("")

    return "\n".join(lines)

