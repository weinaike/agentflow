#!/usr/bin/env python3
"""
脚本用于下载 top100_dataset.csv 中列出的所有代码库到指定目录
"""

import os
import csv
import subprocess
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_repos.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def setup_directories():
    """设置目录结构"""
    base_dir = Path("/media/wnk/projects")
    
    if not base_dir.exists():
        logging.info(f"创建目录: {base_dir}")
        base_dir.mkdir(parents=True, exist_ok=True)
    
    return base_dir

def is_git_repo(url):
    """检查是否是 Git 仓库"""
    return url.endswith('.git') or 'github.com' in url

def convert_https_to_git(url):
    """将 HTTPS GitHub URL 转换为 Git 协议 URL"""
    if url.startswith('https://github.com/'):
        # 将 https://github.com/owner/repo.git 转换为 git://github.com/owner/repo.git
        return url.replace('https://github.com/', 'git@github.com:')
    return url

def clone_git_repo(url, project_name, base_dir):
    """克隆 Git 仓库"""
    repo_path = base_dir / project_name
    
    if repo_path.exists():
        logging.info(f"仓库 {project_name} 已存在，跳过")
        return True
    
    # 转换为 Git 协议
    git_url = convert_https_to_git(url)
    
    try:
        logging.info(f"正在克隆 {project_name} 从 {git_url}")
        cmd = ["git", "clone", "--depth", "1", git_url, str(repo_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            logging.info(f"成功克隆 {project_name}")
            return True
        else:
            logging.error(f"克隆 {project_name} 失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logging.error(f"克隆 {project_name} 超时")
        return False
    except Exception as e:
        logging.error(f"克隆 {project_name} 时发生错误: {str(e)}")
        return False

def download_file(url, project_name, base_dir):
    """下载文件"""
    file_path = base_dir / f"{project_name}.tar.xz"
    
    if file_path.exists():
        logging.info(f"文件 {project_name}.tar.xz 已存在，跳过")
        return True
    
    try:
        logging.info(f"正在下载 {project_name} 从 {url}")
        cmd = ["wget", "-O", str(file_path), url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            logging.info(f"成功下载 {project_name}")
            return True
        else:
            logging.error(f"下载 {project_name} 失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logging.error(f"下载 {project_name} 超时")
        return False
    except Exception as e:
        logging.error(f"下载 {project_name} 时发生错误: {str(e)}")
        return False

def check_dependencies():
    """检查必要的依赖"""
    dependencies = ['git', 'wget']
    missing = []
    
    for dep in dependencies:
        try:
            subprocess.run([dep, '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(dep)
    
    if missing:
        logging.error(f"缺少依赖: {', '.join(missing)}")
        logging.error("请安装缺少的依赖后重新运行脚本")
        sys.exit(1)

def main():
    """主函数"""
    logging.info("开始下载 top100 代码库")
    
    # 检查依赖
    check_dependencies()
    
    # 设置目录
    base_dir = setup_directories()
    
    # 读取 CSV 文件
    csv_file = Path(__file__).parent / "top100_dataset.csv"
    
    if not csv_file.exists():
        logging.error(f"CSV 文件不存在: {csv_file}")
        sys.exit(1)
    
    success_count = 0
    failure_count = 0
    total_count = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            url = row['path'].strip()
            project_name = row['project_name'].strip()
            
            if not url or not project_name:
                continue
                
            total_count += 1
            
            logging.info(f"处理 {total_count}: {project_name}")
            
            if is_git_repo(url):
                success = clone_git_repo(url, project_name, base_dir)
            else:
                success = download_file(url, project_name, base_dir)
            
            if success:
                success_count += 1
            else:
                failure_count += 1
            
            logging.info(f"进度: {success_count + failure_count}/{total_count}")
    
    logging.info(f"下载完成! 成功: {success_count}, 失败: {failure_count}, 总计: {total_count}")
    
    if failure_count > 0:
        logging.warning(f"有 {failure_count} 个项目下载失败，请查看日志了解详情")

if __name__ == "__main__":
    main()
