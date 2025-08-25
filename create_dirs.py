import os

# 创建目录结构
dirs = [
    'ui',
    'core',
    'utils',
    'cache',
    'cache/texts',
    'cache/summaries',
    'cache/dialogs'
]

for dir_name in dirs:
    os.makedirs(dir_name, exist_ok=True)
    print(f"Created directory: {dir_name}")