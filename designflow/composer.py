import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .config import Theme, Article, SizePreset
from .utils import hex_to_rgb, ensure_image_mode, smart_resize, slugify


def get_font(font_name: str, size: int, fallback_dir: Optional[Path] = None) -> ImageFont.FreeTypeFont:
    font_paths = []
    if fallback_dir:
        font_paths.extend(list(fallback_dir.glob("*.ttf")) + list(fallback_dir.glob("*.otf")))
    system_font_dirs = [
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts"),
        Path("/Library/Fonts"),
        Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
        Path.home() / ".fonts",
    ]
    for font_dir in system_font_dirs:
        if font_dir.exists():
            font_paths.extend(list(font_dir.glob("*.ttf")) + list(font_dir.glob("*.otf")))
    for font_path in font_paths:
        if font_name.lower().replace(" ", "") in font_path.stem.lower().replace(" ", ""):
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except (OSError, IOError):
                continue
    for font_path in font_paths:
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except (OSError, IOError):
            continue
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except (OSError, IOError):
        return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    words = text.replace("\n", " \n ").split()
    lines = []
    current_line = ""
    for word in words:
        if word == "\n":
            lines.append(current_line.strip())
            current_line = ""
            continue
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines or [""]


def create_overlay(size: Tuple[int, int], color: str, opacity: float) -> Image.Image:
    overlay = Image.new("RGBA", size, hex_to_rgb(color) + (0,))
    overlay_draw = ImageDraw.Draw(overlay)
    alpha = int(255 * opacity)
    overlay_draw.rectangle([(0, 0), size], fill=hex_to_rgb(color) + (alpha,))
    return overlay


def create_gradient(size: Tuple[int, int], colors: list, direction: str = "vertical") -> Image.Image:
    base = Image.new("RGB", size, colors[0])
    if len(colors) < 2:
        return base
    gradient = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    if direction == "vertical":
        for y in range(size[1]):
            ratio = y / size[1]
            color_idx = min(int(ratio * (len(colors) - 1)), len(colors) - 2)
            local_ratio = (ratio * (len(colors) - 1)) - color_idx
            c1 = hex_to_rgb(colors[color_idx])
            c2 = hex_to_rgb(colors[color_idx + 1])
            r = int(c1[0] + (c2[0] - c1[0]) * local_ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * local_ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * local_ratio)
            draw.line([(0, y), (size[0], y)], fill=(r, g, b, 255))
    elif direction == "horizontal":
        for x in range(size[0]):
            ratio = x / size[0]
            color_idx = min(int(ratio * (len(colors) - 1)), len(colors) - 2)
            local_ratio = (ratio * (len(colors) - 1)) - color_idx
            c1 = hex_to_rgb(colors[color_idx])
            c2 = hex_to_rgb(colors[color_idx + 1])
            r = int(c1[0] + (c2[0] - c1[0]) * local_ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * local_ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * local_ratio)
            draw.line([(x, 0), (x, size[1])], fill=(r, g, b, 255))
    return gradient


def create_cover_image(
    article: Article,
    theme: Theme,
    preset: SizePreset,
    source_image: Optional[Path] = None,
    fonts_dir: Optional[Path] = None,
    add_overlay: bool = True,
    overlay_position: str = "bottom",
) -> Image.Image:
    width, height = preset.width, preset.height
    layout = theme.layout
    palette = theme.palette
    padding = layout.get("padding", 60)

    base = Image.new("RGB", (width, height), hex_to_rgb(palette.get("background", "#FFFFFF")))

    if source_image and source_image.exists():
        try:
            with Image.open(source_image) as img:
                img = ensure_image_mode(img, "RGB")
                resized = smart_resize(img, width, height, crop=True)
                base = resized
        except Exception:
            pass

    if add_overlay:
        overlay = create_overlay((width, height), palette.get("primary", "#000000"),
                                layout.get("overlay_opacity", 0.3))
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(base)

    title_font = get_font(theme.fonts.get("title", "Microsoft YaHei Bold"),
                          layout.get("title_size", 72), fonts_dir)
    subtitle_font = get_font(theme.fonts.get("subtitle", "Microsoft YaHei"),
                             layout.get("subtitle_size", 36), fonts_dir)

    text_color = hex_to_rgb(palette.get("text_light", "#FFFFFF"))

    content_width = width - 2 * padding
    content_height = height - 2 * padding

    title_lines = wrap_text(article.title, title_font, content_width, draw)
    subtitle_lines = wrap_text(article.subtitle, subtitle_font, content_width, draw) if article.subtitle else []

    title_size = layout.get("title_size", 72)
    subtitle_size = layout.get("subtitle_size", 36)
    line_spacing = 1.3

    total_title_height = len(title_lines) * title_size * line_spacing
    total_subtitle_height = len(subtitle_lines) * subtitle_size * line_spacing if subtitle_lines else 0
    total_height = total_title_height + total_subtitle_height + (40 if subtitle_lines else 0)

    if overlay_position == "bottom":
        y_start = height - padding - total_height
    elif overlay_position == "center":
        y_start = (height - total_height) // 2
    else:
        y_start = padding

    y = y_start
    for line in title_lines:
        draw.text((padding, y), line, font=title_font, fill=text_color)
        y += title_size * line_spacing

    if subtitle_lines:
        y += 20
        for line in subtitle_lines:
            draw.text((padding, y), line, font=subtitle_font, fill=text_color)
            y += subtitle_size * line_spacing

    accent_color = hex_to_rgb(palette.get("accent", "#0984E3"))
    bar_width = 120
    bar_height = 6
    if overlay_position == "bottom":
        bar_y = y_start - bar_height - 20
    else:
        bar_y = y_start + total_height + 20
    draw.rectangle([(padding, bar_y), (padding + bar_width, bar_y + bar_height)], fill=accent_color)

    return base


