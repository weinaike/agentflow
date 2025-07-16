import os
import subprocess
import shutil
from pathlib import Path
from typing import Union, List, Dict, Any, Annotated
import asyncio
import logging
import json
import difflib
try:
    from .utils import thread_safe_singleton
except ImportError:
    from utils import thread_safe_singleton

logger = logging.getLogger(__name__)

@thread_safe_singleton
class CommandExecutor:
    """命令执行器"""
    
    def __init__(self, working_dir: str = "~"):
        # 正确处理 ~ 路径展开
        if working_dir == "~":
            self.working_dir = Path.home()
        else:
            # 使用 expanduser 来处理可能包含 ~ 的路径
            expanded_path = os.path.expanduser(working_dir)
            self.working_dir = Path(expanded_path)
        # self.working_dir.mkdir(parents=True, exist_ok=True)
        self.current_dir = self.working_dir
        # 维护环境变量状态
        self.env_vars = dict(os.environ)
        
    async def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行shell命令"""
        try:
            # 先分割命令
            commands = self._split_compound_command(command)
            
            all_stdout = []
            all_stderr = []
            final_return_code = 0
            
            # 逐个执行命令
            for cmd in commands:
                cmd = cmd.strip()
                if not cmd:
                    continue
                    
                # 检查是否是环境变量设置命令
                if self._is_env_command(cmd):
                    result = self._handle_env_command(cmd)
                    if result['stderr']:
                        all_stderr.append(result['stderr'])
                    if result['return_code'] != 0:
                        final_return_code = result['return_code']
                    continue
                    
                if cmd.startswith('cd '):
                    # 处理cd命令
                    result = await self._handle_cd_command(cmd)
                    if result['stderr']:
                        all_stderr.append(result['stderr'])
                    if result['return_code'] != 0:
                        final_return_code = result['return_code']
                        # cd失败时，通常应该停止执行后续命令
                        break
                else:
                    # 执行其他命令时传入当前环境变量
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=str(self.current_dir),
                        env=self.env_vars  # 传入维护的环境变量
                    )
                    
                    
                    # 使用流式读取来收集超时前的部分输出
                    stdout_data = b''
                    stderr_data = b''
                    
                    async def read_stdout():
                        nonlocal stdout_data
                        try:
                            while True:
                                chunk = await process.stdout.read(8192)  # 8KB chunks
                                if not chunk:
                                    break
                                stdout_data += chunk
                        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                            # 进程被取消或连接断开，这是正常的
                            pass
                        except Exception as e:
                            # 记录其他异常但继续执行
                            logger.debug(f"Exception in read_stdout: {e}")
                    
                    async def read_stderr():
                        nonlocal stderr_data
                        try:
                            while True:
                                chunk = await process.stderr.read(8192)  # 8KB chunks
                                if not chunk:
                                    break
                                stderr_data += chunk
                        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                            # 进程被取消或连接断开，这是正常的
                            pass
                        except Exception as e:
                            # 记录其他异常但继续执行
                            logger.debug(f"Exception in read_stderr: {e}")
                    
                    try:
                        # 并行读取stdout和stderr，并等待进程结束
                        read_tasks = asyncio.gather(
                            read_stdout(),
                            read_stderr(),
                            process.wait(),
                            return_exceptions=True  # 防止单个任务异常影响整体
                        )
                        
                        await asyncio.wait_for(read_tasks, timeout=timeout)
                        
                        # 进程正常结束，处理输出
                        if stdout_data:
                            stdout_text = stdout_data.decode('utf-8', errors='replace')
                            # 如果内容过长，只保留最后10000个字符
                            if len(stdout_text) > 10000:
                                stdout_text = '内容过长，仅显示最后10000个字符\n' + stdout_text[-10000:]
                            all_stdout.append(stdout_text)
                        
                        if stderr_data:
                            stderr_text = stderr_data.decode('utf-8', errors='replace')
                            # 如果内容过长，只保留最后10000个字符
                            if len(stderr_text) > 10000:
                                stderr_text = '内容过长，仅显示最后10000个字符\n' + stderr_text[-10000:]
                            all_stderr.append(stderr_text)
                        
                        if process.returncode != 0:
                            final_return_code = process.returncode
                            
                    except asyncio.TimeoutError:
                        timeout_msg = f"Command '{cmd}' timed out after {timeout} seconds, content before timeout is in stdout"
                        
                        # 处理超时前收集的stdout数据
                        if stdout_data:
                            stdout_text = stdout_data.decode('utf-8', errors='replace')
                            if len(stdout_text) > 10000:
                                stdout_text = '内容过长，仅显示最后10000个字符\n' + stdout_text[-10000:]
                            all_stdout.append(stdout_text)
                        
                        # 处理超时前收集的stderr数据
                        if stderr_data:
                            stderr_text = stderr_data.decode('utf-8', errors='replace')
                            if len(stderr_text) > 10000:
                                stderr_text = '内容过长，仅显示最后10000个字符\n' + stderr_text[-10000:]
                            timeout_msg += f"\n--- Stderr before timeout ({len(stderr_data)} bytes) ---\n{stderr_text}"
                        
                        all_stderr.append(timeout_msg)
                        final_return_code = -1
                        break                    
            
            return {
                "stdout": '\n'.join(all_stdout),
                "stderr": '\n'.join(all_stderr),
                "return_code": final_return_code,
                "working_dir": str(self.current_dir),
                "success": final_return_code == 0
            }
                
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            # 保留已收集的stdout和stderr信息，并添加异常信息
            if 'all_stdout' in locals():
                collected_stdout = '\n'.join(all_stdout)
            else:
                collected_stdout = ""
            
            if 'all_stderr' in locals():
                collected_stderr = '\n'.join(all_stderr)
                # 在已收集的stderr后添加异常信息
                if collected_stderr:
                    collected_stderr += f"\n\nException occurred: {str(e)}"
                else:
                    collected_stderr = f"Exception occurred: {str(e)}"
            else:
                collected_stderr = f"Exception occurred: {str(e)}"
            
            return {
                "stdout": collected_stdout,
                "stderr": collected_stderr,
                "return_code": -1,
                "working_dir": str(self.current_dir),
                "success": False
            }
    
    async def _handle_cd_command(self, command: str) -> Dict[str, Any]:
        """处理cd命令"""
        try:
            path_part = command.strip()[3:].strip()  # 移除'cd '
            if not path_part or path_part == '~':
                new_dir = self.working_dir
            else:
                if path_part.startswith('/'):
                    new_dir = Path(path_part)
                else:
                    # 处理相对路径中可能包含的 ~ 
                    if path_part.startswith('~'):
                        expanded_path = os.path.expanduser(path_part)
                        new_dir = Path(expanded_path)
                    else:
                        new_dir = self.current_dir / path_part
                new_dir = new_dir.resolve()
            
            # 检查目录是否存在
            if new_dir.exists() and new_dir.is_dir():
                self.current_dir = new_dir
                return {
                    "stdout": "",
                    "stderr": "",
                    "return_code": 0,
                    "working_dir": str(self.current_dir),
                    "success": True
                }
            else:
                return {
                    "stdout": "",
                    "stderr": f"cd: {path_part}: No such file or directory",
                    "return_code": 1,
                    "working_dir": str(self.current_dir),
                    "success": False
                }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"cd: {str(e)}",
                "return_code": 1,
                "working_dir": str(self.current_dir),
                "success": False
            }

    def _is_env_command(self, cmd: str) -> bool:
        """检查是否是环境变量设置命令"""
        cmd_stripped = cmd.strip()
        
        # 检查 export 命令
        if cmd_stripped.startswith('export '):
            return True
            
        # 检查 VAR=value 格式（排除一些特殊情况）
        if '=' in cmd_stripped and not cmd_stripped.startswith(('test ', 'if ', '[ ', '[[ ')):
            # 确保不是比较操作或其他命令
            # 简单检查：如果 = 前面是合法的变量名
            equal_pos = cmd_stripped.find('=')
            if equal_pos > 0:
                var_part = cmd_stripped[:equal_pos].strip()
                # 检查是否是合法的变量名（字母、数字、下划线，且不以数字开头）
                if var_part.replace('_', '').replace('-', '').isalnum() and not var_part[0].isdigit():
                    return True
                    
        # 检查 unset 命令
        if cmd_stripped.startswith('unset '):
            return True
            
        return False

    def _handle_env_command(self, cmd: str) -> Dict[str, Any]:
        """处理环境变量设置命令"""
        try:
            cmd_stripped = cmd.strip()
            
            if cmd_stripped.startswith('export '):
                # 处理 export VAR=value 或 export VAR
                env_part = cmd_stripped[7:].strip()
                
                if '=' in env_part:
                    # export VAR=value
                    var_name, var_value = env_part.split('=', 1)
                    var_name = var_name.strip()
                    # 处理引号
                    var_value = self._process_env_value(var_value.strip())
                    self.env_vars[var_name] = var_value
                    return {
                        "stdout": "",
                        "stderr": "",
                        "return_code": 0,
                        "working_dir": str(self.current_dir),
                        "success": True
                    }
                else:
                    # export VAR (导出已存在的变量)
                    var_name = env_part.strip()
                    if var_name in self.env_vars:
                        # 变量已存在，标记为导出（在我们的实现中所有变量都是导出的）
                        return {
                            "stdout": "",
                            "stderr": "",
                            "return_code": 0,
                            "working_dir": str(self.current_dir),
                            "success": True
                        }
                    else:
                        return {
                            "stdout": "",
                            "stderr": f"export: {var_name}: not found",
                            "return_code": 1,
                            "working_dir": str(self.current_dir),
                            "success": False
                        }
                        
            elif cmd_stripped.startswith('unset '):
                # 处理 unset VAR
                var_names = cmd_stripped[6:].strip().split()
                for var_name in var_names:
                    var_name = var_name.strip()
                    if var_name in self.env_vars:
                        del self.env_vars[var_name]
                        
                return {
                    "stdout": "",
                    "stderr": "",
                    "return_code": 0,
                    "working_dir": str(self.current_dir),
                    "success": True
                }
                
            elif '=' in cmd_stripped:
                # 处理 VAR=value
                var_name, var_value = cmd_stripped.split('=', 1)
                var_name = var_name.strip()
                var_value = self._process_env_value(var_value.strip())
                self.env_vars[var_name] = var_value
                
                return {
                    "stdout": "",
                    "stderr": "",
                    "return_code": 0,
                    "working_dir": str(self.current_dir),
                    "success": True
                }
            else:
                return {
                    "stdout": "",
                    "stderr": f"Invalid environment command: {cmd}",
                    "return_code": 1,
                    "working_dir": str(self.current_dir),
                    "success": False
                }
                
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Error processing environment command: {str(e)}",
                "return_code": 1,
                "working_dir": str(self.current_dir),
                "success": False
            }

    def _process_env_value(self, value: str) -> str:
        """处理环境变量值，包括引号处理和变量替换"""
        # 去除外层引号
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        
        # 处理变量替换 $VAR 和 ${VAR}
        import re
        
        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            return self.env_vars.get(var_name, '')
        
        # 替换 ${VAR} 和 $VAR 格式的变量
        value = re.sub(r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)', replace_var, value)
        
        return value

    def _split_compound_command(self, command: str) -> List[str]:
        """分割复合命令，支持 ; && || & 分隔符，但保持heredoc、括号分组和转义的完整性"""
        import re
        
        # 预处理：处理反斜杠续行
        command = self._handle_line_continuation(command)
        
        # 检查是否包含heredoc语法
        if '<<' in command:
            heredoc_match = re.search(r'<<\s*[\'"]?(\w+)[\'"]?', command)
            if heredoc_match:
                delimiter = heredoc_match.group(1)
                # 检查是否有完整的heredoc（包含结束标记）
                if f'\n{delimiter}' in command or command.endswith(delimiter):
                    # 找到heredoc的结束位置
                    end_pattern = f'\n{delimiter}'
                    end_pos = command.find(end_pattern)
                    if end_pos != -1:
                        heredoc_end = end_pos + len(end_pattern)
                        
                        # 分割heredoc之前的命令
                        heredoc_start = command.find('<<')
                        before_heredoc = command[:heredoc_start].rstrip()
                        
                        # 查找最后一个分隔符在heredoc之前
                        split_positions = []
                        for pattern, length in [('&&', 2), ('||', 2), (';', 1)]:
                            pos = before_heredoc.rfind(pattern)
                            if pos >= 0:
                                split_positions.append((pos, length))
                        
                        # 构建命令列表
                        commands = []
                        if split_positions:
                            split_pos, split_len = max(split_positions, key=lambda x: x[0])
                            first_cmd = command[:split_pos].strip()
                            if first_cmd:
                                commands.append(first_cmd)
                        
                        # heredoc命令部分
                        heredoc_cmd = command[:heredoc_end]
                        if split_positions:
                            split_pos, split_len = max(split_positions, key=lambda x: x[0])
                            heredoc_cmd = command[split_pos + split_len:heredoc_end].strip()
                        if heredoc_cmd:
                            commands.append(heredoc_cmd)
                        
                        # heredoc之后的命令
                        after_heredoc = command[heredoc_end:].strip()
                        if after_heredoc:
                            # 递归处理heredoc之后的命令
                            after_commands = self._split_compound_command(after_heredoc)
                            commands.extend(after_commands)
                        
                        return commands if commands else [command]
                    else:
                        return [command]
        
        # 主要的分割逻辑，支持括号分组
        commands = []
        current_cmd = ""
        i = 0
        in_quotes = False
        quote_char = None
        paren_depth = 0
        in_backticks = False
        
        while i < len(command):
            char = command[i]
            
            # 处理转义字符
            if char == '\\' and i + 1 < len(command):
                current_cmd += char + command[i + 1]
                i += 2
                continue
            
            # 处理反引号
            if char == '`' and not in_quotes:
                in_backticks = not in_backticks
            
            # 处理引号
            if char in ['"', "'"] and not in_quotes and not in_backticks:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            
            # 处理括号深度（只在非引号且非反引号状态下）
            if not in_quotes and not in_backticks:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
            
            # 只在非引号、非反引号且非括号内部时进行分割
            if not in_quotes and not in_backticks and paren_depth == 0:
                if char == ';':
                    if current_cmd.strip():
                        commands.append(current_cmd.strip())
                    current_cmd = ""
                    i += 1
                    continue
                elif char == '&':
                    if i + 1 < len(command) and command[i + 1] == '&':
                        # 处理 &&
                        if current_cmd.strip():
                            commands.append(current_cmd.strip())
                        current_cmd = ""
                        i += 2
                        continue
                    elif i + 1 < len(command) and command[i + 1] == '>':
                        # 处理 &> 重定向，不分割
                        pass
                    elif (i > 0 and command[i-1].isdigit()) or (i + 1 < len(command) and command[i+1].isdigit()):
                        # 处理重定向中的 &，如 2>&1 或 &1，不分割
                        pass
                    else:
                        # 检查是否是行尾的&（后台执行）
                        remaining = command[i+1:].strip()
                        if not remaining:
                            # 行尾的&，是后台执行标记，包含在当前命令中
                            pass
                        else:
                            # 中间的&，分割命令
                            current_cmd += char
                            if current_cmd.strip():
                                commands.append(current_cmd.strip())
                            current_cmd = ""
                            i += 1
                            continue
                elif char == '|' and i + 1 < len(command) and command[i + 1] == '|':
                    # 处理 ||
                    if current_cmd.strip():
                        commands.append(current_cmd.strip())
                    current_cmd = ""
                    i += 2
                    continue
            
            current_cmd += char
            i += 1
        
        if current_cmd.strip():
            commands.append(current_cmd.strip())
        
        return commands
    
    def _handle_line_continuation(self, command: str) -> str:
        """处理反斜杠续行"""
        # 将 \\\n 或 \\\r\n 替换为空格，表示续行
        import re
        # 处理 \\\n 和 \\\r\n 两种情况（注意：字符串中的\\表示一个反斜杠）
        command = re.sub(r'\\\r?\n\s*', ' ', command)
        return command



async def run_command(command: str, timeout: int = 300) -> Dict[str, Any]:
    """
    执行shell命令
    Args:
        command (str): 要执行的shell命令
        timeout (int): 超时时间（秒），默认300秒
    Returns:
        Dict[str, Any]: 命令执行结果的字典
    """
    logger.info(f"Executing command: {command}")
    executor = CommandExecutor()
    result = await executor.execute_command(command, timeout)
    return result


async def get_working_directory() -> str:
    """
    获取当前工作目录
    Returns:
        str: 当前工作目录路径
    """
    executor = CommandExecutor()
    return str(executor.current_dir)


async def list_directory(path: str = ".") -> Dict[str, Any]:
    """
    列出目录内容
    Args:
        path (str): 目录路径，默认为当前目录
    Returns:
        Dict[str, Any]: 目录内容的字典
    """
    executor = CommandExecutor()
    try:
        if path == ".":
            target_path = executor.current_dir
        elif path.startswith('/'):
            target_path = Path(path)
        else:
            target_path = executor.current_dir / path
            
        if not target_path.exists():
            return {"error": f"Path does not exist: {path}"}
            
        if not target_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}
            
        items = []
        for item in sorted(target_path.iterdir()):
            stat = item.stat()
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "permissions": oct(stat.st_mode)[-3:]
            })
            
        return {
            "path": str(target_path),
            "items": items
        }
        
    except Exception as e:
        logger.error(f"List directory error: {e}")
        return {"error": str(e)}


async def read_file(file_path: str, start_line: int = 1, end_line: int = None, encoding: str = "utf-8", show_line_numbers: bool = True) -> Dict[str, Any]:
    """
    读取文件内容, 支持指定行范围(从1开始)；对于大文件，建议使用分页读取；
    Args:
        file_path (str): 文件绝对路径
        start_line (int): 起始行号，默认1（包含）
        end_line (int): 结束行号，默认None（读取到文件末尾，包含）
        encoding (str): 文件编码，默认utf-8
        show_line_numbers (bool): 是否显示行号，默认True
    Returns:
        Dict[str, Any]: 文件内容或错误信息的字典
    """
    executor = CommandExecutor()
    try:
        if file_path.startswith('/'):
            target_path = Path(file_path)
        else:
            target_path = executor.current_dir / file_path
            
        if not target_path.exists():
            return {"error": f"File does not exist: {file_path}"}
            
        if not target_path.is_file():
            return {"error": f"Path is not a file: {file_path}"}
        
        # 参数验证
        if start_line < 1:
            start_line = 1
        
        if end_line is not None and end_line < start_line:
            end_line = start_line

        with open(target_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        
        # 如果起始行超出文件范围
        if start_line > total_lines:
            return {
                "file_path": str(target_path),
                "total_lines": total_lines,               
                "start_line": start_line,
                "end_line": end_line,
                "content": "",
                "actual_lines_read": 0,
                "message": f"start_line {start_line} exceeds file length {total_lines}"
            }
        
        # 确定实际的结束行
        actual_end_line = min(end_line, total_lines) if end_line is not None else total_lines
        
        # 提取指定行范围的内容（Python数组索引从0开始，所以要减1）
        selected_lines = lines[start_line-1:actual_end_line]
        
        # 处理内容格式化
        if show_line_numbers:
            # 计算行号宽度，用于对齐
            max_line_num = start_line + len(selected_lines) - 1
            line_num_width = len(str(max_line_num))
            
            # 添加行号
            formatted_lines = []
            for i, line in enumerate(selected_lines):
                current_line_num = start_line + i
                # 移除原有的换行符，然后添加格式化的行号
                line_content = line.rstrip('\n\r')
                formatted_line = f"{current_line_num:>{line_num_width}}: {line_content}\n"
                formatted_lines.append(formatted_line)
            
            content = ''.join(formatted_lines)
        else:
            content = ''.join(selected_lines)
        
        return {
            "file_path": str(target_path),
            "total_lines": total_lines,
            "start_line": start_line,
            "end_line": actual_end_line,
            "content": content,
            "actual_lines_read": len(selected_lines),
            "size": len(content),
            "show_line_numbers": show_line_numbers
        }
        
    except Exception as e:
        logger.error(f"Read file error: {e}")
        return {"error": str(e)}


async def write_file(file_path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    写入文件内容
    Args:
        file_path (str): 文件具体对路径
        content (str): 文件内容
        encoding (str): 文件编码，默认utf-8
    Returns:
        Dict[str, Any]: 操作结果的字典
    """
    try:
        executor = CommandExecutor()
        if file_path.startswith('/'):
            target_path = Path(file_path)
        else:
            target_path = executor.current_dir / file_path
            
        # 创建父目录
        target_path.parent.mkdir(parents=True, exist_ok=True)
            
        with open(target_path, 'w', encoding=encoding) as f:
            f.write(content)
            
        return {
            "file_path": str(target_path),
            "message": "File written successfully",
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Write file error: {e}")
        return {"error": str(e)}


async def get_environment() -> Dict[str, Any]:
    """
    获取详细的环境信息，包括系统信息、编译工具版本、硬件信息等
    Returns:
        Dict[str, Any]: 环境信息的字典
    """
    try:
        executor = CommandExecutor()
        env_info = {
            "python_version": os.sys.version,
            "platform": os.name,
            "working_directory": str(executor.current_dir),
            "environment_variables": dict(os.environ),
            "path": os.environ.get('PATH', '').split(os.pathsep)
        }
        
        # 定义要执行的命令列表
        commands = {
            # 基础工具位置检查 - 使用bash显式调用
            "tool_locations": "bash -c 'for tool in gcc g++ make cmake git python python3 pip pip3  pkg-config ; do echo -n \"$tool: \"; which $tool 2>/dev/null || echo \"not found\"; done'",            
            # 编译器版本信息
            "gcc_version": "gcc --version 2>/dev/null | head -3",
            "gpp_version": "g++ --version 2>/dev/null | head -3", 
            "gcc_standards": "echo | gcc -dM -E -x c++ - 2>/dev/null | grep __cplusplus",
            "gcc_supported_standards": "gcc -v --help 2>&1 | grep -E 'std=c\\+\\+' | head -5",           
            
            # 构建工具版本
            "cmake_version": "cmake --version 2>/dev/null | head -3",
            "make_version": "make --version 2>/dev/null | head -3",

            # 包管理工具
            "pkg_config_version": "pkg-config --version 2>/dev/null",
            "pkg_config_path": "pkg-config --variable pc_path pkg-config 2>/dev/null || echo 'pkg-config path not available'",

            # 系统开发库检查 - 改进命令
            "installed_dev_packages": "bash -c 'if command -v dpkg >/dev/null 2>&1; then dpkg -l 2>/dev/null | grep -E \"(build-essential|libc6-dev|linux-headers|libstdc)\" | head -10; elif command -v rpm >/dev/null 2>&1; then rpm -qa 2>/dev/null | grep -E \"(gcc|glibc-devel|kernel-headers|libstdc)\" | head -10; else echo \"Package manager not available\"; fi'",
            
            # CUDA环境检查（如果存在）
            "nvcc_version": "nvcc --version 2>/dev/null | grep -E '(release|Build)'",
            "nvidia_smi": "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits 2>/dev/null",
            "cuda_paths": "ls -la /usr/local/cuda* 2>/dev/null | head -20",
            
            # 链接器信息
            "ld_version": "ld --version 2>/dev/null | head -3",
            "ld_library_path": "echo \"LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-'(not set)'}\"; echo \"Current library paths:\"; echo \"$LD_LIBRARY_PATH\" | tr ':' '\\n' | head -10",
            "library_search_paths": "ldconfig -v 2>/dev/null | grep '^/' | head -10",
            
            # 系统信息
            "git_version": "git --version 2>/dev/null",
            "system_info": "uname -a 2>/dev/null",
            "os_release": "cat /etc/os-release 2>/dev/null | head -3",
            "cpu_info": "lscpu 2>/dev/null | head -15",
            "memory_info": "free -h 2>/dev/null",
            "disk_info": "df -h 2>/dev/null | head -10",
        }
        
        # 执行所有命令
        for key, cmd in commands.items():
            try:
                result = await executor.execute_command(cmd, timeout=15)
                if result['success']:
                    stdout = result['stdout'].strip()
                    if stdout:
                        env_info[key] = stdout
                    else:
                        env_info[key] = f"Command executed successfully but returned no output"
                else:
                    stderr = result['stderr'].strip()
                    if stderr:
                        env_info[key] = f"Error: {stderr}"
                    else:
                        env_info[key] = f"Command failed with return code {result['return_code']}"
            except Exception as e:
                env_info[key] = f"Exception executing command: {str(e)}"
        
        return env_info
        
    except Exception as e:
        logger.error(f"Get environment error: {e}")
        return {"error": str(e)}


async def glob_search(pattern: str, path: str = '.') -> str:
    """
    使用glob模块在指定路径下查找匹配的文件或目录。
    Args:
        pattern (str): 匹配模式，如 '*.py'、'**/*.cpp' 等。
        path (str): 搜索的起始目录，默认为当前目录。
    Returns:
        list: 匹配到的文件或目录的绝对路径列表。
    Example:
        glob_search('*.py', '/home/user/project')
    """
    import glob
    search_path = os.path.join(path, pattern)
    # recursive=True 支持 ** 通配符
    results = glob.glob(search_path, recursive=True)
    merge = ';'.join(results)
    if len(merge) > 10000:
        merge = merge[:10000] + '... (truncated)'
    return merge


def run_shell_code(code:Annotated[str, "The shell code to run"], 
                   path:Annotated[str, "the directory to run the shell code"] = None) -> str:
    '''
    run_shell_code: Run the shell code in the given path

    Args:
        code (Annotated[str, "The shell code to run"]): The shell code to run

        path (Annotated[str, "the directory to run the shell code"]): The directory to run the shell code

    Returns:
        str: The output of the shell code

    Example:    
        code = """
        ls
        """
        print(run_shell_code(code))
        # Output: file1 file2 file3
        
    '''
    if path is None:
        result = subprocess.run(code, shell=True, text=True, capture_output=True)
    else:
        result = subprocess.run(code, shell=True, text=True, capture_output=True, cwd=path)
    output = {'stdout':result.stdout if len(result.stdout) < 10000 else result.stdout[-10000:], 
              'stderr':result.stderr if len(result.stderr) < 10000 else result.stderr[-10000:], 
              'returncode':result.returncode}
    return json.dumps(output)



def get_derived_class_of_function(func:Annotated[str, "function"], src_path:Annotated[str, "path to source code"])->str:
    '''
        查询函数的所有派生类实现，由于查询的时派生类是否实现，因而需要提供源码路径（绝对路径）

        Args: 
            func (str): 函数名
            src_path (str): 源码路径（绝对路径）

        Returns:
            str: 查询到的信息

        Example:
            ret = get_derived_class_of_function("shoot", "/home/jiangbo/project/src")

            ret = """
        src/SBVonKarman.cpp:    void VonKarmanInfo::shoot(PhotonArray& photons, UniformDeviate ud) const
        src/SBVonKarman.cpp:    void SBVonKarman::SBVonKarmanImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        src/SBConvolve.cpp:    void SBConvolve::SBConvolveImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        src/SBConvolve.cpp:    void SBAutoConvolve::SBAutoConvolveImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        src/SBConvolve.cpp:    void SBAutoCorrelate::SBAutoCorrelateImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        """
    '''
    
    item = func.split('::')
    if len(item) == 1:
        cmd = 'grep -r "::{}" {}'.format(func, src_path)
    else:
        func = item[-1]
        cmd = 'grep -r "::{}" {}'.format(func, src_path)
    return run_shell_code(cmd)


def get_derived_class_of_class(class_name:Annotated[str, "class name"], inc_path:Annotated[str, "path to include code"])->str:
    '''
    查询类的所有派生类， 由于派生类声明代码文件通常放在头文件目录， 因而需要提供头文件目录（绝对路径）

    Args:
        class_name (str): 类名
        inc_path (str): 头文件路径（绝对路径）

    return:
        str: 查询到的信息

    Example:
        ret = get_derived_class_of_class("SBProfile", "/home/wnk/code/GalSim/include/galsim/")

        ret = """
    /home/wnk/code/GalSim/include/galsim/SBMoffatImpl.h:    class SBMoffat::SBMoffatImpl : public SBProfileImpl
    /home/wnk/code/GalSim/include/galsim/SBInclinedExponentialImpl.h:    class SBInclinedExponential::SBInclinedExponentialImpl : public SBProfileImpl
    /home/wnk/code/GalSim/include/galsim/SBTransformImpl.h:    class SBTransform::SBTransformImpl : public SBProfileImpl
    “”“
    '''    
    
    
    cmd = 'grep -r ": public {}" {}'.format(class_name, inc_path)
    return run_shell_code(cmd)


def run_cmake_and_make(path:Annotated[str, "The path to the bulid directory"])->str:  

    '''
    run_cmake_and_make: Run cmake and make in the given path to build the project

    Args:
        path (Annotated[str, "The path to the bulid directory"]): The path to the bulid directory

        the following commands will be run in the given path:
        cmake command : cmake .. -DENABLE_CUDA=ON
        make command : make -j12
        make build command : make build    

    Returns:
        str: The output of the cmake and make command

    Example:
        path = "/home/jiangbo/galsim_cuda/build"
        print(run_cmake_and_make(path))
        # Output: 
        # -- Configuring done
        # -- Generating done
        # -- Build files have been written to: /home/jiangbo/galsim_cuda/build
        # Scanning dependencies of target galsim_cuda
        # [ 50%] Building CXX object CMakeFiles/galsim_cuda.dir/galsim_cuda.cpp.o
        # [100%] Linking CXX shared library libgalsim_cuda.so
        # [100%] Built target galsim_cuda

    '''

    subprocess.run(['rm', 'CMakeCache.txt'], cwd=path, text=True, capture_output=True)  
    cmake_result = subprocess.run(['cmake', '..', '-DENABLE_CUDA=ON'], cwd=path, text=True, capture_output=True)
    if cmake_result.stderr:
        return cmake_result.stderr
    make_result = subprocess.run(['make', 'DEFINES="-DENABLE_CUDA"', '-j12'], cwd=path, text=True, capture_output=True)
    if make_result.stderr:
        return make_result.stderr
    
    return cmake_result.stdout + make_result.stdout

def run_make(path:Annotated[str, "The path to the bulid directory"])->str:    
    '''
    run_make: Run make in the given path to build the project

    Args:
        path (Annotated[str, "The path to the bulid directory"]): The path to the bulid directory

        the following commands will be run in the given path:
        make command : make
        make build command : make build

    Returns:
        str: The output of make command
    '''

    subprocess.run(['rm', 'CMakeCache.txt'], cwd=path, text=True, capture_output=True)

    cmake_result = subprocess.run(['cmake', '..', '-DENABLE_CUDA=ON'], cwd=path, text=True, capture_output=True)
    if cmake_result.stderr:
        return cmake_result.stderr    
    make_result = subprocess.run(['make', 'DEFINES="-DENABLE_CUDA"', '-j12'], cwd=path, text=True, capture_output=True)
    if make_result.stderr:
        return make_result.stderr
    make_build_result = subprocess.run(['make', 'install'], cwd=path, text=True, capture_output=True)
    if make_build_result.stderr:        
        return  make_build_result.stderr
    test_result = subprocess.run(['python', '../examples/demo0.py'], cwd=path, text=True, capture_output=True)
    if test_result.stderr:        
        return  test_result.stderr    
    
    return make_result.stdout + make_build_result.stdout + test_result.stdout




def run_python_code(code:Annotated[str, "The python code to run"], 
                    path:Annotated[str, "the directory to run the python code"] = None)->str:
    '''
    run_python_code: Run the python code in the given path

    Args:
        code (Annotated[str, "The python code to run"]): The python code to run

        path (Annotated[str, "the directory to run the python code"]): The directory to run the python code

    Returns:
        str: The output of the python code

    Example:    
        code = """
        print("Hello World")
        """
        print(run_python_code(code))
        # Output: Hello World


    '''

    if path is None:
        result = subprocess.run(['python3', '-c', code], text=True, capture_output=True)
    else:
        result = subprocess.run(['python3', '-c', code], cwd=path, text=True, capture_output=True)
    if result.stderr:
        return result.stderr
    return result.stdout



def get_cpp_dir_structure(path:Annotated[Union[str, List[str]], "The path to the directory"])->dict:
    '''
    "
    get_cpp_dir_structure: Get the directory structure of the given path. find all the .cpp, .cu, .h, .cuh, .c files

    Args:
        path (Annotated[Union[str, List[str]], '']): The path to the directory

    Returns:
        dict: The directory structure of the given path

    Example: 
        path = ['/home/jiangbo/galsim_cuda/']
        print(get_cpp_dir_structure(path))
    "
    '''
    special_files = ['makefile', 'cmakelists.txt', 'readme.md']

    dir_structure = {}
    if isinstance(path, str):
        path = [path]
    
    for p in path:           
        for root, dirs, files in os.walk(p):

            root = root.replace(p, "")
            root = root.replace("\\", "/")
            if root.startswith('build') or root.startswith('CMakeFiles') or root.startswith('cmake'):
                continue
            if root == "":
                root = p
            for file in files:
                if file.endswith((".cpp", ".cu", ".h", ".cuh", ".c")) or file.lower() in special_files:
                    if root not in dir_structure:
                        dir_structure[root] = []
                    dir_structure[root].append(file)
    return dir_structure


def get_dir_structure_with_tree_cmd(path:Annotated[ Union[str, List[str]], "The path to the directory"], 
                                    directories_only: Annotated[bool, "" ]= False) -> str:
    '''
    "
    get_dir_structure_with_tree_cmd: Get the directory structure of the given path

    Args:
        path (Annotated[Union[str, List[str]], '']): The path to the directory

    Returns:
        dict: The directory structure of the given path

    Example: 
        path = ['/home/jiangbo/galsim_cuda/']
        print(get_dir_structure_with_tree_cmd(path))
    "
    '''    
    command = ['tree']
    if directories_only:
        command.append('-d')
    if isinstance(path, list):
        command.extend(path)
    else:
        command.append(path)

    result = subprocess.run(command, text=True, capture_output=True)

    if result.stderr:
        return result.stderr
    return result.stdout


def show_dir_content(path:Annotated[ Union[str, List[str]], "The path to the directory"]) -> str:
    '''
    "
    show_dir_content: Get the directory structure of the given path

    Args:
        path (Annotated[Union[str, List[str]], '']): The path to the directory

    Returns:
        dict: The directory structure of the given path

    Example: 
        path = ['/home/wnk/code/galsim_cuda/']
        print(show_dir_content(path))
    "
    '''    
    command = ['tree']
    command.append('-L')
    command.append('1')
    if isinstance(path, list):
        command.extend(path)
    else:
        command.append(path)

    result = subprocess.run(command, text=True, capture_output=True)

    if result.stderr:
        return result.stderr + "\n请安装工具后重试"
    return result.stdout



def file_backup(source: str, backup_dir: str) -> str:
    """
    Backs up the source file to the specified backup directory.
    Returns the backup file path.
    """
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    filename = os.path.basename(source)
    destination = os.path.join(backup_dir, filename)
    shutil.copy2(source, destination)
    
    ret = f' File {source} is backed up to {destination}'

    return ret


if __name__ == '__main__':
    # print(get_cpp_dir_structure('/home/wnk/code/GalSim/'))
    command = 'find / -name *.h*'

    # # command = 'ls -l /home/wnk/code/GalSim/ && ls -l /home/wnk/code/GalSim/include/ && ls -l /home/wnk/code/GalSim/src/'
    # json_str = '{"command":"cd /root/project \\u0026\\u0026 bash scripts/deps.sh 4","timeout":10}'
    # json_data = json.loads(json_str)
    # command = json_data['command']
    # print(command)
    # executor = CommandExecutor()
    # command = "cd /root/project/build &&  cmake .. -DCMAKE_BUILD_TYPE=Release -DLLVM_DIR=/usr/lib/llvm-15/lib/cmake/llvm"
    result = asyncio.run(run_command(command, timeout=1))
    print(result)
    # # print(result['stdout'])
    # a = run_shell_code(command)
    # b = {'result': a}
    # print(json.dumps(b))