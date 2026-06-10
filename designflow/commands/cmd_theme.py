import click
from pathlib import Path
from typing import Optional

from ..config import (
    find_project_root,
    load_config,
    save_config,
    load_themes,
    save_themes,
    Theme,
    DEFAULT_THEMES,
)
from ..utils import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    timestamp,
)


@click.group()
def theme():
    """
    管理版式主题和视觉风格。

    查看、选择、自定义主题配色和字体。
    """
    pass


@theme.command("list")
def list_themes():
    """
    列出所有可用的主题。
    """
    print_header("可用主题")

    project_root = find_project_root()
    themes = load_themes(project_root) if project_root else {}

    if not themes:
        print_warning("未找到任何主题")
        return

    rows = []
    for name, theme_obj in themes.items():
        palette_str = " ".join([
            f"[{c}]██[/]" for c in list(theme_obj.palette.values())[:5]
        ])
        rows.append([
            f"[bold]{theme_obj.display_name or name}[/bold]",
            name,
            theme_obj.description or "",
            palette_str,
        ])

    print_table(["显示名称", "标识", "描述", "色板"], rows)


@theme.command("show")
@click.argument("name")
def show_theme(name):
    """
    显示指定主题的详细信息。
    """
    print_header(f"主题详情: {name}")

    project_root = find_project_root()
    themes = load_themes(project_root) if project_root else {}

    if name not in themes:
        print_error(f"主题 '{name}' 不存在")
        available = ", ".join(themes.keys())
        print_info(f"可用主题: {available}")
        raise click.Abort()

    t = themes[name]

    print_table(
        ["属性", "值"],
        [
            ["名称", t.display_name or t.name],
            ["标识", t.name],
            ["描述", t.description or "-"],
        ],
        "基本信息"
    )

    palette_rows = [[k, f"[{v}]■[/] {v}"] for k, v in t.palette.items()]
    print_table(["用途", "颜色"], palette_rows, "色板")

    font_rows = [[k, v] for k, v in t.fonts.items()]
    print_table(["用途", "字体"], font_rows, "字体")

    layout_rows = [[k, str(v)] for k, v in t.layout.items()]
    print_table(["属性", "值"], layout_rows, "布局参数")


@theme.command("use")
@click.argument("name")
def use_theme(name):
    """
    设置当前项目使用的主题。
    """
    print_header(f"应用主题: {name}")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    themes = load_themes(project_root)
    if name not in themes:
        print_error(f"主题 '{name}' 不存在")
        available = ", ".join(themes.keys())
        print_info(f"可用主题: {available}")
        raise click.Abort()

    config = load_config(project_root)
    config.current_theme = name
    config.updated_at = timestamp()
    save_config(project_root, config)

    print_success(f"已切换到主题: {themes[name].display_name or name}")
    print_info("使用 'designflow compose' 命令应用新主题生成图片")


@theme.command("current")
def current_theme():
    """
    显示当前使用的主题。
    """
    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    themes = load_themes(project_root)

    current_name = config.current_theme or "default"
    current = themes.get(current_name)

    if current:
        print_header(f"当前主题: {current.display_name or current_name}")
        palette_str = " ".join([f"[{c}]██[/] {c}" for c in list(current.palette.values())[:4]])
        print_info(f"色板: {palette_str}")
        print_info(f"描述: {current.description or '无'}")
    else:
        print_warning(f"当前主题 '{current_name}' 不存在，使用 default")


@theme.command("create")
@click.option("--name", "-n", required=True, help="主题标识（英文，如 mytheme）")
@click.option("--display-name", "-d", help="显示名称")
@click.option("--description", "-desc", help="主题描述")
@click.option("--primary", help="主色（十六进制，如 #FF0000）")
@click.option("--accent", help="强调色（十六进制）")
@click.option("--background", help="背景色（十六进制）")
@click.option("--text", help="文字颜色（十六进制）")
@click.option("--base-on", help="基于现有主题创建")
def create_theme(name, display_name, description, primary, accent, background, text, base_on):
    """
    创建自定义主题。
    """
    print_header("创建自定义主题")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    themes = load_themes(project_root)

    if name in themes:
        print_error(f"主题 '{name}' 已存在")
        raise click.Abort()

    if base_on and base_on in themes:
        base = themes[base_on]
        new_theme = Theme(
            name=name,
            display_name=display_name or f"{base.display_name or base_on} (自定义)",
            description=description or base.description,
            palette=dict(base.palette),
            fonts=dict(base.fonts),
            layout=dict(base.layout),
        )
        print_info(f"基于主题 '{base_on}' 创建")
    else:
        from ..config import DEFAULT_THEMES
        base = DEFAULT_THEMES["default"]
        new_theme = Theme(
            name=name,
            display_name=display_name or name,
            description=description or "自定义主题",
            palette=dict(base.palette),
            fonts=dict(base.fonts),
            layout=dict(base.layout),
        )

    if primary:
        new_theme.palette["primary"] = primary
    if accent:
        new_theme.palette["accent"] = accent
    if background:
        new_theme.palette["background"] = background
    if text:
        new_theme.palette["text"] = text

    themes[name] = new_theme
    save_themes(project_root, themes)

    print_success(f"主题 '{name}' 已创建")

    palette_str = " ".join([f"[{c}]██[/] {c}" for c in list(new_theme.palette.values())[:5]])
    print_info(f"色板: {palette_str}")


