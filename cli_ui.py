import sys
import os


class CommandLineUI:
    # ANSI颜色代码
    COLORS = {
        'reset': '\033[0m',
        'black': '\033[30m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bright_black': '\033[90m',
        'bright_red': '\033[91m',
        'bright_green': '\033[92m',
        'bright_yellow': '\033[93m',
        'bright_blue': '\033[94m',
        'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m',
        'bright_white': '\033[97m',
    }

    BACKGROUNDS = {
        'black': '\033[40m',
        'red': '\033[41m',
        'green': '\033[42m',
        'yellow': '\033[43m',
        'blue': '\033[44m',
        'magenta': '\033[45m',
        'cyan': '\033[46m',
        'white': '\033[47m',
    }

    STYLES = {
        'bold': '\033[1m',
        'underline': '\033[4m',
        'reverse': '\033[7m',
    }

    BANNER = r"""
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
    """

    MENU_OPTIONS = """
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
    """

    MODE_DESCRIPTIONS = {
        'basic': """
    ════════════════════════════════════════════════════════════════
                         基本模式说明
    ════════════════════════════════════════════════════════════════
    此模式会将您的文档转换为标准的Anki记忆卡。

    支持的功能：
    * 解析.docx和.txt格式文档
    * AI智能识别单词和释义
    * 自动过滤无关内容
    * 支持规范格式批量导入
    * 生成.csv或.apkg格式

    输入示例：
    * 624. words 单词
    * vocabulary n. 词汇
    * important - 重要的
        """,
        'quiz': """
    ════════════════════════════════════════════════════════════════
                         选择题模式说明
    ════════════════════════════════════════════════════════════════
    此模式会生成带有干扰选项的选择题卡片，模仿百词斩的学习方式。

    支持的功能：
    * 4选1选择题模式
    * AI智能生成干扰选项
    * 或使用其他单词释义作为干扰
    * 答案顺序随机打乱
    * HTML格式精美展示

    使用方式：
    * python main.py words.txt --quiz-mode
    * python main.py words.txt --quiz-mode --num-distractors 4
        """,
        'config': """
    ════════════════════════════════════════════════════════════════
                         配置说明
    ════════════════════════════════════════════════════════════════
    您可以通过以下方式配置程序：

    1. 命令行参数（优先级最高）：
       --api-key YOUR_KEY
       --base-url https://api.example.com/v1
       --model gpt-3.5-turbo

    2. config.json配置文件：
       位于程序目录下的config.json文件

    3. 环境变量：
       ANKI_API_KEY
       ANKI_BASE_URL
        """,
        'test': """
    ════════════════════════════════════════════════════════════════
                         测试工具
    ════════════════════════════════════════════════════════════════
    可用的测试选项：

    * 测试API连接
      python main.py --test-api

    * 预览模式（不生成文件）
      python main.py words.txt --preview

    * 查看帮助信息
      python main.py --help
        """
    }

    def __init__(self):
        self.use_color = self._check_color_support()

    def _check_color_support(self) -> bool:
        """检查终端是否支持颜色"""
        if not hasattr(sys.stdout, 'fileno'):
            return False
        if not os.isatty(sys.stdout.fileno()):
            return False
        if os.name == 'nt' and 'TERM' not in os.environ:
            return False
        return True

    def c(self, text: str, color: str = 'white', style: str = None, background: str = None) -> str:
        """添加颜色和样式"""
        if not self.use_color:
            return text

        result = ''
        if background and background in self.BACKGROUNDS:
            result += self.BACKGROUNDS[background]
        if color and color in self.COLORS:
            result += self.COLORS[color]
        if style and style in self.STYLES:
            result += self.STYLES[style]
        result += text + self.COLORS['reset']
        return result

    def print_banner(self):
        """打印欢迎横幅"""
        if not self.use_color:
            print(self._strip_ansi(self.BANNER))
            return

        banner_lines = self.BANNER.split('\n')
        colors = ['cyan', 'bright_cyan', 'bright_green', 'bright_yellow', 'bright_green', 'magenta', 'bright_magenta']

        for i, line in enumerate(banner_lines):
            if 'Anki' in line or 'Converter' in line:
                color_idx = (i % len(colors))
                print(self.c(line, colors[color_idx]))
            elif '═' in line or '║' in line:
                print(self.c(line, 'cyan'))
            elif line.strip() and not line.strip().startswith('║'):
                print(self.c(line, 'white'))
            else:
                print(line)

    def print_menu(self):
        """打印主菜单"""
        if not self.use_color:
            print(self._strip_ansi(self.MENU_OPTIONS))
            return

        lines = self.MENU_OPTIONS.split('\n')
        for line in lines:
            if '═' in line or '╔╗╚╝╠╣' in line:
                print(self.c(line, 'cyan'))
            elif '[1]' in line:
                print(self.c(line, 'bright_green'))
            elif '[2]' in line:
                print(self.c(line, 'bright_yellow'))
            elif '[3]' in line:
                print(self.c(line, 'bright_blue'))
            elif '[4]' in line:
                print(self.c(line, 'bright_magenta'))
            elif '[5]' in line:
                print(self.c(line, 'bright_cyan'))
            elif '[0]' in line:
                print(self.c(line, 'bright_red'))
            elif '主菜单' in line or '主功能' in line:
                print(self.c(line, 'white', style='bold'))
            else:
                print(line)

    def print_mode_description(self, mode: str):
        """打印指定模式的详细说明"""
        desc = self.MODE_DESCRIPTIONS.get(mode, "未知模式")
        print(desc)

    def print_success(self, message: str):
        """打印成功消息"""
        prefix = self.c('[OK]', 'bright_green', style='bold')
        print(f"{prefix} {message}")

    def print_error(self, message: str):
        """打印错误消息"""
        prefix = self.c('[ERROR]', 'bright_red', style='bold')
        print(f"{prefix} {message}")

    def print_warning(self, message: str):
        """打印警告消息"""
        prefix = self.c('[WARNING]', 'bright_yellow', style='bold')
        print(f"{prefix} {message}")

    def print_info(self, message: str):
        """打印信息消息"""
        prefix = self.c('[INFO]', 'bright_blue', style='bold')
        print(f"{prefix} {message}")

    def print_progress(self, current: int, total: int, message: str = ""):
        """打印进度条"""
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = '#' * filled + '-' * (bar_length - filled)
        percentage = int(100 * current / total)

        if self.use_color:
            progress_bar = self.c(f'{bar}', 'green')
            percentage_text = self.c(f'{percentage}%', 'bright_green', style='bold')
        else:
            progress_bar = f'{bar}'
            percentage_text = f'{percentage}%'

        print(f'\r[{progress_bar}] {percentage_text} {message}', end='', flush=True)
        if current >= total:
            print()

    def get_input(self, prompt: str, default: str = None) -> str:
        """获取用户输入"""
        if default:
            prompt = f"{prompt} [{default}]"

        if self.use_color:
            prompt = self.c(prompt, 'bright_cyan')

        value = input(f"{prompt}: ").strip()
        return value if value else (default or "")

    def print_table(self, headers: list, rows: list, title: str = None):
        """打印表格"""
        if self.use_color:
            header_color = 'bright_green'
            border_color = 'cyan'
        else:
            header_color = border_color = ''

        # 计算列宽
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # 打印标题
        if title:
            print(self.c(title, 'white', style='bold'))
            print()

        # 打印表头
        header_line = "|"
        for i, h in enumerate(headers):
            header_line += f" {h.ljust(col_widths[i])} |"
        print(self.c(header_line, border_color))
        print(self.c("+" + "+".join("-" * (w + 2) for w in col_widths) + "+", border_color))

        # 打印数据行
        for row in rows:
            row_line = "|"
            for i, cell in enumerate(row):
                row_line += f" {str(cell).ljust(col_widths[i])} |"
            print(row_line)

    def _strip_ansi(self, text: str) -> str:
        """移除ANSI转义序列"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def clear_screen(self):
        """清除屏幕"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def pause(self, message: str = "按Enter键继续..."):
        """暂停等待用户操作"""
        if self.use_color:
            message = self.c(message, 'bright_yellow')
        input(message)


def create_ui() -> CommandLineUI:
    """创建UI实例"""
    return CommandLineUI()
