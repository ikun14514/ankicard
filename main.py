#!/usr/bin/env python3
import sys
import argparse
import os
from pathlib import Path
from typing import Optional, List, Dict, Union

from config import get_config, ConfigError
from logger import get_logger, Logger
from ai_client import create_ai_client
from pipeline import ConversionPipeline


class AnkiWordConverter:
    def __init__(self, config_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.pipeline = ConversionPipeline(config_path, self.logger)

    def run(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        output_format: str = "csv",
        preview_only: bool = False,
        confidence_threshold: float = 0.5,
        use_ai: bool = True,
        quiz_mode: bool = False,
        num_distractors: int = 3,
        use_other_words_as_distractors: bool = True
    ) -> Dict[str, any]:
        result = self.pipeline.execute(
            input_file=input_file,
            output_file=output_file,
            api_key=api_key,
            base_url=base_url,
            model=model,
            output_format=output_format,
            preview_only=preview_only,
            confidence_threshold=confidence_threshold,
            use_ai=use_ai,
            quiz_mode=quiz_mode,
            num_distractors=num_distractors,
            use_other_words_as_distractors=use_other_words_as_distractors
        )
        return result.__dict__


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Word documents to Anki flashcard format using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.docx
  %(prog)s document.docx -o output.csv
  %(prog)s document.docx --api-key sk-xxx --base-url https://api.example.com/v1
  %(prog)s document.docx --format apkg --preview
  %(prog)s document.docx --quiz-mode --num-distractors 3
        """
    )

    parser.add_argument(
        'input_file',
        nargs='?',
        help='Path to the input .docx file'
    )

    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='Output file path (default: auto-generated name)'
    )

    parser.add_argument(
        '-c', '--config',
        dest='config_path',
        help='Path to configuration file (default: config.json)'
    )

    parser.add_argument(
        '--api-key',
        dest='api_key',
        help='AI API key (overrides config file)'
    )

    parser.add_argument(
        '--base-url',
        dest='base_url',
        help='AI API base URL (overrides config file)'
    )

    parser.add_argument(
        '--model',
        dest='model',
        help='AI model name (overrides config file)'
    )

    parser.add_argument(
        '-f', '--format',
        dest='output_format',
        choices=['csv', 'apkg'],
        default='csv',
        help='Output format (default: csv)'
    )

    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview cards without generating file'
    )

    parser.add_argument(
        '--confidence',
        dest='confidence_threshold',
        type=float,
        default=0.5,
        help='Minimum confidence threshold (0.0-1.0, default: 0.5)'
    )

    parser.add_argument(
        '--test-api',
        action='store_true',
        help='Test AI API connection and exit'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Use rule-based parsing instead of AI'
    )

    parser.add_argument(
        '--quiz-mode',
        action='store_true',
        help='Generate multiple-choice quiz cards (like Baicizhan)'
    )

    parser.add_argument(
        '--num-distractors',
        type=int,
        default=3,
        help='Number of distractors for quiz cards (default: 3)'
    )

    parser.add_argument(
        '--no-use-other-words',
        action='store_true',
        dest='no_use_other_words',
        help='Do not use other words from the list as distractors'
    )

    return parser


def test_api_connection(args) -> bool:
    try:
        config = get_config(args.config_path)
        if args.api_key:
            config.set('api.api_key', args.api_key)
        if args.base_url:
            config.set('api.base_url', args.base_url)
        if args.model:
            config.set('api.model', args.model)

        print(f"Testing API connection...")
        print(f"  Base URL: {config.base_url}")
        print(f"  Model: {config.model}")

        client = create_ai_client(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model
        )

        if client.test_connection():
            print("✓ API connection successful!")
            return True
        else:
            print("✗ API connection failed")
            return False

    except Exception as e:
        print(f"✗ API connection test failed: {e}")
        return False


def interactive_setup():
    print("=" * 60)
    print("ANKI WORD CONVERTER - SETUP")
    print("=" * 60)

    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    try:
        config = get_config(config_path)
    except:
        print("Configuration file not found. Creating new configuration...")
        config = None

    print("\nPlease configure your AI API settings:\n")

    api_key = input("API Key: ").strip()
    if not api_key:
        api_key = "your-api-key-here"

    base_url = input("Base URL [https://api.openai.com/v1]: ").strip()
    if not base_url:
        base_url = "https://api.openai.com/v1"

    model = input("Model [gpt-3.5-turbo]: ").strip()
    if not model:
        model = "gpt-3.5-turbo"

    output_format = input("Output Format [csv]: ").strip()
    if not output_format:
        output_format = "csv"

    print("\nConfiguration saved to config.json")


def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    if args.test_api:
        success = test_api_connection(args)
        sys.exit(0 if success else 1)

    if args.input_file is None:
        print("Anki Word Converter - Convert Word documents to Anki flashcards")
        print()
        parser.print_help()
        print()
        print("Or run with --test-api to test your AI API connection")
        sys.exit(1)

    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    converter = AnkiWordConverter(config_path=args.config_path)

    result = converter.run(
        input_file=args.input_file,
        output_file=args.output_file,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        output_format=args.output_format,
        preview_only=args.preview,
        confidence_threshold=args.confidence_threshold,
        use_ai=not args.no_ai,
        quiz_mode=args.quiz_mode,
        num_distractors=args.num_distractors,
        use_other_words_as_distractors=not args.no_use_other_words
    )

    if result["success"]:
        print("\n[OK] " + result['message'])
        if result.get("preview"):
            print(result["preview"])
        sys.exit(0)
    else:
        print("\n[ERROR] " + result['message'])
        if result.get("errors"):
            print("\nErrors:")
            for error in result["errors"]:
                print("  - " + error)
        sys.exit(1)


if __name__ == "__main__":
    main()