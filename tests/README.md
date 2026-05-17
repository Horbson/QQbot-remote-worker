# QQBot 项目单元测试

## 测试文件结构

```
tests/
├── __init__.py              # 测试包初始化
├── README.md                # 测试说明文档
├── test_executor.py         # Executor 模式测试
├── test_chat.py             # Chat 模式测试
└── test_mode_manager.py     # Mode Manager 测试
```

## 运行测试

### 运行所有测试
```bash
cd C:\Users\horbs\Desktop\qqbot
python -m pytest tests/ -v
```

### 运行特定测试文件
```bash
# Executor 模式测试
python -m pytest tests/test_executor.py -v

# Chat 模式测试
python -m pytest tests/test_chat.py -v

# Mode Manager 测试
python -m pytest tests/test_mode_manager.py -v
```

### 运行特定测试类
```bash
python -m pytest tests/test_executor.py::TestExecutorClass -v
```

### 运行特定测试方法
```bash
python -m pytest tests/test_executor.py::TestExecutorClass::test_initialization -v
```

### 生成覆盖率报告
```bash
python -m pytest tests/ --cov=. --cov-report=html
```

## 测试说明

### test_executor.py

测试 Executor 模式（命令执行）的功能。

**测试类别**:
- `TestRunCommand` - 测试 `run_command()` 函数
  - ✅ echo 命令测试
  - ✅ dir 命令测试
  - ✅ tree 命令测试
  - ✅ 超时处理测试
  - ✅ 不存在的命令测试
  - ✅ 自定义工作目录测试
  - ✅ 错误输出捕获测试

- `TestExecutorClass` - 测试 `Executor` 类
  - ✅ 初始化测试
  - ✅ 消息处理测试（echo, dir, timeout）
  - ✅ 命令处理测试（set_cwd, whereami）
  - ✅ 帮助信息测试

- `TestExecutorMessagesTemplate` - 测试消息模板
  - ✅ 命令成功模板
  - ✅ 命令超时模板
  - ✅ 命令错误模板
  - ✅ 帮助文本模板

**安全说明**: 
> ⚠️ 本测试文件**仅使用安全命令**（dir, echo, tree 等），不包含任何高危命令（如 rm, del, format 等）。

---

### test_chat.py

测试 Chat 模式（LLM 对话）的功能。

**测试类别**:
- `TestChatClass` - 测试 `Chat` 类
  - ✅ 初始化测试
  - ✅ 清除上下文测试
  - ✅ 命令处理测试（new_session, reasoning, confirm/cancel）
  - ✅ 帮助信息测试

- `TestChatMessageHandler` - 测试消息处理
  - ✅ 普通消息回复测试
  - ✅ 工具调用上下文追加测试
  - ✅ 危险工具调用确认测试

- `TestChatMessagesTemplate` - 测试消息模板
  - ✅ 新会话模板
  - ✅ reasoning 强度模板
  - ✅ 未知命令模板

- `TestChatTools` - 测试 Chat 工具
  - ✅ ls/read/write/exec/pwd 基础行为
  - ✅ 写入确认策略
  - ✅ 危险命令识别

- `TestChatLLMCall` - 测试 LLM 调用（需要 API 配置）
  - ⏭️ 基本调用测试（跳过，需要 API）
  - ⏭️ 带推理强度调用测试（跳过，需要 API）

---

### test_mode_manager.py

测试 Mode Manager（模式管理器）的功能。

**测试类别**:
- `TestModeManager` - 测试 `ModeManager` 类
  - ✅ 初始化测试
  - ✅ 模式切换测试
  - ✅ 消息处理测试
  - ✅ 命令处理测试（switch, help, active_mode, modes）
  - ✅ 错误处理测试

- `TestModeManagerCircularSwitch` - 测试循环切换
  - ✅ 循环切换测试

- `TestModeManagerMessagesTemplate` - 测试消息模板
  - ✅ 切换成功/失败模板
  - ✅ 未知命令模板
  - ✅ 帮助模板
  - ✅ 模式列表模板

---

## 测试结果

### 通过标准
- ✅ 所有测试用例通过（跳过需要 API 配置的测试）
- ✅ 无错误（ERROR）
- ✅ 无失败（FAILED）

### 当前状态
```
78 passed, 1 skipped
```

**跳过的测试**:
- `test_call_llm_basic` - 需要有效的 LLM API 配置

---

## 添加新测试

### 测试 Executor 新模式
```python
def test_my_new_feature(self):
    """测试新功能"""
    executor = Executor()
    result = executor.my_new_feature()
    self.assertEqual(result, expected_value)
```

### 测试 Chat 新模式
```python
@patch('mode.chat.core.call_llm')
def test_my_chat_feature(self, mock_call_llm):
    """测试聊天新功能"""
    mock_call_llm.return_value = {"content": "mock response"}
    chat = Chat()
    result = chat.message_handler("test")
    self.assertIn("mock response", result)
```

### 测试 Mode Manager
```python
def test_new_manager_feature(self):
    """测试管理器新功能"""
    manager = ModeManager(modes)
    result = manager.new_feature()
    self.assertTrue(result)
```

---

## 常见问题

### Q: 为什么有些测试跳过？
A: `test_chat.py` 中的 LLM 调用测试需要有效的 API 配置。如果未配置或 API 不可用，测试会自动跳过。

### Q: 如何调试失败的测试？
A: 使用 `-v` 参数查看详细输出，使用 `--tb=long` 查看完整堆栈跟踪：
```bash
python -m pytest tests/test_executor.py -v --tb=long
```

### Q: 如何只运行失败的测试？
A: 使用 `--lf` 参数：
```bash
python -m pytest tests/ --lf
```

### Q: 如何测试安全命令？
A: Executor 测试中只使用以下安全命令：
- `echo` - 输出文本
- `dir` - 列出目录
- `tree` - 显示目录树
- `ping` - 网络测试

**禁止使用**：`rm`, `del`, `format`, `shutdown` 等高危命令。

---

## 持续集成

### GitHub Actions 示例
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.12
    - name: Install dependencies
      run: pip install -r requirements.txt pytest
    - name: Run tests
      run: python -m pytest tests/ -v
```

---

**最后更新**: 2026-03-30
