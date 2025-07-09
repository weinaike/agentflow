# 代码库下载脚本

这个脚本用于下载 `top100_dataset.csv` 中列出的所有代码库到 `/media/wnk/projects` 目录。

## 文件说明

- `download_repos.py` - Python 版本的下载脚本
- `download_repos.sh` - Bash 版本的下载脚本
- `top100_dataset.csv` - 包含代码库列表的 CSV 文件

## 功能特性

1. **自动检测仓库类型**: 自动识别 Git 仓库和普通文件下载
2. **断点续传**: 如果目录或文件已存在，会跳过下载
3. **超时控制**: 每个下载任务有 1 小时的超时限制
4. **详细日志**: 记录所有操作到日志文件
5. **进度显示**: 实时显示下载进度
6. **错误处理**: 优雅处理各种错误情况

## 使用方法

### 使用 Python 脚本

```bash
cd /home/wnk/code/agentflow/script
python3 download_repos.py
```

### 使用 Bash 脚本

```bash
cd /home/wnk/code/agentflow/script
./download_repos.sh
```

## 依赖要求

- `git` - 用于克隆 GitHub 仓库
- `wget` - 用于下载文件
- `python3` - 如果使用 Python 脚本

在 Ubuntu/Debian 系统上安装依赖：

```bash
sudo apt update
sudo apt install git wget python3
```

## 下载内容

脚本会下载以下类型的项目：

1. **GitHub 仓库**: 使用 `git clone --depth 1` 进行浅克隆
2. **SourceForge 文件**: 使用 `wget` 下载压缩文件

## 目录结构

下载完成后，`/media/wnk/projects` 目录下会包含：

```
/media/wnk/projects/
├── gcc/                    # Git 仓库
├── 8cc/                    # Git 仓库
├── tensorflow/             # Git 仓库
├── codeblocks.tar.xz       # 压缩文件
└── ...
```

## 日志文件

所有操作都会记录到 `download_repos.log` 文件中，包括：
- 成功下载的项目
- 失败的项目及错误信息
- 跳过的项目（已存在）

## 注意事项

1. **磁盘空间**: 这些项目的总大小可能很大（数百 GB），请确保有足够的磁盘空间
2. **网络连接**: 下载过程需要稳定的网络连接
3. **执行时间**: 完整下载可能需要数小时，建议在后台运行
4. **权限**: 确保对目标目录有写入权限

## 后台运行

如果想在后台运行脚本：

```bash
# Python 版本
nohup python3 download_repos.py > download.log 2>&1 &

# Bash 版本
nohup ./download_repos.sh > download.log 2>&1 &
```

## 监控进度

可以通过以下方式监控下载进度：

```bash
# 查看日志
tail -f download_repos.log

# 查看已下载的项目数量
ls -1 /media/wnk/projects | wc -l
```

## 故障排除

1. **权限问题**: 确保对目标目录有写入权限
2. **网络问题**: 检查网络连接，某些仓库可能需要 VPN
3. **磁盘空间**: 确保有足够的磁盘空间
4. **依赖缺失**: 安装所需的依赖程序

## 自定义配置

如果需要修改下载目录，可以编辑脚本中的 `BASE_DIR` 变量：

```python
# Python 脚本中
base_dir = Path("/your/custom/path")
```

```bash
# Bash 脚本中
BASE_DIR="/your/custom/path"
```
