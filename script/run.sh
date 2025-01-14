
# 日志文件名，以时间戳命名
solution='cuda_migration' #'readme_doc' # 'cuda_migration'
log_file="logs/$solution-$(date +%Y%m%d%H%M%S).log"

# 运行 AgentFlow
python -m AgentFlow.main workflows/$solution/solution.toml -f flow4  | tee -a $log_file