@theme.command("modify")
@click.argument("name")
@click.option("--primary", help="主色（十六进制）")
@click.option("--secondary", help="次色（十六进制）")
@click.option("--accent", help="强调色（十六进制）")
@click.option("--background", help="背景色（十六进制）")
@click.option("--text", help="文字颜色（十六进制）")
@click.option("--title-font", help="标题字体")
@click.option("--body-font", help="正文字体")
@click.option("--title-size", type=int, help="标题字号")
@click.option("--padding", type=int, help="内边距（像素）")
def modify_theme(name, primary, secondary, accent, background, text,
                 title_font, body_font, title_size, padding):
    """
    修改现有主题的参数。
    """
    print_header(f"修改主题: {name}")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    themes = load_themes(project_root)

    if name not in themes:
        print_error(f"主题 '{name}' 不存在")
        raise click.Abort()

    theme_obj = themes[name]

    if primary:
        theme_obj.palette["primary"] = primary
    if secondary:
        theme_obj.palette["secondary"] = secondary
    if accent:
        theme_obj.palette["accent"] = accent
    if background:
        theme_obj.palette["background"] = background
    if text:
        theme_obj.palette["text"] = text
    if title_font:
        theme_obj.fonts["title"] = title_font
    if body_font:
        theme_obj.fonts["body"] = body_font
    if title_size:
        theme_obj.layout["title_size"] = title_size
    if padding:
        theme_obj.layout["padding"] = padding

    save_themes(project_root, themes)

    config = load_config(project_root)
    if config.current_theme == name:
        config.updated_at = timestamp()
        save_config(project_root, config)

    print_success(f"主题 '{name}' 已更新并持久化保存")
    palette_str = " ".join([f"[{c}]██[/]" for c in list(theme_obj.palette.values())[:5]])
    print_info(f"当前色板: {palette_str}")


@theme.command("preview")
@click.option("--theme", "-t", help="要预览的主题（默认使用当前主题）")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="输出目录")
def preview_theme(theme, output):
    """
    生成主题预览图。
    """
    print_header("主题预览")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    themes = load_themes(project_root)

    theme_name = theme or config.current_theme or "default"
    if theme_name not in themes:
        print_error(f"主题 '{theme_name}' 不存在")
        raise click.Abort()

    theme_obj = themes[theme_name]

    try:
        from PIL import Image, ImageDraw

        preview_size = (1200, 600)
        img = Image.new("RGB", preview_size, theme_obj.palette.get("background", "#FFFFFF"))
        draw = ImageDraw.Draw(img)

        padding = 40
        swatch_size = 80
        y = padding

        draw.text((padding, y), f"主题: {theme_obj.display_name or theme_name}",
                 fill=theme_obj.palette.get("text", "#000000"))
        y += 40

        for i, (color_name, color_hex) in enumerate(theme_obj.palette.items()):
            x = padding + i * (swatch_size + 20)
            from ..utils import hex_to_rgb
            draw.rectangle([x, y, x + swatch_size, y + swatch_size], fill=hex_to_rgb(color_hex))
            draw.text((x, y + swatch_size + 10), color_name,
                     fill=theme_obj.palette.get("text", "#000000"))
            draw.text((x, y + swatch_size + 30), color_hex,
                     fill=theme_obj.palette.get("secondary", "#666666"))

        output_dir = output or project_root / "output" / "preview"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"theme_preview_{theme_name}.png"
        img.save(output_path, "PNG")

        print_success(f"预览图已保存: {output_path}")

    except Exception as e:
        print_error(f"生成预览失败: {str(e)}")
