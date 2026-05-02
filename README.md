# Anki单词转换器

一个强大的Python工具，使用AI将Word文档转换为Anki记忆卡，支持自定义API端点和内容过滤。

## 功能特点

- **Word文档解析**：支持`.docx`和`.txt`格式文档
- **AI内容识别**：使用OpenAI API兼容服务识别英语单词及其释义
- **智能内容过滤**：自动去除语法规则、示例和笔记等无关内容
- **Token高效处理**：将大型文档分块以保持在API token限制内（< 4096 tokens）
- **多种输出格式**：生成`.csv`或`.apkg`格式的Anki兼容文件
- **可自定义配置**：支持自定义API端点、密钥和识别规则
- **强大的错误处理**：优雅处理API失败和文档解析错误
- **百词斩风格选择题**：生成带混淆选项的选择题卡片，支持自定义干扰项数量
- **规则解析模式**：无需AI即可解析规范格式的单词列表
- **彩色命令行UI**：美观的交互界面，支持颜色高亮和进度显示
- **Web界面**：基于Flask的在线转换平台
- **GitHub Actions**：自动化CI/CD工作流

## 界面预览

### 启动界面

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   █████╗     ██╗  ██████╗ ██████╗  ██████╗  ██████╗ ██████╗  ║
║  ██╔══██╗   ███║ ██╔════╝ ██╔══██╗ ██╔══██╗ ██╔══██╗ ██╔══██╗ ║
║  ███████║   ╚██║ ██║  ███╗██████╔╝ ██████╔╝ ██████╔╝ ██████╔╝ ║
║  ██╔══██║    ██║ ██║   ██║██╔══██╗ ██╔══██╗ ██╔══██╗ ██╔══██╗ ║
║  ██║  ██║    ██║ ╚██████╔╝██║  ██║ ██║  ██║ ██║  ██║ ██║  ██║ ║
║  ╚═╝  ╚═╝    ╚═╝  ╚═════╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝ ║
║                                                              ║
║               Anki Word Converter v2.0                        ║
║           Transform Words into Memories                       ║
╚══════════════════════════════════════════════════════════════╝
```

### 主菜单

```
╔══════════════════════════════════════════════════════════════╗
║                         主菜单                               ║
╠══════════════════════════════════════════════════════════════╣
║  [1] 基本模式          - 解析文档生成标准记忆卡          ║
║  [2] 选择题模式        - 生成百词斩风格选择题卡片        ║
║  [3] 配置设置          - 修改API和识别参数               ║
║  [4] 测试工具          - 测试API连接等                  ║
║  [5] 使用帮助          - 查看详细使用说明                ║
║  [0] 退出程序                                             ║
╚══════════════════════════════════════════════════════════════╝
```

## 安装

### 前置要求

- Python 3.7+
- pip包管理器

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### Web界面（推荐）

启动Web服务器并访问浏览器界面：

```bash
python web_app.py
```

然后在浏览器中打开 http://127.0.0.1:5000

### 交互式菜单

```bash
python interactive.py
```

### 命令行模式

```bash
python main.py document.docx
```

### GitHub Actions

将文件推送到GitHub仓库，触发自动化工作流：

1. 将`.github/workflows/anki-converter.yml`添加到仓库
2. 推送包含`.txt`或`.docx`文件的提交
3. 在GitHub Actions页面查看进度
4. 下载生成的Anki文件

或者手动触发工作流：
1. 进入仓库的Actions页面
2. 选择"Anki Word Converter"工作流
3. 点击"Run workflow"
4. 填写参数并运行

## 选择题模式（百词斩风格）

使用 `--quiz-mode` 参数可以生成带有多个选项的记忆卡：

```bash
python main.py words.txt --quiz-mode --num-distractors 3
```

## 不使用AI模式

如果您的文档已经是规范的单词-释义格式：

```bash
python main.py word_list.txt --no-ai
```

**支持的规范格式**：
- `624. words 单词`
- `1. importance 重要性`

## 配置

编辑`config.json`文件：

```json
{
    "api": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "your-api-key-here",
        "model": "gpt-3.5-turbo"
    }
}
```

## 项目结构

```
ankicard/
├── .github/
│   └── workflows/
│       └── anki-converter.yml    # GitHub Actions工作流
├── templates/
│   └── index.html                # Web界面模板
├── config.json                   # 配置文件
├── config.py                    # 配置管理器
├── cli_ui.py                    # 命令行UI界面
├── web_app.py                   # Web应用
├── main.py                      # CLI主入口
├── interactive.py                # 交互式菜单
├── document_parser.py            # 文档解析器
├── ai_client.py                 # OpenAI API客户端
├── content_recognizer.py         # AI内容识别器
├── data_cleaner.py              # 数据清洗
├── distractor_generator.py       # 干扰选项生成器
├── anki_generator.py            # Anki卡片生成器
├── requirements.txt             # 依赖包
└── README.md                    # 本文档
```

## 工作原理

### Web界面流程
1. 用户上传文件
2. 服务器接收并保存
3. 调用转换逻辑
4. 生成Anki文件
5. 返回下载链接

### GitHub Actions流程
1. 触发工作流（推送或手动）
2. 检出代码
3. 安装依赖
4. 检查输入文件
5. 运行转换
6. 上传生成的文件作为artifact

## 故障排除

### Web界面问题
- 确保Flask已安装：`pip install flask`
- 检查端口5000是否被占用
- 查看控制台错误日志

### GitHub Actions问题
- 确保仓库有workflow权限
- 检查 Secrets 配置
- 查看Actions日志定位问题

## 示例

### 输入（规范格式.txt）
```
624. words 单词
625. repeat 重复
```

### 输出
- CSV格式：可直接导入Anki
- APKG格式：Anki牌组文件

## 许可证

MIT许可证
