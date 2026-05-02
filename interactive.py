#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from cli_ui import create_ui
from main import AnkiWordConverter
import argparse


def interactive_menu():
    """交互式菜单主循环"""
    ui = create_ui()

    while True:
        ui.clear_screen()
        ui.print_banner()
        ui.print_menu()

        choice = ui.get_input("请选择功能", "0")

        if choice == '1':
            run_basic_mode(ui)
        elif choice == '2':
            run_quiz_mode(ui)
        elif choice == '3':
            show_config(ui)
        elif choice == '4':
            run_tests(ui)
        elif choice == '5':
            show_help(ui)
        elif choice == '0':
            ui.print_info("感谢使用！再见！")
            break
        else:
            ui.print_error("无效选择，请重新输入")


def run_basic_mode(ui):
    """运行基本模式"""
    ui.clear_screen()
    ui.print_banner()

    print(ui.c("\n基本模式 - 解析文档生成标准记忆卡\n", 'bright_green', style='bold'))

    input_file = ui.get_input("请输入文档路径")
    if not input_file:
        ui.print_error("文档路径不能为空")
        ui.pause()
        return

    if not os.path.exists(input_file):
        ui.print_error(f"文件不存在: {input_file}")
        ui.pause()
        return

    output_file = ui.get_input("输出文件路径（留空自动生成）") or None
    use_ai = ui.get_input("是否使用AI模式？(y/n)", "y").lower() == 'y'
    preview = ui.get_input("是否预览模式？(y/n)", "y").lower() == 'y'

    ui.print_info("正在处理...")

    converter = AnkiWordConverter()
    result = converter.run(
        input_file=input_file,
        output_file=output_file,
        use_ai=use_ai,
        preview_only=preview
    )

    if result['success']:
        ui.print_success(result['message'])
        if result.get('preview'):
            print(result['preview'])
    else:
        ui.print_error(result['message'])
        if result.get('errors'):
            ui.print_error("错误详情:")
            for error in result['errors']:
                print(f"  * {error}")

    ui.pause()


def run_quiz_mode(ui):
    """运行选择题模式"""
    ui.clear_screen()
    ui.print_banner()

    print(ui.c("\n选择题模式 - 生成百词斩风格记忆卡\n", 'bright_yellow', style='bold'))

    input_file = ui.get_input("请输入文档路径")
    if not input_file:
        ui.print_error("文档路径不能为空")
        ui.pause()
        return

    if not os.path.exists(input_file):
        ui.print_error(f"文件不存在: {input_file}")
        ui.pause()
        return

    output_file = ui.get_input("输出文件路径（留空自动生成）") or None
    num_distractors = int(ui.get_input("干扰项数量（3-5）", "3") or "3")
    use_ai = ui.get_input("是否使用AI模式？(y/n)", "y").lower() == 'y'
    preview = ui.get_input("是否预览模式？(y/n)", "y").lower() == 'y'

    ui.print_info("正在处理...")

    converter = AnkiWordConverter()
    result = converter.run(
        input_file=input_file,
        output_file=output_file,
        use_ai=use_ai,
        quiz_mode=True,
        num_distractors=num_distractors,
        preview_only=preview
    )

    if result['success']:
        ui.print_success(result['message'])
        if result.get('preview'):
            print(result['preview'])
    else:
        ui.print_error(result['message'])
        if result.get('errors'):
            ui.print_error("错误详情:")
            for error in result['errors']:
                print(f"  * {error}")

    ui.pause()


def show_config(ui):
    """显示配置信息"""
    ui.clear_screen()
    ui.print_banner()

    print(ui.c("\n配置设置\n", 'bright_blue', style='bold'))

    try:
        from config import get_config
        config = get_config()

        headers = ["配置项", "当前值"]
        rows = [
            ["API Base URL", config.base_url],
            ["API Model", config.model],
            ["Temperature", str(config.temperature)],
            ["Max Tokens", str(config.max_tokens)],
        ]

        ui.print_table(headers, rows, "当前配置")

        print("\n")
        ui.print_info("修改配置请编辑 config.json 文件")

    except Exception as e:
        ui.print_error(f"读取配置失败: {e}")

    ui.pause()