def create_quote_card(
    article: Article,
    theme: Theme,
    preset: SizePreset,
    fonts_dir: Optional[Path] = None,
) -> Image.Image:
    width, height = preset.width, preset.height
    layout = theme.layout
    palette = theme.palette
    padding = layout.get("padding", 60)

    base = Image.new("RGB", (width, height), hex_to_rgb(palette.get("background", "#FFFFFF")))
    draw = ImageDraw.Draw(base)

    accent_color = hex_to_rgb(palette.get("accent", "#0984E3"))
    primary_color = hex_to_rgb(palette.get("primary", "#2D3436"))
    text_color = hex_to_rgb(palette.get("text", "#2D3436"))

    quote_font_size = int(width / 20)
    quote_font = get_font(theme.fonts.get("quote", "Georgia Italic"), quote_font_size, fonts_dir)
    author_font_size = int(width / 30)
    author_font = get_font(theme.fonts.get("body", "Microsoft YaHei"), author_font_size, fonts_dir)

    content_width = width - 2 * padding

    quote_text = article.quote or f"「{article.title}」"
    quote_lines = wrap_text(quote_text, quote_font, content_width, draw)

    total_quote_height = len(quote_lines) * quote_font_size * 1.5
    total_height = total_quote_height + author_font_size + 100

    y_start = (height - total_height) // 2

    quote_mark_font_size = int(width / 8)
    quote_mark_font = get_font("Georgia", quote_mark_font_size, fonts_dir)
    draw.text((padding - 10, y_start - quote_mark_font_size - 20), '"',
              font=quote_mark_font, fill=accent_color)

    y = y_start
    for line in quote_lines:
        draw.text((padding, y), line, font=quote_font, fill=text_color)
        y += quote_font_size * 1.5

    author_text = article.author or article.title
    y += 40
    draw.rectangle([(padding, y), (padding + 60, y + 2)], fill=accent_color)
    y += 20
    draw.text((padding, y), f"— {author_text}", font=author_font, fill=primary_color)

    return base


def add_watermark(
    image: Image.Image,
    watermark_text: str,
    position: str = "bottom-right",
    opacity: float = 0.6,
    font_size: Optional[int] = None,
) -> Image.Image:
    if not watermark_text:
        return image

    img = image.convert("RGBA")
    width, height = img.size

    fs = font_size or max(20, min(width, height) // 30)
    font = get_font("Microsoft YaHei", fs)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    margin = 20
    positions = {
        "top-left": (margin, margin),
        "top-right": (width - text_width - margin, margin),
        "bottom-left": (margin, height - text_height - margin),
        "bottom-right": (width - text_width - margin, height - text_height - margin),
        "center": ((width - text_width) // 2, (height - text_height) // 2),
    }
    x, y = positions.get(position, positions["bottom-right"])

    alpha = int(255 * opacity)
    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, alpha))

    return Image.alpha_composite(img, overlay)


