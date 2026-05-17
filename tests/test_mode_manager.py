# -*- coding: utf-8 -*-
"""
Mode Manager 单元测试
"""
import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mode.manager import ModeManager
from mode import messages_template as tpl


class TestModeManager(unittest.TestCase):
    """测试 ModeManager 类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建模拟模式类
        class MockMode1:
            def message_handler(self, message):
                self.last_message = message
                return "Mode1 response"
            
            def command_handler(self, message, command, arg_str):
                self.last_command_message = message
                return f"Mode1 command: {command}"
            
            def helper(self, command=None):
                return "Mode1 help"
        
        class MockMode2:
            def message_handler(self, message):
                return "Mode2 response"
            
            def command_handler(self, message, command, arg_str):
                return f"Mode2 command: {command}"
            
            def helper(self, command=None):
                return "Mode2 help"
        
        self.mode_configs = {
            "mode1": {"class": MockMode1, "description": "测试模式 1"},
            "mode2": {"class": MockMode2, "description": "测试模式 2"}
        }
        
        self.manager = ModeManager(self.mode_configs)
    
    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.manager.current_mode_index, 0)
        self.assertEqual(len(self.manager.modes_instances), 2)
        self.assertEqual(len(self.manager.modes_descriptions), 2)
    
    def test_get_current_mode_name(self):
        """测试获取当前模式名称"""
        result = self.manager.get_current_mode_name()
        self.assertEqual(result, "mode1")
    
    def test_switch_mode_next(self):
        """测试切换到下一个模式"""
        # 当前是 mode1 (index 0)
        self.assertEqual(self.manager.current_mode_index, 0)
        
        # 切换到下一个
        result = self.manager.switch_mode()
        
        self.assertEqual(self.manager.current_mode_index, 1)
        self.assertEqual(result, tpl.SWITCH_MODE_SUCCESS.format(mode_name="mode2"))
    
    def test_switch_mode_specific(self):
        """测试切换到指定模式"""
        # 切换到 mode2
        result = self.manager.switch_mode("mode2")
        
        self.assertEqual(self.manager.get_current_mode_name(), "mode2")
        self.assertIn("mode2", result)
    
    def test_switch_mode_not_found(self):
        """测试切换不存在的模式"""
        result = self.manager.switch_mode("nonexistent_mode")
        
        self.assertEqual(result, tpl.SWITCH_MODE_NOT_FOUND.format(mode_name="nonexistent_mode"))
    
    def test_message_handler(self):
        """测试消息处理"""
        # 创建一个模拟消息对象
        class MockMessage:
            def __init__(self, content):
                self.content = content
        
        message = MockMessage("test")
        result = self.manager.message_handler(message)
        
        # 默认是 mode1
        self.assertEqual(result, "Mode1 response")
        self.assertIs(self.manager.modes_instances[0].last_message, message)
    
    def test_handle_command_basic_switch(self):
        """测试基本命令 - switch"""
        result = self.manager.handle_command("switch", "mode2")
        self.assertIn("mode2", result)
    
    def test_handle_command_basic_active_mode(self):
        """测试基本命令 - active_mode"""
        result = self.manager.handle_command("active_mode", None)
        self.assertEqual(result, "mode1")
    
    def test_handle_command_basic_modes(self):
        """测试基本命令 - modes"""
        result = self.manager.handle_command("modes", None)
        self.assertIsInstance(result, str)
        self.assertIn("可用的模式", result)
        self.assertIn("mode1", result)
        self.assertIn("mode2", result)
    
    def test_handle_command_basic_help(self):
        """测试基本命令 - help"""
        result = self.manager.handle_command("help", None)
        self.assertIsInstance(result, str)
        self.assertEqual(result, tpl.HELP_BASIC)
    
    def test_handle_command_basic_help_specific_mode(self):
        """测试基本命令 - help 指定模式"""
        result = self.manager.handle_command("help", "mode1")
        self.assertEqual(result, "Mode1 help")
    
    def test_handle_command_basic_help_mode_not_found(self):
        """测试基本命令 - help 模式不存在"""
        result = self.manager.handle_command("help", "nonexistent")
        self.assertEqual(result, tpl.HELP_MODE_NOT_FOUND.format(mode_name="nonexistent"))
    
    def test_handle_command_mode_specific(self):
        """测试模式特定命令"""
        result = self.manager.handle_command("mode1:test_cmd", "arg")
        self.assertIn("Mode1 command", result)
        self.assertIn("test_cmd", result)
        self.assertEqual(
            self.manager.modes_instances[0].last_command_message,
            "mode1:test_cmd",
        )
    
    def test_handle_command_unknown_format(self):
        """测试未知命令格式"""
        result = self.manager.handle_command("unknown", None)
        self.assertEqual(result, tpl.UNKNOWN_COMMAND.format(command="unknown"))
    
    def test_handle_command_mode_not_found(self):
        """测试模式不存在"""
        result = self.manager.handle_command("nonexistent:cmd", None)
        self.assertEqual(result, tpl.UNKNOWN_MODE_COMMAND.format(mode_name="nonexistent"))
    
    def test_all_modes(self):
        """测试列出所有模式"""
        result = self.manager.all_modes()
        self.assertIsInstance(result, str)
        self.assertIn(tpl.MODES_LIST_HEADER, result)
        self.assertIn("mode1", result)
        self.assertIn("mode2", result)
        self.assertIn("测试模式 1", result)
        self.assertIn("测试模式 2", result)


class TestModeManagerCircularSwitch(unittest.TestCase):
    """测试模式循环切换"""
    
    def setUp(self):
        class MockMode:
            def message_handler(self, message):
                return "response"
            def command_handler(self, message, command, arg_str):
                return "cmd"
            def helper(self, command=None):
                return "help"
        
        self.mode_configs = {
            "a": {"class": MockMode, "description": "A"},
            "b": {"class": MockMode, "description": "B"},
            "c": {"class": MockMode, "description": "C"}
        }
        self.manager = ModeManager(self.mode_configs)
    
    def test_circular_switch(self):
        """测试循环切换"""
        # 初始是 a
        self.assertEqual(self.manager.get_current_mode_name(), "a")
        
        # 切换到 b
        self.manager.switch_mode()
        self.assertEqual(self.manager.get_current_mode_name(), "b")
        
        # 切换到 c
        self.manager.switch_mode()
        self.assertEqual(self.manager.get_current_mode_name(), "c")
        
        # 循环回 a
        self.manager.switch_mode()
        self.assertEqual(self.manager.get_current_mode_name(), "a")


class TestModeManagerMessagesTemplate(unittest.TestCase):
    """测试 Mode Manager 消息模板"""
    
    def test_switch_mode_success_template(self):
        """测试切换成功模板"""
        result = tpl.SWITCH_MODE_SUCCESS.format(mode_name="test")
        self.assertIn("test", result)
        self.assertIn("Switched to", result)
    
    def test_switch_mode_not_found_template(self):
        """测试切换失败模板"""
        result = tpl.SWITCH_MODE_NOT_FOUND.format(mode_name="test")
        self.assertIn("test", result)
        self.assertIn("not found", result)
    
    def test_unknown_command_template(self):
        """测试未知命令模板"""
        result = tpl.UNKNOWN_COMMAND.format(command="test")
        self.assertIn("test", result)
        self.assertIn("未知命令", result)
    
    def test_unknown_mode_command_template(self):
        """测试未知模式命令模板"""
        result = tpl.UNKNOWN_MODE_COMMAND.format(mode_name="test")
        self.assertIn("test", result)
        self.assertIn("没有", result)
    
    def test_help_basic_template(self):
        """测试基本帮助模板"""
        self.assertIsInstance(tpl.HELP_BASIC, str)
        self.assertGreater(len(tpl.HELP_BASIC), 0)
        self.assertIn("基本信息", tpl.HELP_BASIC)
    
    def test_help_mode_not_found_template(self):
        """测试帮助模式不存在模板"""
        result = tpl.HELP_MODE_NOT_FOUND.format(mode_name="test")
        self.assertIn("test", result)
        self.assertIn("未知模式", result)
    
    def test_modes_list_header_template(self):
        """测试模式列表头模板"""
        self.assertIsInstance(tpl.MODES_LIST_HEADER, str)
        self.assertIn("可用的模式", tpl.MODES_LIST_HEADER)
    
    def test_modes_list_item_template(self):
        """测试模式列表项模板"""
        result = tpl.MODES_LIST_ITEM.format(mode_name="test", description="desc")
        self.assertIn("test", result)
        self.assertIn("desc", result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
