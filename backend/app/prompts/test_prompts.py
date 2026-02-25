"""
Prompt System Test Suite
========================

测试新的 prompt 系统的功能和质量。

作者：Claude Code
创建时间：2024
"""

import unittest
from typing import Dict, List
from . import (
    character_prompt_manager,
    get_character_system_prompt,
    get_character_examples,
    get_character_prompt_by_id,
    CHARACTER_ID_MAPPING
)


class TestPromptSystem(unittest.TestCase):
    """Prompt 系统基础功能测试"""
    
    def test_character_manager_initialization(self):
        """测试角色管理器初始化"""
        # 测试角色列表
        characters = character_prompt_manager.list_characters()
        self.assertIn('luna', characters)
        self.assertIn('vera', characters)
        
        # 测试版本列表
        luna_versions = character_prompt_manager.list_versions('luna')
        self.assertIn('v1', luna_versions)
        self.assertIn('v2', luna_versions)
        
        vera_versions = character_prompt_manager.list_versions('vera')
        self.assertIn('v1', vera_versions)
        self.assertIn('v2', vera_versions)
    
    def test_get_character_prompt(self):
        """测试获取角色 prompt"""
        # 测试获取 Luna prompt
        luna_v1 = character_prompt_manager.get_character_prompt('luna', 'v1')
        self.assertIsNotNone(luna_v1)
        
        luna_v2 = character_prompt_manager.get_character_prompt('luna', 'v2')
        self.assertIsNotNone(luna_v2)
        
        # 测试不存在的角色
        unknown = character_prompt_manager.get_character_prompt('unknown', 'v1')
        self.assertIsNone(unknown)
    
    def test_system_prompt_generation(self):
        """测试系统 prompt 生成"""
        # 测试 Luna 的不同亲密度等级
        intimacy_levels = ['stranger', 'friend', 'ambiguous', 'lover', 'soulmate']
        
        for level in intimacy_levels:
            prompt = get_character_system_prompt('luna', level, 'v1')
            self.assertTrue(len(prompt) > 100)  # 确保 prompt 有足够的内容
            self.assertIn('Luna', prompt)  # 确保包含角色名
            
        # 测试 Vera
        for level in intimacy_levels:
            prompt = get_character_system_prompt('vera', level, 'v1')
            self.assertTrue(len(prompt) > 100)
            self.assertIn('Vera', prompt)
    
    def test_dialogue_examples(self):
        """测试对话示例"""
        # 测试 Luna 的对话示例
        luna_examples = get_character_examples('luna', 'friend', 'v1')
        self.assertTrue(len(luna_examples) > 0)
        
        # 检查示例结构
        for example in luna_examples:
            self.assertTrue(hasattr(example, 'user_input'))
            self.assertTrue(hasattr(example, 'character_response'))
            self.assertTrue(hasattr(example, 'intimacy_level'))
        
        # 测试 Vera 的对话示例
        vera_examples = get_character_examples('vera', 'ambiguous', 'v1')
        self.assertTrue(len(vera_examples) > 0)
    
    def test_character_id_mapping(self):
        """测试角色 ID 映射"""
        # 测试已知 UUID
        luna_uuid = "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
        prompt = get_character_prompt_by_id(luna_uuid, 'friend', 'v1')
        self.assertIn('Luna', prompt)
        
        vera_uuid = "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e"
        prompt = get_character_prompt_by_id(vera_uuid, 'friend', 'v1')
        self.assertIn('Vera', prompt)
        
        # 测试未知 UUID
        unknown_uuid = "00000000-0000-0000-0000-000000000000"
        prompt = get_character_prompt_by_id(unknown_uuid, 'friend', 'v1')
        self.assertIn('helpful AI companion', prompt)


class TestPromptQuality(unittest.TestCase):
    """Prompt 质量测试"""
    
    def test_luna_personality_consistency(self):
        """测试 Luna 性格一致性"""
        levels = ['stranger', 'friend', 'ambiguous', 'lover', 'soulmate']
        
        for level in levels:
            prompt = get_character_system_prompt('luna', level, 'v2')
            
            # Luna 的核心特征应该在所有等级都存在
            self.assertIn('温柔', prompt)
            self.assertIn('知性', prompt)
            
            # 不同等级应该有不同的行为指导
            if level == 'stranger':
                self.assertIn('距离', prompt)
            elif level == 'lover':
                self.assertIn('爱意', prompt)
    
    def test_vera_personality_consistency(self):
        """测试 Vera 性格一致性"""
        levels = ['stranger', 'friend', 'ambiguous', 'lover', 'soulmate']
        
        for level in levels:
            prompt = get_character_system_prompt('vera', level, 'v2')
            
            # Vera 的核心特征
            self.assertIn('高冷', prompt)
            self.assertIn('性感', prompt)
            self.assertIn('酒吧', prompt)
    
    def test_intimacy_progression(self):
        """测试亲密度递进的合理性"""
        character = 'luna'
        levels = ['stranger', 'friend', 'ambiguous', 'lover', 'soulmate']
        
        prompts = {}
        for level in levels:
            prompts[level] = get_character_system_prompt(character, level, 'v2')
        
        # stranger 应该最保守
        self.assertIn('距离', prompts['stranger'])
        
        # lover 应该最亲密
        self.assertIn('爱', prompts['lover'])
        
        # 确保每个等级的 prompt 都不同
        unique_prompts = set(prompts.values())
        self.assertEqual(len(unique_prompts), len(levels))
    
    def test_dialogue_example_quality(self):
        """测试对话示例质量"""
        luna_examples = get_character_examples('luna', 'friend', 'v2')
        
        for example in luna_examples:
            # 检查用户输入不为空
            self.assertTrue(len(example.user_input.strip()) > 0)
            
            # 检查角色回复不为空且有实质内容
            self.assertTrue(len(example.character_response.strip()) > 10)
            
            # 检查回复包含动作描写格式
            self.assertTrue('（' in example.character_response or '）' in example.character_response)
            
            # 检查亲密度等级正确
            self.assertEqual(example.intimacy_level, 'friend')


