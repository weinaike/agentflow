
# 日志文件名，以时间戳命名
solution='comprehension' #'readme_doc' # 'cuda_migration'
log_file="logs/$solution-$(date +%Y%m%d%H%M%S).log"

# 运行 AgentFlow
python3 -m AgentFlow.main workflows/$solution/solution.toml -f flow2  | tee -a $log_file
