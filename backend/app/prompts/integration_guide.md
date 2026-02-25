# Luna Prompt 优化系统集成指南

## 概述

本文档说明如何将优化后的 prompt 系统集成到现有的 Luna 后端架构中。

## 系统架构

### 新的 Prompt 系统结构

```
app/prompts/
├── __init__.py              # 主要管理器和接口
├── base_prompt.py          # 基础 prompt 模板
├── luna_prompt.py          # Luna 角色 prompt (v1, v2)
├── vera_prompt.py          # Vera 角色 prompt (v1, v2)
├── integration_guide.md    # 本文档
└── test_prompts.py         # 测试文件
```

### 与现有系统的关系

- **`character_config.py`**: 保留角色配置参数 (Z轴、阈值等)
- **`prompt_builder.py`**: 修改以使用新的 prompt 系统
- **新的 prompts 模块**: 提供结构化的角色 prompt

## 集成方案

### 方案 1: 渐进式集成 (推荐)

保持现有系统不变，添加新的 prompt 作为可选组件：

```python
# 在 prompt_builder.py 中添加
from app.prompts import get_character_prompt_by_id

def _build_base_prompt(self, char_config: CharacterConfig, game_result: GameResult, character_id: str) -> str:
    # 尝试使用新的 prompt 系统
    try:
        # 映射亲密度到新系统的等级
        intimacy_level = self._map_intimacy_to_level(game_result.current_intimacy)
        
        # 检查是否启用新的 prompt 系统 (可通过配置控制)
        if self._use_new_prompts:
            new_prompt = get_character_prompt_by_id(
                character_id, 
                intimacy_level, 
                version="v2"  # 或者通过 A/B 测试决定
            )
            if new_prompt:
                return self._enhance_prompt_with_context(new_prompt, game_result)
    except Exception as e:
        logger.warning(f"Failed to use new prompt system: {e}")
    
    # 回退到原有系统
    return self._build_legacy_prompt(char_config, game_result, character_id)

def _map_intimacy_to_level(self, intimacy: int) -> str:
    """将数值亲密度映射到文字等级"""
    if intimacy < 20:
        return "stranger"
    elif intimacy < 40:
        return "friend"
    elif intimacy < 60:
        return "ambiguous"
    elif intimacy < 80:
        return "lover"
    else:
        return "soulmate"
```

### 方案 2: 完全替换

直接用新系统替换现有的 prompt 生成逻辑：

```python
# 修改 character_config.py 中的 system_prompt
def get_enhanced_system_prompt(char_id: str, intimacy: int) -> str:
    """获取增强的系统 prompt"""
    from app.prompts import get_character_prompt_by_id
    
    intimacy_level = map_intimacy_to_level(intimacy)
    return get_character_prompt_by_id(char_id, intimacy_level)
```

## A/B 测试支持

### 实现 A/B 测试

```python
def get_prompt_version_for_user(user_id: str, character_id: str) -> str:
    """为用户分配 prompt 版本"""
    # 简单的哈希分配
    hash_value = hash(f"{user_id}_{character_id}")
    return "v2" if hash_value % 2 == 0 else "v1"

def build_prompt_with_ab_test(user_id: str, character_id: str, intimacy: int):
    """构建带 A/B 测试的 prompt"""
    version = get_prompt_version_for_user(user_id, character_id)
    intimacy_level = map_intimacy_to_level(intimacy)
    
    return get_character_prompt_by_id(character_id, intimacy_level, version)
```

### 记录测试数据

```python
# 在使用新 prompt 时记录
def log_prompt_usage(user_id: str, character_id: str, version: str, response_quality: float):
    """记录 prompt 使用情况"""
    # 发送到分析系统
    analytics.track('prompt_usage', {
        'user_id': user_id,
        'character_id': character_id,
        'prompt_version': version,
        'response_quality': response_quality,
        'timestamp': datetime.now()
    })
```

## 配置管理

### 环境变量

```bash
# .env 文件
USE_NEW_PROMPTS=true
DEFAULT_PROMPT_VERSION=v2
ENABLE_AB_TEST=true
AB_TEST_SPLIT=50  # v2 使用比例
```

### 配置类

```python
# app/config.py 中添加
class PromptConfig:
    USE_NEW_PROMPTS = os.getenv('USE_NEW_PROMPTS', 'false').lower() == 'true'
    DEFAULT_PROMPT_VERSION = os.getenv('DEFAULT_PROMPT_VERSION', 'v1')
    ENABLE_AB_TEST = os.getenv('ENABLE_AB_TEST', 'false').lower() == 'true'
    AB_TEST_SPLIT = int(os.getenv('AB_TEST_SPLIT', '50'))
```

## 迁移步骤

### 第一阶段：准备 (1-2天)
1. 部署新的 prompts 模块
2. 添加配置开关
3. 创建测试用例

### 第二阶段：灰度测试 (1周)
1. 对少量用户启用新系统 (USE_NEW_PROMPTS=true, 10% 用户)
2. 监控响应质量和错误率
3. 收集用户反馈

### 第三阶段：A/B 测试 (2-3周)
1. 启用 A/B 测试 (ENABLE_AB_TEST=true)
2. 对比 v1 vs v2 的表现
3. 分析数据，优化 prompt

### 第四阶段：全量发布 (1周)
1. 根据测试结果选择最佳版本
2. 全量用户使用新系统
3. 移除旧代码

## 监控指标

### 技术指标
- 响应生成时间
- 错误率
- prompt 加载时间

### 业务指标
- 用户满意度 (通过反馈收集)
- 对话轮次 (更好的 prompt 应该产生更长的对话)
- 用户留存率

### 收集方式
```python
def collect_feedback(user_id: str, message_id: str, rating: int):
    """收集用户反馈"""
    # 记录 prompt 版本和用户评分的关联
    pass

def track_conversation_metrics(user_id: str, session_id: str):
    """跟踪对话指标"""
    # 记录对话轮次、时长等
    pass
```

## 回滚计划

### 快速回滚
```python
# 紧急情况下快速关闭新系统
USE_NEW_PROMPTS=false
```

### 部分回滚
```python
# 只回滚特定角色或版本
CHARACTER_PROMPT_OVERRIDES={
    "luna": "legacy",
    "vera": "v1"
}
```

## 最佳实践

### Prompt 开发
1. **版本控制**: 每次修改都创建新版本
2. **测试驱动**: 先写对话示例，再写 prompt
3. **一致性检查**: 定期验证角色行为一致性
4. **用户反馈**: 积极收集用户意见

### 部署流程
1. **本地测试**: 完整的单元测试和集成测试
2. **预发布**: 在测试环境完整验证
3. **灰度发布**: 小范围用户试用
4. **全量发布**: 基于数据决策

### 维护管理
1. **定期审查**: 每月审查 prompt 表现
2. **持续优化**: 根据用户反馈迭代
3. **文档更新**: 保持文档与代码同步
4. **知识分享**: 团队内部分享最佳实践

## 常见问题

### Q: 新系统会影响现有用户体验吗？
A: 通过渐进式集成和充分测试，可以确保平滑过渡。

### Q: 如果新 prompt 效果不好怎么办？
A: 有完整的回滚机制，可以快速切回原有系统。

### Q: 如何确保角色一致性？
A: 通过结构化的 prompt 设计和充分的测试用例。

### Q: A/B 测试的最小样本量是多少？
A: 建议每个版本至少 1000 个对话样本，持续 1-2 周。