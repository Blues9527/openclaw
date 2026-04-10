#!/bin/bash
# 安装本地 tavily-search skill

SOURCE_DIR="/Users/a58/Downloads/ChromeDownload/openclaw-tavily-search-0.1.0"
TARGET_DIR="/Users/a58/.nvm/versions/node/v24.14.0/lib/node_modules/openclaw/extensions/tavily-search"

# 创建目标目录
mkdir -p "$TARGET_DIR"

# 复制文件
cp -r "$SOURCE_DIR"/* "$TARGET_DIR/"

echo "Skill installed to: $TARGET_DIR"
echo "Files:"
ls -la "$TARGET_DIR/"