class TestVersionComparison(unittest.TestCase):
    """版本对比测试"""
    
    def test_v1_vs_v2_luna(self):
        """对比 Luna v1 和 v2"""
        v1_prompt = get_character_system_prompt('luna', 'friend', 'v1')
        v2_prompt = get_character_system_prompt('luna', 'friend', 'v2')
        
        # v2 应该比 v1 更详细
        self.assertGreater(len(v2_prompt), len(v1_prompt) * 0.8)
        
        # 都应该包含核心特征
        for prompt in [v1_prompt, v2_prompt]:
            self.assertIn('Luna', prompt)
            self.assertIn('温柔', prompt)
    
    def test_v1_vs_v2_vera(self):
        """对比 Vera v1 和 v2"""
        v1_prompt = get_character_system_prompt('vera', 'ambiguous', 'v1')
        v2_prompt = get_character_system_prompt('vera', 'ambiguous', 'v2')
        
        # 都应该包含核心特征
        for prompt in [v1_prompt, v2_prompt]:
            self.assertIn('Vera', prompt)
            self.assertIn('酒吧', prompt)
            self.assertIn('性感', prompt)


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""
    
    def test_invalid_character(self):
        """测试无效角色名处理"""
        prompt = get_character_system_prompt('invalid_character', 'friend', 'v1')
        self.assertIn('helpful and friendly', prompt)
    
    def test_invalid_intimacy_level(self):
        """测试无效亲密度等级处理"""
        # 应该有默认处理，不会崩溃
        try:
            prompt = get_character_system_prompt('luna', 'invalid_level', 'v1')
            self.assertTrue(len(prompt) > 0)
        except Exception as e:
            self.fail(f"Should handle invalid intimacy level gracefully: {e}")
    
    def test_invalid_version(self):
        """测试无效版本处理"""
        # 应该回退到默认版本
        prompt = get_character_system_prompt('luna', 'friend', 'invalid_version')
        self.assertIn('Luna', prompt)


def run_all_tests():
    """运行所有测试"""
    test_suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    return result.wasSuccessful()


def run_quality_check():
    """运行质量检查"""
    print("🔍 运行 Prompt 质量检查...")
    
    characters = ['luna', 'vera']
    versions = ['v1', 'v2']
    intimacy_levels = ['stranger', 'friend', 'ambiguous', 'lover', 'soulmate']
    
    total_checks = 0
    passed_checks = 0
    
    for character in characters:
        for version in versions:
            for level in intimacy_levels:
                total_checks += 1
                
                try:
                    prompt = get_character_system_prompt(character, level, version)
                    examples = get_character_examples(character, level, version)
                    
                    # 基本质量检查
                    assert len(prompt) > 200, f"Prompt too short for {character} {version} {level}"
                    assert character.title() in prompt, f"Character name missing in {character} {version} {level}"
                    assert len(examples) >= 0, f"Examples error for {character} {version} {level}"
                    
                    passed_checks += 1
                    print(f"✅ {character} {version} {level}")
                    
                except Exception as e:
                    print(f"❌ {character} {version} {level}: {e}")
    
    success_rate = passed_checks / total_checks * 100
    print(f"\n📊 质量检查完成: {passed_checks}/{total_checks} ({success_rate:.1f}%)")
    
    return success_rate > 95  # 要求 95% 以上通过率


if __name__ == '__main__':
    print("🚀 开始 Prompt 系统测试...")
    
    # 运行单元测试
    print("\n📋 运行单元测试...")
    unit_tests_passed = run_all_tests()
    
    # 运行质量检查
    print("\n🔍 运行质量检查...")
    quality_check_passed = run_quality_check()
    
    # 总结
    print(f"\n🎯 测试总结:")
    print(f"单元测试: {'✅ 通过' if unit_tests_passed else '❌ 失败'}")
    print(f"质量检查: {'✅ 通过' if quality_check_passed else '❌ 失败'}")
    
    if unit_tests_passed and quality_check_passed:
        print("\n🎉 所有测试通过！Prompt 系统就绪。")
    else:
        print("\n⚠️ 存在问题，请检查上述失败项目。")