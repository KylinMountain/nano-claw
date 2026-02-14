"""
配置加载器 - 支持YAML配置文件
"""
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """加载配置文件"""
    config = get_default_config()
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
            if user_config:
                # 合并配置
                config = deep_merge(config, user_config)
    
    # 从环境变量读取API密钥
    if not config['llm'].get('api_key'):
        if config['llm']['provider'] == 'openai':
            config['llm']['api_key'] = os.getenv('OPENAI_API_KEY')
        else:
            config['llm']['api_key'] = os.getenv('GEMINI_API_KEY')
    
    # 展开路径中的 ~
    if config['skills'].get('directories'):
        for key, path in config['skills']['directories'].items():
            if path:
                config['skills']['directories'][key] = os.path.expanduser(path)
    
    if config['memory'].get('global_dir'):
        config['memory']['global_dir'] = os.path.expanduser(config['memory']['global_dir'])
    
    return config


def get_default_config() -> Dict[str, Any]:
    """获取默认配置"""
    return {
        'llm': {
            'provider': 'openai',
            'api_key': None,
            'openai': {
                'model': 'gpt-4o-mini',
                'base_url': None
            },
            'gemini': {
                'model': 'gemini-2.0-flash',
                'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai/'
            }
        },
        'agent': {
            'max_turns': 50,
            'temperature': 0.7,
            'enable_compression': True,
            'auto_approve_readonly': True,
            'approval_mode': 'default'
        },
        'system_prompt': '''You are Nano Claw, a helpful AI assistant with access to tools.

When using tools:
1. Explain your intent before calling a tool
2. Use the exact tool name and parameters
3. Wait for results before proceeding
4. Report the outcome to the user

Be concise but thorough in your responses.''',
        'skills': {
            'enabled': True,
            'directories': {
                'builtin': './skills/builtin',
                'user': '~/.nano_claw/skills',
                'workspace': '.nano_claw/skills'
            }
        },
        'memory': {
            'enabled': True,
            'global_dir': '~/.nano_claw'
        },
        'mcp': {
            'enabled': False,
            'servers': {}
        }
    }


def deep_merge(base: Dict, update: Dict) -> Dict:
    """深度合并两个字典"""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def save_config(config: Dict[str, Any], config_path: str = "config.yaml") -> None:
    """保存配置到文件"""
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)