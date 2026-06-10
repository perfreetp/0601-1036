import click
from pathlib import Path

from ..config import (
    find_project_root,
    load_config,
    save_config,
    get_project_dirs,
    save_history,
)
from ..composer import add_watermark, add_signature
from ..utils import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    find_images,
    timestamp,
)
from PIL import Image


@click.group()
def caption():
    """
    添加署名、替换水印等文字标注。
    """
    pass


@caption.command("watermark")
@click.option("--text", "-t", help="水印文字（默认使用项目配置）")
@click.option("--input", "-i", "input_dir", type=click.Path(exists=True, path_type=Path),
              help="输入目录")
@click.option("--output", "-o", "output_dir", type=click.Path(path_type=Path),
              help="输出目录（默认使用 output/captions）")
@click.option("--position", "-p",
              type=click.Choice(["top-left", "top-right", "bottom-left", "bottom-right", "center"]),
              default="bottom-right",
              help="水印位置")
@click.option("--opacity", type=click.FloatRange(0.1, 1.0), default=0.6,
              help="水印透明度（0.1-1.0）")
@click.option("--font-size", type=int, help="水印字号（自动计算）")
@click.option("--replace", "-r", is_flag=True, help="替换现有水印（重新生成）")
@click.option("--remove", is_flag=True, help="移除水印（不添加新水印）")
def add_watermark_cmd(text, input_dir, output_dir, position, opacity, font_size, replace, remove):
    """
    为图片添加或替换水印。
    """
    print_header("添加水印" if not remove else "移除水印")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    dirs = get_project_dirs(project_root)

    watermark_text = text or config.watermark
    if not watermark_text and not remove:
        print_warning("未指定水印文字，将使用项目名称")
        watermark_text = config.name

    input_dir = input_dir or dirs["resized"]
    if not input_dir.exists():
        print_error(f"输入目录不存在: {input_dir}")
        raise click.Abort()

    output_dir = output_dir or dirs["captions"]
    output_dir.mkdir(parents=True, exist_ok=True)

    images = find_images(input_dir, recursive=True)
    if not images:
        print_error(f"在 {input_dir} 中未找到图片")
        raise click.Abort()

    print_info(f"处理 {len(images)} 张图片")
    if not remove:
        print_info(f"水印文字: '{watermark_text}'")
        print_info(f"位置: {position}")
        print_info(f"透明度: {opacity}")

    processed = []

    with click.progressbar(images, label="处理中", show_pos=True) as bar:
        for img_path in bar:
            try:
                with Image.open(img_path) as img:
                    if remove:
                        result_img = img.convert("RGB")
                    else:
                        result_img = add_watermark(
                            image=img,
                            watermark_text=watermark_text,
                            position=position,
                            opacity=opacity,
                            font_size=font_size,
                        ).convert("RGB")

                    output_path = output_dir / img_path.name
                    result_img.save(output_path, "PNG" if img_path.suffix.lower() == ".png" else "JPEG", quality=95)

                    processed.append({
                        "path": output_path,
                        "action": "removed" if remove else "added",
                    })

            except Exception as e:
                print_error(f"处理失败 '{img_path.name}': {str(e)}")

    if not remove:
        config.watermark = watermark_text
        config.updated_at = timestamp()
        save_config(project_root, config)

    history_entry = {
        "action": "watermark",
        "timestamp": timestamp(),
        "text": watermark_text if not remove else "",
        "position": position,
        "opacity": opacity,
        "processed": len(processed),
        "remove": remove,
    }
    save_history(project_root, history_entry)

    action_str = "移除" if remove else "添加"
    print_success(f"成功{action_str}水印，处理 {len(processed)} 张图片")
    print_info(f"输出目录: {output_dir}")


@caption.command("signature")
@click.option("--text", "-t", help="签名文字（如栏目名称）")
@click.option("--author", "-a", help="作者名称")
@click.option("--input", "-i", "input_dir", type=click.Path(exists=True, path_type=Path),
              help="输入目录")
@click.option("--output", "-o", "output_dir", type=click.Path(path_type=Path),
              help="输出目录")
@click.option("--position", "-p",
              type=click.Choice(["bottom", "bottom-left", "bottom-right", "center"]),
              default="bottom",
              help="签名位置")
def add_signature_cmd(text, author, input_dir, output_dir, position):
    """
    为图片添加署名和作者信息。
    """
    print_header("添加署名")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    dirs = get_project_dirs(project_root)

    sig_text = text or config.signature
    author_text = author or config.author

    if not sig_text and not author_text:
        print_error("请指定签名文字（--text）或作者（--author）")
        raise click.Abort()

    input_dir = input_dir or dirs["captions"]
    if not input_dir.exists():
        input_dir = dirs["resized"]
    if not input_dir.exists():
        print_error(f"输入目录不存在: {input_dir}")
        raise click.Abort()

    output_dir = output_dir or dirs["captions"]
    output_dir.mkdir(parents=True, exist_ok=True)

    images = find_images(input_dir, recursive=True)
    if not images:
        print_error(f"在 {input_dir} 中未找到图片")
        raise click.Abort()

    print_info(f"处理 {len(images)} 张图片")
    if sig_text:
        print_info(f"签名: '{sig_text}'")
    if author_text:
        print_info(f"作者: '{author_text}'")
    print_info(f"位置: {position}")

    processed = []

    with click.progressbar(images, label="处理中", show_pos=True) as bar:
        for img_path in bar:
            try:
                with Image.open(img_path) as img:
                    result_img = add_signature(
                        image=img,
                        signature=sig_text,
                        author=author_text,
                        position=position,
                    ).convert("RGB")

                    output_path = output_dir / img_path.name
                    result_img.save(output_path, "PNG" if img_path.suffix.lower() == ".png" else "JPEG", quality=95)

                    processed.append({
                        "path": output_path,
                    })

            except Exception as e:
                print_error(f"处理失败 '{img_path.name}': {str(e)}")

    if sig_text:
        config.signature = sig_text
    if author_text:
        config.author = author_text
    config.updated_at = timestamp()
    save_config(project_root, config)

    history_entry = {
        "action": "signature",
        "timestamp": timestamp(),
        "signature": sig_text,
        "author": author_text,
        "position": position,
        "processed": len(processed),
    }
    save_history(project_root, history_entry)

    print_success(f"成功添加署名，处理 {len(processed)} 张图片")
    print_info(f"输出目录: {output_dir}")


@caption.command("set")
@click.option("--signature", "-s", help="设置默认签名文字")
@click.option("--watermark", "-w", help="设置默认水印文字")
@click.option("--author", "-a", help="设置默认作者")
def set_defaults(signature, watermark, author):
    """
    设置默认的签名、水印、作者信息。
    """
    print_header("设置默认信息")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    updated = []

    if signature is not None:
        config.signature = signature
        updated.append(f"签名: '{signature}'")

    if watermark is not None:
        config.watermark = watermark
        updated.append(f"水印: '{watermark}'")

    if author is not None:
        config.author = author
        updated.append(f"作者: '{author}'")

    if not updated:
        print_warning("未指定任何设置项")
        return

    config.updated_at = timestamp()
    save_config(project_root, config)

    for item in updated:
        print_success(f"已设置 {item}")
