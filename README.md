# DesignFlow 创意设计平台 CLI

> 供电子刊物编辑批量生成文章配图和社媒预览的命令行工具

## ✨ 功能特性

### 八组核心命令

| 命令 | 功能 |
|------|------|
| **init** | 建立项目，创建目录结构和配置文件 |
| **import** | 导入标题和图片素材 |
| **theme** | 选择版式主题，自定义色板和字体 |
| **compose** | 批量套用封面、生成引语卡、统一视觉风格 |
| **resize** | 裁切多平台尺寸、自动编号 |
| **caption** | 添加署名、替换水印 |
| **export** | 导出压缩包、生成分享清单 |
| **check** | 检查低清图、预览目录、记录每期配置 |

### 支持的社交平台尺寸

- 微信公众号 (1280×720)
- 微信竖版 (1080×1920)
- 微博 (1080×1080)
- 小红书 3:4 (1080×1440)
- 小红书 1:1 (1080×1080)
- 抖音 (1080×1920)
- B站 (1146×717)
- 知乎 (1920×1080)
- Twitter/X (1600×900)
- LinkedIn (1200×628)

### 内置主题

| 主题 | 风格描述 |
|------|----------|
| **default** | 默认简约 - 简洁大气的现代风格 |
| **elegant** | 典雅商务 - 优雅精致的商务风格 |
| **vibrant** | 活力亮色 - 充满活力的渐变色彩 |
| **dark** | 暗黑模式 - 深色背景搭配亮色文字 |
| **warm** | 温暖治愈 - 暖色调搭配 |

## 🚀 快速开始

### 安装

```bash
# 克隆或下载项目后，在项目根目录执行
pip install -e .
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

### 快速使用流程

```bash
# 1. 初始化项目
designflow init 电子刊 --issue 001 --author "编辑部"

# 2. 导入文章标题（支持 TXT/CSV/JSON）
designflow import titles articles.txt

# 3. 导入图片素材
designflow import images ./raw_images/

# 4. 选择主题
designflow theme use vibrant

# 5. 批量生成配图
designflow compose --sizes wechat,weibo,xiaohongshu

# 6. 调整为各平台尺寸并编号
designflow resize --sizes wechat,weibo --numbering

# 7. 添加水印和署名
designflow caption watermark --text "© 电子刊"
designflow caption signature --author "编辑部"

# 8. 质量检查
designflow check all --fix

# 9. 导出压缩包
designflow export zip --name 第001期素材

# 10. 生成分享清单
designflow export share --format markdown
```

## 📖 命令详解

### init - 初始化项目

```bash
designflow init [项目名] [选项]
```

**选项：**
- `--issue, -i` - 期刊编号，如 001、2024-06
- `--description, -d` - 项目描述
- `--author, -a` - 作者/编辑名称
- `--dir` - 项目根目录（默认为当前目录）
- `--force, -f` - 强制覆盖已存在的项目

**示例：**
```bash
designflow init "科技前沿" --issue 001 --author "科技编辑部"
```

### import - 导入数据

#### 导入标题

```bash
designflow import titles <文件路径> [选项]
```

**支持的文件格式：**

**TXT 格式：**
```
title: 文章标题
subtitle: 副标题
summary: 文章摘要
quote: 引语内容
author: 作者名
keywords: 关键词1, 关键词2
image: 配图文件名.jpg
```

**CSV 格式：**
```csv
title,subtitle,author,quote,image
文章1,副标题1,作者1,引语1,img1.jpg
```

**JSON 格式：**
```json
{
  "articles": [
    {
      "title": "文章标题",
      "subtitle": "副标题",
      "author": "作者",
      "quote": "引语",
      "image": "img.jpg"
    }
  ]
}
```

**选项：**
- `--format, -f` - 指定格式：auto/txt/csv/json
- `--merge, -m` - 合并到现有文章列表
- `--dry-run, -n` - 预览导入结果

#### 导入图片

```bash
designflow import images <目录或文件> [选项]
```

**选项：**
- `--recursive/--no-recursive` - 是否递归扫描子目录
- `--move` - 移动文件而不是复制
- `--pattern, -p` - 文件名过滤模式（如 `*.jpg`）

#### 手动添加文章

```bash
designflow import article --title "标题" --author "作者" --quote "引语"
```

### theme - 主题管理

```bash
# 列出所有主题
designflow theme list

# 查看主题详情
designflow theme show default

# 切换当前主题
designflow theme use vibrant

# 查看当前主题
designflow theme current

# 创建自定义主题
designflow theme create --name mytheme --primary #FF6B6B --base-on default

# 修改主题参数
designflow theme modify default --primary #FF0000 --title-size 80

# 生成主题预览图
designflow theme preview --theme vibrant
```

### compose - 批量合成配图

```bash
designflow compose [选项]
```

**选项：**
- `--theme, -t` - 指定主题（默认使用当前主题）
- `--articles, -a` - 只处理指定文章，如 "1,3,5"
- `--sizes, -s` - 指定尺寸预设，如 "wechat,weibo"
- `--all-sizes` - 生成所有预设尺寸
- `--no-quote` - 不生成引语卡片
- `--no-numbering` - 不添加自动编号
- `--overlay-position` - 文字遮罩位置：top/center/bottom
- `--dry-run, -n` - 预览生成计划

**示例：**
```bash
# 使用指定主题，只生成微信和小红书尺寸
designflow compose --theme elegant --sizes wechat,xiaohongshu

