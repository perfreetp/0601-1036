import os
import re
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
from PIL import Image, ImageOps
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def generate_id(prefix: str = "") -> str:
    unique_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8]
    return f"{prefix}{unique_id}" if prefix else unique_id


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_short() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text[:60]


def get_image_info(image_path: Path) -> dict:
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            info = {
                "path": str(image_path),
                "width": width,
                "height": height,
                "mode": img.mode,
                "format": img.format,
                "size_kb": round(image_path.stat().st_size / 1024, 2),
                "dpi": img.info.get("dpi", (72, 72)),
            }
            return info
    except Exception as e:
        return {"path": str(image_path), "error": str(e)}


def is_low_resolution(image_path: Path, min_width: int = 1920, min_height: int = 1080) -> Tuple[bool, dict]:
    info = get_image_info(image_path)
    if "error" in info:
        return True, info
    is_low = info["width"] < min_width or info["height"] < min_height
    return is_low, info


def find_images(directory: Path, recursive: bool = True) -> List[Path]:
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"}
    if recursive:
        return [p for p in directory.rglob("*") if p.suffix.lower() in extensions]
    return [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in extensions]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def ensure_image_mode(image: Image.Image, mode: str = "RGB") -> Image.Image:
    if image.mode != mode:
        if mode == "RGB" and image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
            return background
        return image.convert(mode)
    return image


def smart_resize(image: Image.Image, target_width: int, target_height: int,
                 crop: bool = True) -> Image.Image:
    original_ratio = image.width / image.height
    target_ratio = target_width / target_height

    if crop:
        if original_ratio > target_ratio:
            new_height = target_height
            new_width = int(new_height * original_ratio)
        else:
            new_width = target_width
            new_height = int(new_width / original_ratio)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (resized.width - target_width) // 2
        top = (resized.height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        return resized.crop((left, top, right, bottom))
    else:
        if original_ratio > target_ratio:
            new_width = target_width
            new_height = int(new_width / original_ratio)
        else:
            new_height = target_height
            new_width = int(new_height * original_ratio)
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def print_header(title: str) -> None:
    console.print()
    console.print(Panel(Text(title, style="bold cyan", justify="center"),
                       border_style="cyan", padding=1))
    console.print()


def print_success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    console.print(f"[yellow]![/yellow] {message}")


def print_info(message: str) -> None:
    console.print(f"[blue]ℹ[/blue] {message}")


def print_table(headers: List[str], rows: List[List[str]], title: str = "") -> None:
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for header in headers:
        table.add_column(header, overflow="fold")
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    console.print(table)


def parse_title_file(filepath: Path) -> List[dict]:
    articles = []
    current = None
    order = 0

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("title:") or line.startswith("标题:"):
            if current:
                articles.append(current)
            order += 1
            current = {
                "id": generate_id("art_"),
                "title": line.split(":", 1)[1].strip(),
                "order": order,
            }
        elif current:
            if line.startswith("subtitle:") or line.startswith("副标题:"):
                current["subtitle"] = line.split(":", 1)[1].strip()
            elif line.startswith("summary:") or line.startswith("摘要:"):
                current["summary"] = line.split(":", 1)[1].strip()
            elif line.startswith("quote:") or line.startswith("引语:"):
                current["quote"] = line.split(":", 1)[1].strip()
            elif line.startswith("author:") or line.startswith("作者:"):
                current["author"] = line.split(":", 1)[1].strip()
            elif line.startswith("keywords:") or line.startswith("关键词:"):
                kw = line.split(":", 1)[1].strip()
                current["keywords"] = [k.strip() for k in kw.split(",")]
            elif line.startswith("image:") or line.startswith("图片:"):
                current["image_path"] = line.split(":", 1)[1].strip()

    if current:
        articles.append(current)

    return articles


def parse_csv_titles(filepath: Path) -> List[dict]:
    import csv
    articles = []
    order = 0

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            order += 1
            article = {
                "id": generate_id("art_"),
                "order": order,
                "title": row.get("title", row.get("标题", "")).strip(),
                "subtitle": row.get("subtitle", row.get("副标题", "")).strip(),
                "summary": row.get("summary", row.get("摘要", "")).strip(),
                "quote": row.get("quote", row.get("引语", "")).strip(),
                "author": row.get("author", row.get("作者", "")).strip(),
                "image_path": row.get("image", row.get("图片", "")).strip(),
            }
            kw = row.get("keywords", row.get("关键词", "")).strip()
            if kw:
                article["keywords"] = [k.strip() for k in kw.split(",")]
            if article["title"]:
                articles.append(article)

    return articles


def parse_json_titles(filepath: Path) -> List[dict]:
    import json
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "articles" in data:
        items = data["articles"]
    else:
        items = [data]

    for i, item in enumerate(items, 1):
        article = {
            "id": item.get("id", generate_id("art_")),
            "order": item.get("order", i),
            "title": item.get("title", ""),
            "subtitle": item.get("subtitle", ""),
            "summary": item.get("summary", ""),
            "quote": item.get("quote", ""),
            "author": item.get("author", ""),
            "keywords": item.get("keywords", []),
            "image_path": item.get("image_path", item.get("image", "")),
        }
        if article["title"]:
            articles.append(article)

    return articles
