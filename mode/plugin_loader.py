# -*- coding: utf-8 -*-
"""
模式插件自动发现与加载器
"""
import importlib
from pathlib import Path
from typing import Dict, Any
from botpy import logging

_log = logging.get_logger(__name__)

def discover_modes() -> Dict[str, Dict[str, Any]]:
    """
    自动发现 mode 目录下的所有模式插件
    
    Returns:
        Dict[str, Dict[str, Any]]: 模式配置字典，格式与原有 modes 字典兼容
        {
            "exec": {
                "class": Executor,
                "description": "执行系统命令的模式。"
            },
            ...
        }
    """
    modes = {}
    mode_dir = Path(__file__).parent
    
    for item in mode_dir.iterdir():
        # 跳过非目录、私有目录和 __pycache__
        if not item.is_dir() or item.name.startswith('_'):
            continue
        
        # 检查是否存在 core.py
        core_file = item / 'core.py'
        if not core_file.exists():
            _log.warning(f"跳过目录 {item.name}: 缺少 core.py")
            continue
        
        # 构建模块名并导入
        module_name = f"mode.{item.name}.core"
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            _log.error(f"加载模式 {item.name} 失败：{e}")
            _log.warning(f"{item.name} 加载时出错")
            continue
        
        # 查找模式类（目录名首字母大写）
        class_name = item.name.replace('-', '_').replace(' ', '_').capitalize()
        
        # 处理特殊情况：如 image_search -> ImageSearch
        if '_' in item.name:
            parts = item.name.split('_')
            class_name = ''.join(part.capitalize() for part in parts)
        
        if not hasattr(module, class_name):
            _log.warning(f"模式 {item.name} 未找到类 {class_name}，尝试查找 Mode 后缀类")
            # 尝试查找带 Mode 后缀的类
            class_name_with_mode = class_name + "Mode"
            if hasattr(module, class_name_with_mode):
                class_name = class_name_with_mode
            else:
                _log.error(f"模式 {item.name} 未找到有效的模式类")
                continue
        
        mode_class = getattr(module, class_name)
        
        # 获取描述信息
        description = getattr(module, 'DESCRIPTION', 
                            getattr(mode_class, '__doc__', '无描述') or '无描述')
        
        # 清理描述（取第一行）
        if isinstance(description, str):
            description = description.strip().split('\n')[0]
        
        modes[item.name] = {
            'class': mode_class,
            'description': description
        }
        
        _log.info(f"发现模式：{item.name} -> {class_name}")
    
    if not modes:
        _log.warning("未发现任何可用的模式插件")
    
    return modes


def validate_mode(mode_name: str, mode_config: Dict[str, Any]) -> bool:
    """
    验证模式配置是否有效
    
    Args:
        mode_name: 模式名称
        mode_config: 模式配置字典
    
    Returns:
        bool: 是否有效
    """
    if 'class' not in mode_config:
        _log.error(f"模式 {mode_name} 缺少 'class' 配置")
        return False
    
    mode_class = mode_config['class']
    required_methods = ['message_handler', 'command_handler', 'helper']
    
    for method in required_methods:
        if not hasattr(mode_class, method):
            _log.error(f"模式 {mode_name} 缺少必要方法：{method}")
            return False
    
    return True
