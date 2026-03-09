#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "🚀 开始部署 AI Audio Daily Agent"

# 1. 激活虚拟环境
source venv/bin/activate

# 2. 运行主程序
python main.py

# 3. 清理旧文件（可选）
python -c "from main import AIAudioDailyAgent; AIAudioDailyAgent().cleanup_old_files()"

echo "✅ 部署完成"