def run_tests(ui):
    """运行测试选项"""
    ui.clear_screen()
    ui.print_banner()

    print(ui.c("\n测试工具\n", 'bright_magenta', style='bold'))

    print("1. 测试API连接")
    print("2. 查看程序版本")
    print("3. 列出支持的文件格式")
    print("0. 返回")

    choice = ui.get_input("请选择", "0")

    if choice == '1':
        test_api_connection(ui)
    elif choice == '2':
        show_version(ui)
    elif choice == '3':
        show_supported_formats(ui)


def test_api_connection(ui):
    """测试API连接"""
    ui.print_info("正在测试API连接...")

    try:
        from ai_client import create_ai_client
        client = create_ai_client()

        if client.test_connection():
            ui.print_success("API连接成功！")
        else:
            ui.print_error("API连接失败")

    except Exception as e:
        ui.print_error(f"API连接错误: {e}")

    ui.pause()


def show_version(ui):
    """显示版本信息"""
    version_info = [
        ["组件", "版本"],
        ["Anki Word Converter", "2.0.0"],
        ["Python", sys.version.split()[0]],
    ]

    ui.print_table(version_info[0], version_info[1:], "版本信息")
    ui.pause()


def show_supported_formats(ui):
    """显示支持的文件格式"""
    formats = [
        ["格式", "类型", "说明"],
        ["docx", "文档", "Word文档格式"],
        ["txt", "文本", "纯文本格式（支持规范格式）"],
        ["csv", "输出", "逗号分隔值格式"],
        ["apkg", "输出", "Anki记忆卡包格式"],
    ]

    ui.print_table(formats[0], formats[1:], "支持的文件格式")
    ui.pause()


def show_help(ui):
    """显示帮助信息"""
    ui.clear_screen()
    ui.print_banner()

    print(ui.c("\n使用帮助\n", 'bright_cyan', style='bold'))

    helps = {
        'basic': """
    =================================================================
                         基本模式使用说明
    =================================================================

    【功能说明】
    基本模式会将您的单词列表转换为标准的Anki记忆卡。

    【输入格式】
    支持以下格式：
    * 规范格式：624. words 单词
    * 带词性：vocabulary n. 词汇
    * 分隔符：important - 重要的
    * 冒号分隔：word: definition

    【使用示例】
    # 使用AI识别（需要配置API）
    python main.py document.docx

    # 不使用AI（规范格式）
    python main.py wordlist.txt --no-ai

    # 预览模式
    python main.py wordlist.txt --preview

    # 指定输出
    python main.py wordlist.txt -o output.csv
        """,
        'quiz': """
    =================================================================
                         选择题模式使用说明
    =================================================================

    【功能说明】
    选择题模式会生成带有4个选项的记忆卡，模仿百词斩的学习方式。

    【工作原理】
    1. 为每个单词生成1个正确答案
    2. 生成N个干扰选项（默认3个）
    3. 将所有选项随机排序
    4. 生成HTML格式的卡片

    【使用示例】
    # 生成选择题（使用其他单词释义作为干扰项）
    python main.py wordlist.txt --quiz-mode

    # 指定干扰项数量
    python main.py wordlist.txt --quiz-mode --num-distractors 4

    # 只使用AI生成干扰项
    python main.py wordlist.txt --quiz-mode --no-use-other-words

    【适用场景】
    * 想要测试自己对单词释义的记忆
    * 想要类似百词斩的学习体验
    * 需要生成练习题
        """
    }

    print(helps['basic'])
    ui.pause()

    ui.clear_screen()
    print(helps['quiz'])
    ui.pause()


def main():
    """主入口"""
    try:
        interactive_menu()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
