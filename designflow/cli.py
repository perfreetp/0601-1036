import click
import sys
from pathlib import Path

from . import __version__, __app_name__
from .commands.cmd_init import init
from .commands.cmd_import import import_cmd
from .commands.cmd_theme import theme
from .commands.cmd_compose import compose
from .commands.cmd_resize import resize, list_presets
from .commands.cmd_caption import caption
from .commands.cmd_export import export
from .commands.cmd_check import check

from .utils import console, print_header


@click.group()
@click.version_option(__version__, prog_name=__app_name__)
@click.option("--verbose", "-v", is_flag=True, help="显示详细输出")
@click.pass_context
def cli(ctx, verbose):
    """
    DesignFlow - 创意设计平台命令行工具

    供电子刊物编辑批量生成文章配图和社媒预览。

    快速开始:

      1. designflow init 项目名 --issue 001    # 初始化项目

      2. designflow import titles 文章.txt       # 导入标题

      3. designflow import images ./images/      # 导入图片

      4. designflow theme use vibrant            # 选择主题

      5. designflow compose                      # 批量合成配图

      6. designflow resize --sizes wechat,weibo  # 调整尺寸

      7. designflow caption watermark            # 添加水印

      8. designflow check all --fix              # 质量检查

      9. designflow export zip                   # 导出压缩包
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


cli.add_command(init)
cli.add_command(import_cmd, name="import")
cli.add_command(theme)
cli.add_command(compose)
cli.add_command(resize)
cli.add_command(list_presets, name="presets")
cli.add_command(caption)
cli.add_command(export)
cli.add_command(check)


@cli.command("info")
def show_info():
    """
    显示工具信息和版本。
    """
    print_header("DesignFlow 创意设计平台")
    console.print()
    console.print(f"[bold]版本:[/bold] {__version__}")
    console.print(f"[bold]Python:[/bold] {sys.version.split()[0]}")
    console.print(f"[bold]工作目录:[/bold] {Path.cwd()}")
    console.print()
    console.print("[bold]可用命令:[/bold]")
    commands = [
        ("init", "初始化新项目"),
        ("import", "导入标题和图片"),
        ("theme", "管理主题和色板"),
        ("compose", "批量合成配图"),
        ("resize", "调整多平台尺寸"),
        ("presets", "查看尺寸预设"),
        ("caption", "添加水印和署名"),
        ("export", "导出压缩包和清单"),
        ("check", "质量检查和预览"),
        ("info", "显示工具信息"),
    ]
    for cmd, desc in commands:
        console.print(f"  [cyan]{cmd:<12}[/cyan] {desc}")
    console.print()
    console.print("使用 [cyan]designflow <command> --help[/cyan] 查看命令详细帮助")


@cli.command("docs")
@click.argument("topic", required=False, default="")
def show_docs(topic):
    """
    查看使用文档。
    """
    docs = {
        "": f"""
DesignFlow 使用指南
{'=' * 60}

设计工作流:

  init → import → theme → compose → resize → caption → check → export

命令说明:

  [cyan]designflow init [名称] [选项][/cyan]
    创建新的设计项目，生成目录结构和示例文件。

  [cyan]designflow import titles <文件>[/cyan]
    从 TXT/CSV/JSON 文件导入文章标题、摘要、引语等数据。

  [cyan]designflow import images <目录/文件>[/cyan]
    导入图片素材，自动匹配文章配图。

  [cyan]designflow theme list[/cyan]
    查看所有可用的版式主题和色板。

  [cyan]designflow theme use <主题名>[/cyan]
    切换当前使用的主题。

  [cyan]designflow compose [选项][/cyan]
    批量生成文章封面图和引语卡片，自动应用主题。

  [cyan]designflow resize [选项][/cyan]
    将图片调整为微信、微博、小红书等平台的标准尺寸。

  [cyan]designflow caption watermark [选项][/cyan]
    为图片添加半透明水印。

  [cyan]designflow caption signature [选项][/cyan]
    为图片添加署名和作者信息。

  [cyan]designflow check images[/cyan]
    检查低分辨率图片，确保输出质量。

  [cyan]designflow check all --fix[/cyan]
    执行完整检查并自动修复问题。

  [cyan]designflow export zip[/cyan]
    打包所有生成的图片为压缩包。

  [cyan]designflow export share --format markdown[/cyan]
    生成社交媒体分享清单。

查看具体命令文档:
  [cyan]designflow docs compose[/cyan]
  [cyan]designflow docs theme[/cyan]
  [cyan]designflow docs export[/cyan]
""",

        "compose": """
[bold]compose 命令 - 批量合成配图[/bold]
{'=' * 60}

根据文章内容和当前主题，批量生成封面图和引语卡片。

[bold]基本用法:[/bold]
  designflow compose

[bold]常用选项:[/bold]
  --theme, -t       指定主题（默认使用当前主题）
  --articles, -a    只处理指定文章，如 "1,3,5" 或 "文章标题"
  --sizes, -s       指定尺寸预设，如 "wechat,xiaohongshu"
  --all-sizes       生成所有预设尺寸
  --no-quote        不生成引语卡片
  --no-numbering    不添加自动编号
  --dry-run, -n     预览生成计划，不实际生成

[bold]示例:[/bold]
  # 使用指定主题生成
  designflow compose --theme elegant

  # 只生成前3篇文章
  designflow compose --articles 1,2,3

  # 只生成微信和小红书尺寸
  designflow compose --sizes wechat,xiaahongshu

  # 预览生成计划
  designflow compose --dry-run
""",

        "theme": """
[bold]theme 命令 - 主题管理[/bold]
{'=' * 60}

内置5款主题：
  [cyan]default[/cyan]    默认简约 - 简洁大气的现代风格
  [cyan]elegant[/cyan]    典雅商务 - 优雅精致的商务风格
  [cyan]vibrant[/cyan]    活力亮色 - 充满活力的渐变色彩
  [cyan]dark[/cyan]       暗黑模式 - 深色背景搭配亮色文字
  [cyan]warm[/cyan]       温暖治愈 - 暖色调搭配

[bold]基本用法:[/bold]
  designflow theme list              # 列出所有主题
  designflow theme use vibrant       # 切换主题
  designflow theme show default      # 查看主题详情
  designflow theme current           # 查看当前主题

[bold]创建自定义主题:[/bold]
  designflow theme create --name mytheme \\
    --display-name "我的主题" \\
    --primary #FF6B6B --accent #4ECDC4 \\
    --base-on default

[bold]修改主题参数:[/bold]
  designflow theme modify default \\
    --primary #FF0000 --title-size 80
""",

        "export": """
[bold]export 命令 - 导出[/bold]
{'=' * 60}

[bold]导出压缩包:[/bold]
  designflow export zip
  designflow export zip --name 第001期素材
  designflow export zip --input ./output/resized

[bold]生成分享清单:[/bold]
  designflow export share --format markdown
  designflow export share --format html
  designflow export share --format csv
  designflow export share --format json

[bold]按平台批量导出:[/bold]
  designflow export batch --platforms wechat,weibo
  designflow export batch --all-platforms

[bold]导出配置:[/bold]
  designflow export config           # 导出项目配置
""",
    }

    content = docs.get(topic, docs[""])
    console.print(content)


def main():
    try:
        cli(obj={})
    except click.Abort:
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]错误: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        sys.exit(1)


if __name__ == "__main__":
    main()
