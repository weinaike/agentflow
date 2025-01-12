import threading

def thread_safe_singleton(cls):
    """线程安全的单实例装饰器"""
    instances = {}
    lock = threading.Lock()  # 锁，用于线程安全

    def get_instance(*args, **kwargs):
        nonlocal instances
        if cls not in instances:
            with lock:  # 确保实例化过程是线程安全的
                if cls not in instances:  # 双重检查，防止重复创建
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