# 只处理前3篇文章
designflow compose --articles 1,2,3 --no-quote
```

### resize - 调整尺寸

```bash
designflow resize [选项]
```

**选项：**
- `--input, -i` - 输入目录
- `--output, -o` - 输出目录
- `--sizes, -s` - 尺寸预设列表
- `--width, -w` / `--height, -h` - 自定义尺寸
- `--crop/--no-crop` - 是否裁切
- `--numbering/--no-numbering` - 添加自动编号
- `--format, -f` - 输出格式：keep/png/jpg/webp
- `--quality, -q` - JPEG/WebP 质量 (1-100)
- `--prefix` - 文件名前缀
- `--start-num` - 自动编号起始值

**查看所有预设尺寸：**
```bash
designflow presets
```

### caption - 添加文字标注

#### 添加水印

```bash
designflow caption watermark [选项]
```

**选项：**
- `--text, -t` - 水印文字
- `--position, -p` - 位置：top-left/top-right/bottom-left/bottom-right/center
- `--opacity` - 透明度 (0.1-1.0)
- `--font-size` - 字号
- `--remove` - 移除水印

#### 添加署名

```bash
designflow caption signature [选项]
```

**选项：**
- `--text, -t` - 签名文字（如栏目名称）
- `--author, -a` - 作者名称
- `--position, -p` - 位置：bottom/bottom-left/bottom-right/center

#### 设置默认值

```bash
designflow caption set --signature "专栏名" --watermark "© 品牌" --author "编辑"
```

### export - 导出

#### 导出压缩包

```bash
designflow export zip [选项]
```

**选项：**
- `--name, -n` - 压缩包名称
- `--input, -i` - 输入目录
- `--output, -o` - 输出路径
- `--no-metadata` - 不包含元数据文件
- `--no-manifest` - 不包含文件清单

#### 生成分享清单

```bash
designflow export share [选项]
```

**选项：**
- `--format, -f` - 格式：markdown/html/csv/json/txt
- `--output, -o` - 输出文件路径

#### 按平台批量导出

```bash
designflow export batch --platforms wechat,weibo --separate-zips
designflow export batch --all-platforms --single-zip
```

#### 导出项目配置

```bash
designflow export config
```

### check - 质量检查

#### 检查图片质量

```bash
designflow check images [选项]
```

**选项：**
- `--min-width` / `--min-height` - 最小尺寸（默认 1920×1080）
- `--source-only` - 只检查源图片目录
- `--fix` - 尝试锐化低清图

#### 检查文章数据

```bash
designflow check articles --fix-order
```

#### 预览项目目录

```bash
designflow check preview --limit 20 --by-type
```

#### 查看操作历史

```bash
designflow check history --limit 10
designflow check history --clear
```

#### 查看/保存配置

```bash
designflow check config
designflow check config --save --name 模板名
```

#### 完整检查

```bash
designflow check all --fix
```

## 📁 项目目录结构

```
项目根目录/
├── designflow.yaml          # 项目配置文件
├── articles.yaml            # 文章数据
├── themes.yaml              # 自定义主题
├── history.yaml             # 操作历史记录
├── source/
│   ├── images/              # 原始图片素材
│   └── titles/              # 导入的标题文件
├── assets/
│   ├── fonts/               # 自定义字体
│   └── templates/           # 配置模板
└── output/
    ├── composed/            # 合成后的封面图和引语卡
    ├── resized/             # 调整尺寸后的图片
    ├── captions/            # 添加水印和署名后的图片
    ├── export/              # 导出的压缩包和清单
    └── preview/             # 预览图
```

## 🛠 技术栈

- **Python 3.9+**
- **Click** - 命令行界面框架
- **Pillow (PIL)** - 图像处理
- **PyYAML** - 配置文件
- **Rich** - 美化终端输出

## 📝 配置文件示例

### designflow.yaml

```yaml
project:
  name: 电子刊名称
  issue: "001"
  description: 项目描述
  created_at: 2024-06-01 12:00:00
  updated_at: 2024-06-01 12:00:00
  current_theme: vibrant
  author: 编辑部
  signature: 专栏名
  watermark: "© 品牌名"
  settings: {}
```

### 自定义主题 themes.yaml

```yaml
themes:
  - name: mytheme
    display_name: 我的主题
    description: 自定义主题
    palette:
      primary: "#FF6B6B"
      secondary: "#4ECDC4"
      accent: "#FFE66D"
      background: "#FFFFFF"
      text: "#2D3436"
      text_light: "#FFFFFF"
    fonts:
      title: "Microsoft YaHei Bold"
      subtitle: "Microsoft YaHei"
      body: "Microsoft YaHei"
      quote: "Georgia Italic"
    layout:
      title_size: 72
      subtitle_size: 36
      padding: 60
      overlay_opacity: 0.3
```

## ❓ 常见问题

**Q: 如何添加自定义字体？**

A: 将 TTF/OTF 字体文件放入 `assets/fonts/` 目录，修改主题配置中的字体名称即可。

**Q: 图片质量不佳怎么办？**

A: 使用 `designflow check images --fix` 尝试锐化，或替换更高分辨率的源图片。

**Q: 如何复现往期的配置？**

A: 使用 `designflow export config` 导出配置，`designflow check config --save` 保存为模板。

**Q: 支持哪些图片格式？**

A: 支持 JPG、PNG、WebP、BMP、TIFF、GIF 等常见格式。

## 📄 许可证

MIT License
