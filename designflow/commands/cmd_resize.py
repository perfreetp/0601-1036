import click
from pathlib import Path
from typing import Tuple

from ..config import (
    find_project_root,
    load_config,
    save_config,
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
    smart_resize,
    timestamp,
)
from PIL import Image


@click.command()
@click.option("--input", "-i", "input_dir", type=click.Path(exists=True, path_type=Path),
              help="输入目录（默认使用 output/composed）")
@click.option("--output", "-o", "output_dir", type=click.Path(path_type=Path),
              help="输出目录（默认使用 output/resized）")
@click.option("--sizes", "-s", help="输出尺寸预设，逗号分隔（如 wechat,weibo）")
@click.option("--all-sizes", is_flag=True, help="输出所有预设尺寸")
@click.option("--width", "-w", type=int, help="自定义宽度（像素）")
@click.option("--height", "-h", type=int, help="自定义高度（像素）")
@click.option("--crop/--no-crop", default=True, help="裁切适配尺寸（否则等比缩放）")
@click.option("--numbering/--no-numbering", default=False, help="添加自动编号")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["keep", "png", "jpg", "webp"]),
              default="keep",
              help="输出格式")
@click.option("--quality", "-q", type=click.IntRange(1, 100), default=90,
              help="JPEG/WebP 质量（1-100）")
@click.option("--prefix", default="", help="文件名前缀")
@click.option("--start-num", type=int, default=1, help="自动编号起始值")
def resize(input_dir, output_dir, sizes, all_sizes, width, height, crop, numbering,
           fmt, quality, prefix, start_num):
    """
    裁切多平台尺寸并自动编号。

    将图片调整为各社交平台所需的尺寸。
    """
    print_header("批量调整尺寸")

    project_root = find_project_root()
    if not project_root:
        print_error("未找到 DesignFlow 项目")
        raise click.Abort()

    config = load_config(project_root)
    dirs = get_project_dirs(project_root)

    input_dir = input_dir or dirs["composed"]
    output_dir = output_dir or dirs["resized"]

    if not input_dir.exists():
        print_error(f"输入目录不存在: {input_dir}")
        raise click.Abort()

    images = find_images(input_dir, recursive=True)
    if not images:
        print_error(f"在 {input_dir} 中未找到图片")
        raise click.Abort()

    selected_presets = []

    if all_sizes:
        selected_presets = list(SIZE_PRESETS.values())
    elif sizes:
        size_list = [s.strip() for s in sizes.split(",")]
        for s in size_list:
            if s in SIZE_PRESETS:
                selected_presets.append(SIZE_PRESETS[s])
            else:
                print_warning(f"未知尺寸预设: {s}")
    elif width and height:
        from ..config import SizePreset
        selected_presets = [SizePreset("custom", width, height, "自定义", f"{width}x{height}")]
    else:
        selected_presets = [
            SIZE_PRESETS["wechat"],
            SIZE_PRESETS["weibo"],
            SIZE_PRESETS["xiaohongshu"],
        ]

    if not selected_presets:
        print_error("没有有效的输出尺寸")
        raise click.Abort()

    output_dir.mkdir(parents=True, exist_ok=True)

    print_info(f"输入: {len(images)} 张图片")
    print_info(f"输出尺寸: {', '.join([p.name for p in selected_presets])}")
    print_info(f"裁切: {'是' if crop else '否'}")
    print_info(f"输出格式: {fmt}")
    if numbering:
        print_info(f"自动编号: 从 {start_num} 开始")

    total_processed = []
    global_num = start_num

    with click.progressbar(images, label="处理中", show_pos=True) as bar:
        for img_path in bar:
            try:
                img_num = global_num if numbering else None

                for preset in selected_presets:
                    result = _resize_single(
                        img_path=img_path,
                        preset=preset,
                        output_dir=output_dir,
                        crop=crop,
                        fmt=fmt,
                        quality=quality,
                        prefix=prefix,
                        number=img_num,
                    )
                    if result:
                        total_processed.append(result)

                if numbering:
                    global_num += 1

            except Exception as e:
                print_error(f"处理失败 '{img_path.name}': {str(e)}")

    config.updated_at = timestamp()
    save_config(project_root, config)

    history_entry = {
        "action": "resize",
        "timestamp": timestamp(),
        "input_count": len(images),
        "sizes": [p.name for p in selected_presets],
        "output_count": len(total_processed),
        "crop": crop,
        "format": fmt,
    }
    save_history(project_root, history_entry)

    print_success(f"成功生成 {len(total_processed)} 张图片")
    print_info(f"输出目录: {output_dir}")

    if total_processed:
        preset_counts = {}
        for p in total_processed:
            preset_counts[p["preset"]] = preset_counts.get(p["preset"], 0) + 1
        rows = [[k, str(v)] for k, v in preset_counts.items()]
        print_table(["尺寸", "数量"], rows, "按尺寸统计")


def _resize_single(img_path: Path, preset, output_dir: Path, crop: bool, fmt: str,
                   quality: int, prefix: str, number: int = None) -> dict:
    from ..utils import ensure_image_mode

    with Image.open(img_path) as img:
        img = ensure_image_mode(img, "RGB")
        resized = smart_resize(img, preset.width, preset.height, crop=crop)

        if fmt == "keep":
            suffix = img_path.suffix.lower()
            out_format = "JPEG" if suffix in (".jpg", ".jpeg") else suffix.upper()[1:]
        elif fmt == "jpg":
            suffix = ".jpg"
            out_format = "JPEG"
        elif fmt == "webp":
            suffix = ".webp"
            out_format = "WEBP"
        else:
            suffix = ".png"
            out_format = "PNG"

        num_part = f"_{number:03d}" if number else ""
        prefix_part = f"{prefix}_" if prefix else ""
        filename = f"{prefix_part}{img_path.stem}_{preset.name}{num_part}{suffix}"
        output_path = output_dir / filename

        save_kwargs = {}
        if out_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = quality
        if out_format == "PNG":
            save_kwargs["optimize"] = True

        resized.save(output_path, out_format, **save_kwargs)

        return {
            "path": output_path,
            "preset": preset.name,
            "original": img_path.name,
            "size": f"{preset.width}x{preset.height}",
        }


@click.command("presets")
def list_presets():
    """
    列出所有可用的尺寸预设。
    """
    print_header("尺寸预设")

    rows = []
    for name, preset in SIZE_PRESETS.items():
        rows.append([
            name,
            f"{preset.width}x{preset.height}",
            preset.platform,
            preset.description,
        ])

    print_table(["预设", "尺寸", "平台", "描述"], rows)
