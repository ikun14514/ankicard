import csv
import json
import os
import zipfile
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from logger import get_logger
from config import get_config
from distractor_generator import QuizCard


class AnkiGeneratorError(Exception):
    pass


class AnkiGenerator:
    def __init__(self, output_format: str = "csv"):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.output_config = self.config.get_output_config()

        valid_formats = ['csv', 'apkg']
        if output_format not in valid_formats:
            raise AnkiGeneratorError(f"Invalid output format: {output_format}. Must be one of {valid_formats}")
        self.output_format = output_format

    def generate(self, cards: Union[List[Dict[str, str]], List[QuizCard]], output_path: str) -> str:
        if not cards:
            raise AnkiGeneratorError("No cards provided")

        self.logger.info(f"Generating Anki file with {len(cards)} cards in {self.output_format} format")

        if self.output_format == 'csv':
            return self._generate_csv(cards, output_path)
        elif self.output_format == 'apkg':
            return self._generate_apkg(cards, output_path)
        else:
            raise AnkiGeneratorError(f"Unsupported format: {self.output_format}")

    def _generate_csv(self, cards: Union[List[Dict[str, str]], List[QuizCard]], output_path: str) -> str:
        output_path = self._ensure_extension(output_path, 'csv')

        delimiter = self.output_config.get('csv_delimiter', ';')
        include_headers = self.output_config.get('include_headers', True)

        quoting_mode = self.output_config.get('csv_quoting', 'minimal')
        quoting = getattr(csv, f'QUOTE_{quoting_mode.upper()}', csv.QUOTE_MINIMAL)

        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=delimiter, quoting=quoting)

                if include_headers:
                    # 检查卡片类型
                    if self._is_quiz_card(cards):
                        writer.writerow(['Front', 'Back', 'Options', 'CorrectAnswer'])
                    else:
                        writer.writerow(['Front', 'Back'])

                for card in cards:
                    if self._is_quiz_card(card):
                        front = self._format_quiz_front(card.word)
                        back = self._format_quiz_back(card)
                        options = json.dumps(card.all_options, ensure_ascii=False)
                        correct_answer = card.correct_definition
                        writer.writerow([front, back, options, correct_answer])
                    else:
                        front = self._format_front(card['word'])
                        back = self._format_back(card['definition'])
                        writer.writerow([front, back])

            self.logger.info(f"CSV file generated: {output_path}")
            return output_path

        except Exception as e:
            raise AnkiGeneratorError(f"Failed to write CSV file: {e}")

    def _generate_apkg(self, cards: Union[List[Dict[str, str]], List[QuizCard]], output_path: str) -> str:
        output_path = self._ensure_extension(output_path, 'apkg')

        temp_dir = Path(output_path).parent / f"_temp_anki_{os.getpid()}"
        temp_dir.mkdir(exist_ok=True)

        try:
            collection_path = temp_dir / "collection.ank2"
            media_dir = temp_dir / "media"

            media_dir.mkdir(exist_ok=True)

            self._create_collection_json(cards, collection_path)

            media_files = self._create_media_files(cards, media_dir)

            self._create_apkg_file(
                output_path,
                collection_path,
                media_files
            )

            self.logger.info(f"APKG file generated: {output_path}")
            return output_path

        except Exception as e:
            raise AnkiGeneratorError(f"Failed to generate APKG file: {e}")
        finally:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _create_collection_json(self, cards: Union[List[Dict[str, str]], List[QuizCard]], output_path: Path) -> None:
        deck_name = self.output_config.get('deck_name', 'WordCards')
        timestamp = int(datetime.now().timestamp() * 1000)

        cards_data = []
        for i, card in enumerate(cards):
            note_id = timestamp + i
            card_id = timestamp + i + 1000000

            if self._is_quiz_card(card):
                fields = {
                    "Front": self._format_quiz_front(card.word),
                    "Back": self._format_quiz_back(card),
                    "Options": json.dumps(card.all_options, ensure_ascii=False),
                    "CorrectAnswer": card.correct_definition
                }
            else:
                fields = {
                    "Front": self._format_front(card['word']),
                    "Back": self._format_back(card['definition'])
                }

            card_data = {
                "id": card_id,
                "noteId": note_id,
                "deckId": 1,
                "template": 0,
                "fields": fields
            }
            cards_data.append(card_data)

        # 根据卡片类型选择合适的模型
        if self._is_quiz_card(cards):
            model_name = "QuizCard"
            fields = ["Front", "Back", "Options", "CorrectAnswer"]
        else:
            model_name = "Basic"
            fields = ["Front", "Back"]

        collection = {
            "notes": [
                {
                    "id": timestamp + i,
                    "guid": f"{timestamp + i:016x}",
                    "deckId": 1,
                    "fields": {
                        field: card_data['fields'][field]
                        for field in fields
                    },
                    "tags": []
                }
                for i, card_data in enumerate(cards_data)
            ],
            "cards": cards_data,
            "decks": {
                "1": {
                    "name": deck_name,
                    "id": 1,
                    "extendNew": 10,
                    "extendRev": 10
                }
            },
            "models": {
                "1": {
                    "name": model_name,
                    "id": 1,
                    "fields": fields,
                    "templates": [
                        {
                            "name": "Forward",
                            "Front": "{{Front}}",
                            "Back": "{{Back}}"
                        }
                    ]
                }
            },
            "conf": {},
            "tags": []
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(collection, f, ensure_ascii=False, indent=2)

    def _create_media_files(self, cards: Union[List[Dict[str, str]], List[QuizCard]], media_dir: Path) -> Dict[int, str]:
        media_files = {}
        return media_files

    def _create_apkg_file(
        self,
        output_path: str,
        collection_path: Path,
        media_files: Dict[int, str]
    ) -> None:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(collection_path, 'collection.ank2')

            for idx, filepath in media_files.items():
                if Path(filepath).exists():
                    zipf.write(filepath, f"media/{idx}")

            meta = {
                "creator": "AnkiWordConverter",
                "version": 1,
                "mediaFiles": list(media_files.values())
            }
            zipf.writestr('meta', json.dumps(meta, ensure_ascii=False))

    def _format_front(self, word: str) -> str:
        return f"<div class=\"front\">{word}</div>"

    def _format_back(self, definition: str) -> str:
        return f"<div class=\"back\">{definition}</div>"

    def _format_quiz_front(self, word: str) -> str:
        """格式化选择题卡片的正面，只显示单词"""
        html = f"""
<div class="quiz-front">
    <h3>{word}</h3>
</div>
"""
        return html.strip()

    def _format_quiz_back(self, quiz_card: QuizCard) -> str:
        """格式化选择题卡片的背面，显示选项和正确答案"""
        options_html = ""
        for i, option in enumerate(quiz_card.all_options):
            is_correct = option == quiz_card.correct_definition
            class_name = "correct" if is_correct else "incorrect"
            letter = chr(65 + i)  # A, B, C, D...
            options_html += f'<div class="option {class_name}">{letter}. {option}</div>\n'

        html = f"""
<div class="quiz-back">
    <h3>{quiz_card.word}</h3>
    <div class="options">
{options_html}
    </div>
    <div class="answer">
        <p>正确答案: {quiz_card.correct_definition}</p>
    </div>
</div>
"""
        return html.strip()

    def _ensure_extension(self, path: str, ext: str) -> str:
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"anki_cards_{timestamp}.{ext}"

        p = Path(path)
        if p.suffix.lower() != f'.{ext}':
            path = str(p.with_suffix(f'.{ext}'))

        return path

    def _is_quiz_card(self, card_or_cards: Union[List, QuizCard, Dict]) -> bool:
        """检查卡片或卡片列表是否包含QuizCard对象"""
        if isinstance(card_or_cards, list) and card_or_cards:
            # 如果是列表，检查第一个元素
            card = card_or_cards[0]
        else:
            # 如果是单个对象，直接检查
            card = card_or_cards
        return hasattr(card, 'word') and hasattr(card, 'correct_definition') and hasattr(card, 'all_options')

    def preview(self, cards: Union[List[Dict[str, str]], List[QuizCard]], limit: int = 5) -> str:
        preview_cards = cards[:limit]
        lines = ["=" * 50, "ANKI CARD PREVIEW", "=" * 50]

        if self._is_quiz_card(cards):
            for i, card in enumerate(preview_cards, 1):
                lines.append(f"\nCard #{i}")
                lines.append(f"  Word: {card.word}")
                lines.append("  Options:")
                for j, option in enumerate(card.all_options):
                    letter = chr(65 + j)
                    is_correct = option == card.correct_definition
                    marker = " (*)" if is_correct else ""
                    lines.append(f"    {letter}. {option}{marker}")
        else:
            for i, card in enumerate(preview_cards, 1):
                lines.append(f"\nCard #{i}")
                lines.append(f"  Front: {card['word']}")
                lines.append(f"  Back:  {card['definition']}")

        if len(cards) > limit:
            lines.append(f"\n... and {len(cards) - limit} more cards")

        lines.append("=" * 50)
        return "\n".join(lines)


class AnkiGeneratorError(Exception):
    pass


def generate_anki_cards(
    cards: Union[List[Dict[str, str]], List[QuizCard]],
    output_path: str,
    output_format: str = "csv"
) -> str:
    generator = AnkiGenerator(output_format)
    return generator.generate(cards, output_path)


def preview_cards(cards: Union[List[Dict[str, str]], List[QuizCard]], limit: int = 5) -> str:
    generator = AnkiGenerator()
    return generator.preview(cards, limit)