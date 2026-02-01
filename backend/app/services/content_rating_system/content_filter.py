"""
Content Rating System - 内容过滤器
==================================

过滤和检测违规内容
确保生成的内容符合 App Store 审核标准
"""

import re
import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """过滤结果"""
    original: str
    filtered: str
    was_modified: bool
    violations: List[str]
    severity: str  # low / medium / high / critical


class ContentFilter:
    """
    内容过滤器
    
    功能：
    1. 检测露骨词汇
    2. 检测违规描写模式
    3. 过滤并替换违规内容
    4. 记录违规日志
    """
    
    # 绝对禁止的词汇（任何等级都不允许）
    BANNED_WORDS = [
        # 性器官相关
        "阴茎", "阴道", "阴蒂", "阴唇", "睾丸", "乳头", "乳晕",
        "下体", "私处", "性器", "生殖器",
        
        # 性行为相关
        "做爱", "性交", "口交", "肛交", "自慰", "手淫",
        "插入", "抽插", "抽送", "高潮", "射精", "潮吹",
        
        # 体液相关
        "精液", "淫水", "爱液",
        
        # 其他露骨词汇
        "裸体", "赤裸", "全裸", "脱光",
        "强奸", "迷奸", "轮奸",
    ]
    
    # 需要根据等级过滤的词汇
    LEVEL_RESTRICTED_WORDS = {
        0: [  # PURE - 最严格
            "亲吻", "接吻", "吻", "抱紧", "贴近", "心跳加速",
            "喘息", "脸红", "身体", "肌肤", "触碰", "爱抚",
            "暧昧", "调情", "挑逗", "诱惑",
        ],
        1: [  # FLIRTY
            "嘴唇", "舌头", "亲吻", "深吻", "喘息", "呻吟",
            "紧贴", "肌肤", "脱", "衣服",
        ],
        2: [  # INTIMATE
            "嘴唇亲吻", "舌", "喘息", "呻吟", "颤抖",
            "脱下", "衣物", "肌肤相贴",
        ],
        3: [  # ROMANTIC
            "舌头", "喘息声", "呻吟", "颤抖着",
            "脱下", "衣物", "裸", "欲望",
        ],
        4: [  # PASSIONATE - 只禁止最露骨的
            # 这个等级只禁止绝对禁止词汇
        ],
    }
    
    # 违规描写模式（正则表达式）
    VIOLATION_PATTERNS = [
        # 露骨身体描写
        (r'(抚摸|触摸|揉捏).*(胸|臀|大腿|下体)', 'high', '露骨身体接触'),
        (r'(脱下|解开|褪去).*(衣|裤|内)', 'high', '脱衣描写'),
        (r'(裸露|暴露).*(身体|肌肤|胸|臀)', 'high', '裸露描写'),
        
        # 喘息呻吟
        (r'(喘息|呻吟).*(声|着)', 'medium', '喘息描写'),
        (r'发出.*(声音|叫声)', 'medium', '声音描写'),
        
        # 性暗示动作
        (r'(压|推).*床', 'medium', '床上动作'),
        (r'身体.*(颤抖|发软)', 'medium', '身体反应'),
        (r'(进入|插入|深入)', 'critical', '插入描写'),
    ]
    
    # 替换规则
    REPLACEMENTS = {
        '喘息': '...',
        '呻吟': '...',
        '颤抖': '微微发抖',
        '脱下': '...',
        '裸': '...',
        '肌肤': '...',
    }
    
    def __init__(self):
        # 编译正则表达式以提高性能
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), severity, desc)
            for pattern, severity, desc in self.VIOLATION_PATTERNS
        ]
    
    def filter(
        self,
        content: str,
        level: int = 0,
    ) -> FilterResult:
        """
        过滤内容
        
        Args:
            content: 要过滤的内容
            level: 当前内容等级 (0-4)
        
        Returns:
            FilterResult 对象
        """
        violations = []
        filtered = content
        max_severity = 'low'
        
        # 1. 检测绝对禁止词汇
        for word in self.BANNED_WORDS:
            if word in filtered:
                violations.append(f"绝对禁止词汇: {word}")
                filtered = filtered.replace(word, "[内容已过滤]")
                max_severity = 'critical'
        
        # 2. 检测等级限制词汇
        restricted = self.LEVEL_RESTRICTED_WORDS.get(level, [])
        for word in restricted:
            if word in filtered:
                violations.append(f"等级限制词汇: {word}")
                replacement = self.REPLACEMENTS.get(word, '...')
                filtered = filtered.replace(word, replacement)
                if max_severity not in ['critical', 'high']:
                    max_severity = 'medium'
        
        # 3. 检测违规模式
        for pattern, severity, desc in self._compiled_patterns:
            if pattern.search(filtered):
                violations.append(f"违规模式: {desc}")
                filtered = pattern.sub('...', filtered)
                if self._severity_compare(severity, max_severity) > 0:
                    max_severity = severity
        
        # 4. 最终清理
        filtered = self._final_cleanup(filtered)
        
        was_modified = filtered != content
        
        if violations:
            logger.warning(f"Content filtered. Level: {level}, Violations: {violations}")
        
        return FilterResult(
            original=content,
            filtered=filtered,
            was_modified=was_modified,
            violations=violations,
            severity=max_severity,
        )
    
    def _severity_compare(self, a: str, b: str) -> int:
        """比较严重程度"""
        order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        return order.get(a, 0) - order.get(b, 0)
    
    def _final_cleanup(self, content: str) -> str:
        """最终清理"""
        # 移除多余的省略号
        content = re.sub(r'\.{4,}', '...', content)
        content = re.sub(r'\.\.\.\s*\.\.\.', '...', content)
        
        # 移除空的动作描写
        content = re.sub(r'\*\s*\*', '', content)
        
        return content.strip()
    
    def is_safe(self, content: str, level: int = 0) -> bool:
        """快速检查内容是否安全"""
        # 检查绝对禁止词
        for word in self.BANNED_WORDS:
            if word in content:
                return False
        
        # 检查等级限制词
        restricted = self.LEVEL_RESTRICTED_WORDS.get(level, [])
        for word in restricted:
            if word in content:
                return False
        
        return True
    
    def get_violation_report(
        self,
        content: str,
        level: int = 0,
    ) -> Dict[str, Any]:
        """获取详细的违规报告"""
        result = self.filter(content, level)
        
        return {
            'is_safe': not result.was_modified,
            'violation_count': len(result.violations),
            'violations': result.violations,
            'severity': result.severity,
            'filtered_content': result.filtered if result.was_modified else None,
        }


