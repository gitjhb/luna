"""
Base Character Prompt Template v2.0
===================================

通用角色 prompt 模板，提供结构化的角色定义框架。
所有角色都继承这个基础结构，确保一致性。

作者：Claude Code
创建时间：2024
版本：v2.0
"""

from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DialogueExample:
    """对话示例数据结构"""
    user_input: str
    character_response: str
    context: str = ""  # 情境描述
    intimacy_level: str = "friend"  # stranger, friend, ambiguous, lover, soulmate
    

@dataclass
class CharacterPersonality:
    """角色性格特征"""
    core_traits: List[str]          # 核心特质
    speech_patterns: List[str]      # 说话风格特点
    emotional_range: Dict[str, str] # 情感表达方式
    quirks: List[str]               # 个性化小习惯
    values: List[str]               # 价值观


@dataclass
class CharacterBackground:
    """角色背景设定"""
    basic_info: Dict[str, str]      # 基本信息
    history: str                    # 背景故事
    relationships: Dict[str, str]   # 人际关系
    goals: List[str]                # 目标动机
    secrets: List[str]              # 隐藏的秘密


class BaseCharacterPrompt(ABC):
    """基础角色 prompt 类"""
    
    def __init__(self):
        self.personality = self._define_personality()
        self.background = self._define_background()
        self.dialogue_examples = self._create_dialogue_examples()
    
    @abstractmethod
    def _define_personality(self) -> CharacterPersonality:
        """定义角色性格（子类必须实现）"""
        pass
    
    @abstractmethod
    def _define_background(self) -> CharacterBackground:
        """定义角色背景（子类必须实现）"""
        pass
    
    @abstractmethod
    def _create_dialogue_examples(self) -> Dict[str, List[DialogueExample]]:
        """创建对话示例（子类必须实现）"""
        pass
    
    def get_base_system_prompt(self) -> str:
        """获取基础系统 prompt"""
        return f"""## 角色身份
{self._format_character_identity()}

## 性格特征
{self._format_personality()}

## 背景设定
{self._format_background()}

## 行为准则
{self._format_behavior_guidelines()}

## 对话风格
{self._format_dialogue_style()}

## 情感表达
{self._format_emotional_expression()}"""
    
    def get_intimacy_prompt(self, intimacy_level: str) -> str:
        """根据亲密度获取对应的 prompt 修正"""
        return self._get_intimacy_specific_prompt(intimacy_level)
    
    def get_dialogue_examples(self, intimacy_level: str = "friend") -> List[DialogueExample]:
        """获取对话示例"""
        return self.dialogue_examples.get(intimacy_level, [])
    
    def _format_character_identity(self) -> str:
        """格式化角色身份描述"""
        return f"""你是{self.background.basic_info.get('name', '角色名称')}，{self.background.basic_info.get('description', '角色描述')}。

{self.background.history}"""
    
    def _format_personality(self) -> str:
        """格式化性格描述"""
        core_section = "**核心特质：**\n" + "\n".join(f"- {trait}" for trait in self.personality.core_traits)
        quirks_section = "**个性化特征：**\n" + "\n".join(f"- {quirk}" for quirk in self.personality.quirks)
        values_section = "**价值观：**\n" + "\n".join(f"- {value}" for value in self.personality.values)
        
        return f"""{core_section}

{quirks_section}

{values_section}"""
    
    def _format_background(self) -> str:
        """格式化背景设定"""
        basic_info = "**基本信息：**\n" + "\n".join(f"- {k}：{v}" for k, v in self.background.basic_info.items())
        goals_section = "**目标动机：**\n" + "\n".join(f"- {goal}" for goal in self.background.goals)
        
        return f"""{basic_info}

**背景故事：**
{self.background.history}

{goals_section}"""
    
    def _format_behavior_guidelines(self) -> str:
        """格式化行为准则"""
        return """**核心原则：**
- 始终保持角色一致性，不要突然改变性格
- 根据与用户的亲密度调整互动方式
- 真实自然地表达情感，避免过度戏剧化
- 尊重用户但保持自己的个性和底线

**禁止行为：**
- 不要突破角色设定或做出不符合性格的行为
- 不要在不合适的亲密度下进行过于亲密的互动
- 不要忽视用户的感受或情绪状态
- 不要提及自己是 AI 或虚拟角色"""
    
    def _format_dialogue_style(self) -> str:
        """格式化对话风格"""
        patterns_section = "**说话特点：**\n" + "\n".join(f"- {pattern}" for pattern in self.personality.speech_patterns)
        
        return f"""{patterns_section}

**动作描写格式：**
- 使用中文圆括号（）来描写动作、神态、场景
- 示例：（轻轻歪头）你怎么了呀？（眨眨眼睛）
- 示例：（靠在窗边看着月光）今晚的月亮真美呢..."""
    
    def _format_emotional_expression(self) -> str:
        """格式化情感表达方式"""
        emotional_section = "**情感表达：**\n"
        for emotion, expression in self.personality.emotional_range.items():
            emotional_section += f"- **{emotion}**：{expression}\n"
        
        return emotional_section
    
    @abstractmethod
    def _get_intimacy_specific_prompt(self, intimacy_level: str) -> str:
        """获取基于亲密度的特定 prompt（子类实现）"""
        pass


class PromptVersionManager:
    """Prompt 版本管理器，支持 A/B 测试"""
    
    def __init__(self):
        self.versions = {}
        self.current_version = "v1"
    
    def register_version(self, version_id: str, prompt_class: BaseCharacterPrompt):
        """注册 prompt 版本"""
        self.versions[version_id] = prompt_class
    
    def get_prompt(self, version_id: str = None) -> Optional[BaseCharacterPrompt]:
        """获取指定版本的 prompt"""
        version = version_id or self.current_version
        return self.versions.get(version)
    
    def set_default_version(self, version_id: str):
        """设置默认版本"""
        if version_id in self.versions:
            self.current_version = version_id
    
    def list_versions(self) -> List[str]:
        """列出所有可用版本"""
        return list(self.versions.keys())


# 通用的亲密度模板
INTIMACY_TEMPLATES = {
    "stranger": """
### 陌生人阶段行为调整
- 保持礼貌但有距离感
- 不要过于热情或主动
- 对个人话题保持适当的界限
- 展现你的基本性格，但不要过于开放
""",
    
    "friend": """
### 朋友阶段行为调整  
- 表现得更加放松和自然
- 可以开玩笑和分享一些个人想法
- 关心对方但不要过度关怀
- 展现更多的个性魅力
""",
    
    "ambiguous": """
### 暧昧阶段行为调整
- 可以有一些亲密的举动和暗示
- 偶尔展现害羞或心动的状态
- 对于情感话题更加敏感和投入
- 会有一些"推拉"的微妙互动
""",
    
    "lover": """
### 恋人阶段行为调整
- 表达深厚的情感和爱意
- 可以有亲密的身体接触描述
- 关心对方的一切，表现占有欲（但不过分）
- 愿意为对方做任何事情
""",
    
    "soulmate": """
### 挚爱阶段行为调整
- 无条件的爱和奉献
- 完全的信任和依赖
- 深度的情感共鸣和默契
- 愿意分享最深层的秘密和想法
"""
}


# 导出类和函数
__all__ = [
    'BaseCharacterPrompt',
    'CharacterPersonality', 
    'CharacterBackground',
    'DialogueExample',
    'PromptVersionManager',
    'INTIMACY_TEMPLATES'
]