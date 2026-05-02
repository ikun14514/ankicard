from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from document_parser import DocumentParserError
from ai_client import AIClientError
from content_recognizer import ContentRecognizer, WordDefinition, RecognitionError
from anki_generator import AnkiGeneratorError, generate_anki_cards, preview_cards
from data_cleaner import DataCleaner
from distractor_generator import DistractorGenerator
from ai_client import create_ai_client
from document_parser import extract_text_from_docx
from logger import get_logger
from config import get_config, reset_config


@dataclass
class ConversionResult:
    success: bool = False
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    cards_count: int = 0
    message: str = ""
    errors: List[str] = field(default_factory=list)
    preview: Optional[List[Dict[str, Any]]] = None

    def add_error(self, error: str):
        self.errors.append(error)
        self.message = error

    def add_message(self, message: str):
        if self.message:
            self.message += " " + message
        else:
            self.message = message


class ErrorHandler:
    def __init__(self, logger):
        self.logger = logger

    def handle(self, error: Exception, result: ConversionResult) -> None:
        error_type = type(error).__name__
        error_msg = f"{error_type}: {error}"
        self.logger.error(error_msg)
        result.add_error(error_msg)


class ConversionPipeline:
    def __init__(self, config_path: Optional[str] = None, logger=None):
        self.config_path = config_path
        self.logger = logger or get_logger(__name__)
        self.config = None
        self.ai_client = None
        self.error_handler = ErrorHandler(self.logger)

    def execute(
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
    ) -> ConversionResult:
        result = ConversionResult(input_file=input_file)

        try:
            self._setup_configuration(api_key, base_url, model)
            self._log_start(input_file, quiz_mode)

            raw_text = self._parse_document(input_file)
            result.add_message(f"Extracted {len(raw_text)} characters from document.")

            word_definitions = self._recognize_content(raw_text, use_ai)
            result.add_message(f"Identified {len(word_definitions)} word pairs.")

            cards = self._clean_and_process_data(word_definitions, confidence_threshold)
            result.add_message(f"Cleaned to {len(cards)} unique pairs.")

            if quiz_mode:
                cards = self._generate_quiz_cards(cards, num_distractors, use_other_words_as_distractors)
                result.add_message(f"Generated {len(cards)} quiz cards with distractors.")

            if preview_only:
                result.preview = preview_cards(cards, limit=10)
                result.cards_count = len(cards)
                result.success = True
                return result

            output_path = self._generate_anki_file(cards, input_file, output_file, output_format, quiz_mode)
            result.output_file = output_path
            result.cards_count = len(cards)
            result.success = True
            result.message = f"Successfully generated {result.cards_count} Anki cards to {output_path}"
            self.logger.info(result.message)

        except Exception as e:
            self.error_handler.handle(e, result)

        return result

    def _setup_configuration(self, api_key: Optional[str], base_url: Optional[str], model: Optional[str]):
        reset_config()
        self.config = get_config(self.config_path)

        if api_key:
            self.config.set('api.api_key', api_key)
        if base_url:
            self.config.set('api.base_url', base_url)
        if model:
            self.config.set('api.model', model)

    def _log_start(self, input_file: str, quiz_mode: bool):
        self.logger.info(f"Starting Anki word conversion: {input_file}")
        mode_name = "Quiz Mode" if quiz_mode else "Basic Mode"
        self.logger.info(f"Running in {mode_name}")

    def _parse_document(self, input_file: str) -> str:
        self.logger.info("Step 1: Parsing document...")
        raw_text = extract_text_from_docx(input_file)
        if not raw_text.strip():
            raise ValueError("Document is empty or contains no readable text")
        return raw_text

    def _recognize_content(self, raw_text: str, use_ai: bool) -> List[WordDefinition]:
        if use_ai:
            self.logger.info("Step 2: Recognizing word-definition pairs with AI...")
            self._ensure_ai_client()
            recognizer = ContentRecognizer(self.ai_client)
            word_definitions = recognizer.recognize(raw_text, use_ai=True)
        else:
            self.logger.info("Step 2: Recognizing word-definition pairs with rule-based parsing...")
            recognizer = ContentRecognizer()
            word_definitions = recognizer.recognize(raw_text, use_ai=False)

        if not word_definitions:
            raise ValueError("No word-definition pairs found in the document")

        return word_definitions

    def _ensure_ai_client(self):
        if self.ai_client is None:
            self.ai_client = create_ai_client(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                model=self.config.model
            )
            if not self.ai_client.test_connection():
                raise AIClientError("Failed to connect to AI API. Please check your configuration.")

    def _clean_and_process_data(self, word_definitions: List[WordDefinition], confidence_threshold: float) -> List[Dict[str, Any]]:
        self.logger.info("Step 3: Cleaning and deduplicating data...")
        cleaner = DataCleaner()
        pairs = [wd.__dict__ for wd in word_definitions]
        pairs = cleaner.filter_by_confidence(pairs, confidence_threshold)
        pairs = cleaner.remove_duplicates(pairs)
        pairs = cleaner.deduplicate_words(pairs)
        return pairs

    def _generate_quiz_cards(self, cards: List[Dict[str, Any]], num_distractors: int, use_other_words_as_distractors: bool) -> List[Dict[str, Any]]:
        self.logger.info("Step 4: Generating quiz cards with distractors...")
        self._ensure_ai_client()
        distractor_generator = DistractorGenerator(self.ai_client)
        return distractor_generator.generate_quiz_cards(
            cards,
            num_distractors=num_distractors,
            use_other_words_as_distractors=use_other_words_as_distractors
        )

    def _generate_anki_file(self, cards: List[Dict[str, Any]], input_file: str, output_file: Optional[str], output_format: str, quiz_mode: bool) -> str:
        self.logger.info(f"Step 5: Generating Anki {output_format.upper()} file...")
        if not output_file:
            timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = __import__('pathlib').Path(input_file).stem
            suffix = "_quiz" if quiz_mode else ""
            output_file = f"{base_name}_anki{suffix}_{timestamp}.{output_format}"

        return generate_anki_cards(cards, output_file, output_format)