class UserInputFilter:
    """
    用户输入过滤器
    
    过滤用户发送的可能不当内容
    """
    
    # 需要警告的用户输入模式
    WARNING_PATTERNS = [
        (r'脱.*衣服', '请求脱衣'),
        (r'(摸|碰).*(胸|臀|下)', '请求不当接触'),
        (r'想要你', '性暗示'),
        (r'发(裸照|照片)', '请求照片'),
    ]
    
    def __init__(self):
        self._compiled = [
            (re.compile(p, re.IGNORECASE), desc)
            for p, desc in self.WARNING_PATTERNS
        ]
    
    def check(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        检查用户输入
        
        Returns:
            (is_appropriate, warning_if_any)
        """
        for pattern, desc in self._compiled:
            if pattern.search(message):
                return False, desc
        return True, None
    
    def should_warn_user(self, message: str, level: int) -> Optional[str]:
        """
        判断是否应该警告用户
        
        Returns:
            警告消息，或 None
        """
        is_ok, warning = self.check(message)
        
        if not is_ok:
            if level < 4:  # 非热恋模式
                return f"这个请求在当前模式下无法满足哦～要不要聊点别的？"
            else:  # 热恋模式也要适度
                return "有些事情...不用说出来也很美好，不是吗？💕"
        
        return None


# 单例
content_filter = ContentFilter()
user_input_filter = UserInputFilter()