def add_signature(
    image: Image.Image,
    signature: str,
    author: str = "",
    position: str = "bottom",
) -> Image.Image:
    if not signature and not author:
        return image

    img = image.convert("RGBA")
    width, height = img.size
    padding = 30

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    sig_font = get_font("KaiTi", min(32, width // 40))
    author_font = get_font("Microsoft YaHei", min(20, width // 60))

    sig_text = signature or ""
    author_text = f"文 / {author}" if author else ""

    sig_bbox = draw.textbbox((0, 0), sig_text, font=sig_font) if sig_text else (0, 0, 0, 0)
    author_bbox = draw.textbbox((0, 0), author_text, font=author_font) if author_text else (0, 0, 0, 0)

    sig_width = sig_bbox[2] - sig_bbox[0]
    sig_height = sig_bbox[3] - sig_bbox[0]
    author_width = author_bbox[2] - author_bbox[0]

    total_width = max(sig_width, author_width)
    total_height = sig_height + (author_font.size + 10 if author_text else 0) + 20

    if position == "bottom":
        x = (width - total_width) // 2
        y = height - total_height - padding
    elif position == "bottom-left":
        x = padding
        y = height - total_height - padding
    elif position == "bottom-right":
        x = width - total_width - padding
        y = height - total_height - padding
    else:
        x = (width - total_width) // 2
        y = (height - total_height) // 2

    if sig_text:
        draw.text((x, y), sig_text, font=sig_font, fill=(0, 0, 0, 230))
        y += sig_height + 10

    if author_text:
        draw.text((x, y), author_text, font=author_font, fill=(100, 100, 100, 200))

    return Image.alpha_composite(img, overlay)


def add_numbering(
    image: Image.Image,
    number: int,
    total: int,
    style: str = "circle",
    position: str = "top-right",
) -> Image.Image:
    img = image.convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    num_size = min(60, max(30, width // 25))
    font = get_font("Microsoft YaHei Bold", num_size)

    text = str(number)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    margin = 30
    padding = 15
    box_size = max(text_width, text_height) + 2 * padding

    positions = {
        "top-left": (margin, margin),
        "top-right": (width - box_size - margin, margin),
        "bottom-left": (margin, height - box_size - margin),
        "bottom-right": (width - box_size - margin, height - box_size - margin),
    }
    x, y = positions.get(position, positions["top-right"])

    if style == "circle":
        draw.ellipse([x, y, x + box_size, y + box_size], fill=(255, 255, 255, 230))
        draw.ellipse([x + 3, y + 3, x + box_size - 3, y + box_size - 3],
                    outline=(255, 100, 100, 255), width=3)
    elif style == "square":
        draw.rectangle([x, y, x + box_size, y + box_size],
                      fill=(255, 100, 100, 230), radius=8)
    else:
        draw.rounded_rectangle([x, y, x + box_size, y + box_size],
                              radius=box_size // 2, fill=(255, 100, 100, 230))

    text_x = x + (box_size - text_width) // 2 - bbox[0]
    text_y = y + (box_size - text_height) // 2 - bbox[1]
    text_color = (0, 0, 0, 255) if style == "circle" else (255, 255, 255, 255)
    draw.text((text_x, text_y), text, font=font, fill=text_color)

    return Image.alpha_composite(img, overlay)


def compose_article_images(
    article: Article,
    theme: Theme,
    presets: list,
    source_dir: Path,
    output_dir: Path,
    fonts_dir: Optional[Path] = None,
    include_quote: bool = True,
    numbering: Optional[Tuple[int, int]] = None,
) -> list:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    source_image = None
    if article.image_path:
        candidate = source_dir / article.image_path
        if candidate.exists():
            source_image = candidate
        else:
            candidate = Path(article.image_path)
            if candidate.exists():
                source_image = candidate

    if not source_image:
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            candidate = source_dir / f"{slugify(article.title)}{ext}"
            if candidate.exists():
                source_image = candidate
                break

    article_slug = slugify(article.title)

    for preset in presets:
        preset_name = preset.name
        cover = create_cover_image(article, theme, preset, source_image, fonts_dir)

        if numbering:
            cover = add_numbering(cover, numbering[0], numbering[1])

        filename = f"{article_slug}_{preset_name}_cover.png"
        output_path = output_dir / filename
        cover.save(output_path, "PNG", dpi=(300, 300))
        generated.append({
            "path": output_path,
            "type": "cover",
            "preset": preset_name,
            "article_id": article.id,
        })

        if include_quote and article.quote:
            quote_card = create_quote_card(article, theme, preset, fonts_dir)
            if numbering:
                quote_card = add_numbering(quote_card, numbering[0], numbering[1])
            quote_filename = f"{article_slug}_{preset_name}_quote.png"
            quote_path = output_dir / quote_filename
            quote_card.save(quote_path, "PNG", dpi=(300, 300))
            generated.append({
                "path": quote_path,
                "type": "quote",
                "preset": preset_name,
                "article_id": article.id,
            })

    return generated
