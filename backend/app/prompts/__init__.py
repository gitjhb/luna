"""
Character Prompts Module v2.0
=============================

统一的角色 prompt 管理系统，支持多版本和 A/B 测试。

作者：Claude Code
创建时间：2024
版本：v2.0
"""

from typing import Dict, Optional
from .base_prompt import BaseCharacterPrompt, PromptVersionManager
from .luna_prompt import get_luna_prompt
from .vera_prompt import get_vera_prompt


class CharacterPromptManager:
    """角色 prompt 统一管理器"""
    
    def __init__(self):
        self.version_managers: Dict[str, PromptVersionManager] = {}
        self._initialize_characters()
    
    def _initialize_characters(self):
        """初始化所有角色的版本管理器"""
        # Luna 角色
        luna_manager = PromptVersionManager()
        luna_manager.register_version("v1", get_luna_prompt("v1"))
        luna_manager.register_version("v2", get_luna_prompt("v2"))
        luna_manager.set_default_version("v1")
        self.version_managers["luna"] = luna_manager
        
        # Vera 角色
        vera_manager = PromptVersionManager()
        vera_manager.register_version("v1", get_vera_prompt("v1"))
        vera_manager.register_version("v2", get_vera_prompt("v2"))
        vera_manager.set_default_version("v1")
        self.version_managers["vera"] = vera_manager
    
    def get_character_prompt(
        self, 
        character_name: str, 
        version: str = None
    ) -> Optional[BaseCharacterPrompt]:
        """
        获取角色 prompt
        
        Args:
            character_name: 角色名称 (luna, vera)
            version: 版本 (v1, v2, None=默认)
            
        Returns:
            BaseCharacterPrompt 实例或 None
        """
        manager = self.version_managers.get(character_name.lower())
        if not manager:
            return None
        
        return manager.get_prompt(version)
    
    def get_system_prompt(
        self,
        character_name: str,
        intimacy_level: str = "friend",
        version: str = None
    ) -> str:
        """
        获取完整的系统 prompt
        
        Args:
            character_name: 角色名称
            intimacy_level: 亲密度等级
            version: prompt 版本
            
        Returns:
            完整的系统 prompt 字符串
        """
        prompt_obj = self.get_character_prompt(character_name, version)
        if not prompt_obj:
            return f"You are {character_name}. Please be helpful and friendly."
        
        base_prompt = prompt_obj.get_base_system_prompt()
        intimacy_prompt = prompt_obj.get_intimacy_prompt(intimacy_level)
        
        return f"""{base_prompt}

{intimacy_prompt}"""
    
    def get_dialogue_examples(
        self,
        character_name: str,
        intimacy_level: str = "friend",
        version: str = None
    ) -> list:
        """获取对话示例"""
        prompt_obj = self.get_character_prompt(character_name, version)
        if not prompt_obj:
            return []
        
        return prompt_obj.get_dialogue_examples(intimacy_level)
    
    def list_characters(self) -> list:
        """列出所有可用角色"""
        return list(self.version_managers.keys())
    
    def list_versions(self, character_name: str) -> list:
        """列出角色的所有可用版本"""
        manager = self.version_managers.get(character_name.lower())
        if not manager:
            return []
        return manager.list_versions()
    
    def set_default_version(self, character_name: str, version: str):
        """设置角色的默认版本"""
        manager = self.version_managers.get(character_name.lower())
        if manager:
            manager.set_default_version(version)


# 全局实例
character_prompt_manager = CharacterPromptManager()


def get_character_system_prompt(
    character_name: str,
    intimacy_level: str = "friend",
    version: str = None
) -> str:
    """
    便捷函数：获取角色系统 prompt
    
    Args:
        character_name: 角色名称 (luna, vera)
        intimacy_level: 亲密度等级 (stranger, friend, ambiguous, lover, soulmate)
        version: prompt 版本 (v1, v2)
        
    Returns:
        完整的系统 prompt
    """
    return character_prompt_manager.get_system_prompt(
        character_name, intimacy_level, version
    )


def get_character_examples(
    character_name: str,
    intimacy_level: str = "friend",
    version: str = None
) -> list:
    """
    便捷函数：获取角色对话示例
    
    Args:
        character_name: 角色名称
        intimacy_level: 亲密度等级
        version: prompt 版本
        
    Returns:
        对话示例列表
    """
    return character_prompt_manager.get_dialogue_examples(
        character_name, intimacy_level, version
    )


# 角色 ID 映射 (用于与现有系统兼容)
CHARACTER_ID_MAPPING = {
    "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d": "luna",  # Luna 的 UUID
    "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e": "vera",  # Vera 的 UUID
}


def get_character_name_from_id(character_id: str) -> str:
    """从角色 UUID 获取角色名称"""
    return CHARACTER_ID_MAPPING.get(character_id, "unknown")


def get_character_prompt_by_id(
    character_id: str,
    intimacy_level: str = "friend",
    version: str = None
) -> str:
    """
    通过角色 ID 获取 prompt (兼容现有系统)
    
    Args:
        character_id: 角色 UUID
        intimacy_level: 亲密度等级
        version: prompt 版本
        
    Returns:
        完整的系统 prompt
    """
    character_name = get_character_name_from_id(character_id)
    if character_name == "unknown":
        return f"You are a helpful AI companion with character ID {character_id}."
    
    return get_character_system_prompt(character_name, intimacy_level, version)


# 导出主要接口
__all__ = [
    'CharacterPromptManager',
    'character_prompt_manager',
    'get_character_system_prompt',
    'get_character_examples',
    'get_character_prompt_by_id',
    'get_character_name_from_id',
    'CHARACTER_ID_MAPPING'
]