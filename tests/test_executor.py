# -*- coding: utf-8 -*-
"""
Executor 模式单元测试

注意：本测试文件仅使用安全命令（dir, echo, tree 等），不包含任何高危命令。
"""
import unittest
import subprocess
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mode.executor.core import Executor, run_command
from mode.executor import messages_template as tpl


class MockMessage:
    """模拟消息对象"""
    def __init__(self, content):
        self.content = content


class TestRunCommand(unittest.TestCase):
    """测试 run_command 函数"""
    
    def test_echo_command(self):
        """测试 echo 命令（安全）"""
        result = run_command("echo Hello World", timeout=5)
        self.assertEqual(result['returncode'], 0)
        self.assertIn("Hello World", result['output'])
        self.assertEqual(result['error'], "")
    
    def test_dir_command(self):
        """测试 dir 命令（安全）"""
        result = run_command("dir", timeout=5)
        self.assertEqual(result['returncode'], 0)
        self.assertIsInstance(result['output'], str)
        self.assertGreater(len(result['output']), 0)
    
    def test_tree_command(self):
        """测试 tree 命令（安全）"""
        result = run_command("tree /F /A 2>NUL", timeout=5)
        # tree 可能未安装，只检查不抛出异常
        self.assertIsInstance(result, dict)
        self.assertIn('returncode', result)
        self.assertIn('output', result)
        self.assertIn('error', result)
    
    def test_timeout_command(self):
        """测试超时处理"""
        # 这个测试验证 run_command 能正确处理命令
        # 实际超时测试在 message_handler 中进行
        result = run_command("echo quick", timeout=5)
        self.assertEqual(result['returncode'], 0)
    
    def test_nonexistent_command(self):
        """测试不存在的命令"""
        # 在 Windows 上，不存在的命令会返回非零返回码而不是抛出异常
        result = run_command("nonexistent_command_xyz123", timeout=5)
        self.assertNotEqual(result['returncode'], 0)
    
    def test_custom_cwd(self):
        """测试自定义工作目录"""
        result = run_command("dir", cwd="C:\\", timeout=5)
        self.assertEqual(result['returncode'], 0)
    
    def test_error_output(self):
        """测试错误输出捕获"""
        result = run_command("dir nonexistent_dir_xyz", timeout=5)
        self.assertNotEqual(result['returncode'], 0)
        # 错误信息应该在 error 字段中
        self.assertIsInstance(result['error'], str)


class TestExecutorClass(unittest.TestCase):
    """测试 Executor 类"""
    
    def setUp(self):
        """测试前准备"""
        self.executor = Executor()
        self.original_cwd = self.executor.cwd
    
    def tearDown(self):
        """测试后清理"""
        self.executor.cwd = self.original_cwd
    
    def test_initialization(self):
        """测试初始化"""
        executor = Executor()
        self.assertEqual(executor.cwd, ".")
    
    def test_message_handler_echo(self):
        """测试消息处理 - echo 命令（安全）"""
        message = MockMessage("echo test123")
        result = self.executor.message_handler(message)
        
        self.assertIsInstance(result, str)
        # 检查是否包含命令执行完成的标记
        self.assertTrue(len(result) > 0)
    
    def test_message_handler_dir(self):
        """测试消息处理 - dir 命令（安全）"""
        message = MockMessage("dir")
        result = self.executor.message_handler(message)
        
        self.assertIsInstance(result, str)
        # 成功执行应该包含返回码信息
        self.assertTrue(len(result) > 0)
    
    def test_message_handler_timeout(self):
        """测试消息处理 - 超时情况"""
        message = MockMessage("ping 127.0.0.1 -n 10 -w 1000")
        result = self.executor.message_handler(message)
        
        self.assertIsInstance(result, str)
        # 超时或执行完成都应该返回字符串
    
    def test_set_cwd_valid_path(self):
        """测试设置工作目录 - 有效路径"""
        result = self.executor.set_cwd("C:\\")
        self.assertEqual(result, tpl.SET_CWD_SUCCESS)
        self.assertEqual(self.executor.cwd, "C:\\")
    
    def test_set_cwd_invalid_path(self):
        """测试设置工作目录 - 无效路径"""
        result = self.executor.set_cwd("X:\\nonexistent_path_xyz")
        self.assertEqual(result, tpl.SET_CWD_NOT_FOUND)
    
    def test_set_cwd_missing_argument(self):
        """测试 set_cwd 命令 - 缺少参数"""
        result = self.executor.command_handler("set_cwd", None)
        self.assertEqual(result, tpl.SET_CWD_MISSING_ARG)
    
    def test_whereami(self):
        """测试 whereami 命令"""
        result = self.executor.whereami()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
    
    def test_command_handler_set_cwd(self):
        """测试命令处理 - set_cwd"""
        result = self.executor.command_handler("set_cwd", "C:\\")
        self.assertEqual(result, tpl.SET_CWD_SUCCESS)
    
    def test_command_handler_whereami(self):
        """测试命令处理 - whereami"""
        result = self.executor.command_handler("whereami")
        self.assertIsInstance(result, str)
    
    def test_command_handler_unknown(self):
        """测试命令处理 - 未知命令"""
        result = self.executor.command_handler("unknown_cmd", "arg")
        self.assertIn("unknown_cmd", result)
    
    def test_helper(self):
        """测试帮助信息"""
        result = self.executor.helper()
        self.assertIsInstance(result, str)
        self.assertIn("exec 模式", result)


class TestExecutorMessagesTemplate(unittest.TestCase):
    """测试 Executor 消息模板"""
    
    def test_command_success_template(self):
        """测试命令成功模板"""
        result = tpl.COMMAND_SUCCESS.format(
            command="echo test",
            returncode=0,
            output="test",
            error=""
        )
        self.assertIn("echo test", result)
        self.assertIn("0", result)
        self.assertIn("test", result)
    
    def test_command_timeout_template(self):
        """测试命令超时模板"""
        result = tpl.COMMAND_TIMEOUT.format(command="long_cmd")
        self.assertIn("long_cmd", result)
        self.assertIn("超时", result)
    
    def test_command_error_template(self):
        """测试命令错误模板"""
        result = tpl.COMMAND_ERROR.format(error="test error")
        self.assertIn("test error", result)
    
    def test_help_text_template(self):
        """测试帮助文本模板"""
        self.assertIsInstance(tpl.HELP_TEXT, str)
        self.assertGreater(len(tpl.HELP_TEXT), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
