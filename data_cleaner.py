import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass

from logger import get_logger
from config import get_config


@dataclass
class CleaningResult:
    original_count: int
    cleaned_count: int
    removed_items: List[str]
    cleaned_pairs: List[Dict[str, str]]


class DataCleaner:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.cleaning_config = self.config.get_cleaning_config()

        self._noise_words: Set[str] = {
            'example', 'examples', 'note', 'notes', 'see', 'cf', 'compare',
            'related', 'see also', 'synonym', 'antonym', 'usage', 'see also',
            'reference', 'references', 'derived', 'etymology', 'origin'
        }

        self._html_tags_pattern = re.compile(r'<[^>]+>')
        self._url_pattern = re.compile(r'https?://\S+')
        self._email_pattern = re.compile(r'[\w\.\-]+@[\w\.\-]+\.\w+')
        self._phone_pattern = re.compile(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}')
        self._bracket_ref_pattern = re.compile(r'\[\d+\]|\[\w+\]')
        self._multiple_spaces = re.compile(r'\s+')

    def clean(self, word_definition_pairs: List[Dict[str, str]]) -> CleaningResult:
        original_count = len(word_definition_pairs)
        cleaned_pairs: List[Dict[str, str]] = []
        removed_items: List[str] = []

        for pair in word_definition_pairs:
            word = pair.get('word', '').strip()
            definition = pair.get('definition', '').strip()

            if self._is_valid_pair(word, definition):
                cleaned_word = self._clean_text(word)
                cleaned_definition = self._clean_text(definition)

                if cleaned_word and cleaned_definition:
                    cleaned_pairs.append({
                        'word': cleaned_word,
                        'definition': cleaned_definition
                    })
            else:
                removed_items.append(f"{word}: {definition[:50]}...")

        self.logger.info(f"Cleaning complete: {original_count} -> {len(cleaned_pairs)} pairs")

        return CleaningResult(
            original_count=original_count,
            cleaned_count=len(cleaned_pairs),
            removed_items=removed_items,
            cleaned_pairs=cleaned_pairs
        )

    def _is_valid_pair(self, word: str, definition: str) -> bool:
        if not word or not definition:
            return False

        word_lower = word.lower()
        for noise_word in self._noise_words:
            if word_lower == noise_word or word_lower.startswith(noise_word + ' '):
                return False

        if definition.lower().startswith('example'):
            return False

        if len(word) < 2 or len(definition) < 1:
            return False

        return True

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""

        if self.cleaning_config.get('remove_urls', True):
            text = self._url_pattern.sub('', text)

        if self.cleaning_config.get('remove_emails', True):
            text = self._email_pattern.sub('', text)

        if self.cleaning_config.get('remove_phone_numbers', True):
            text = self._phone_pattern.sub('', text)

        if self.cleaning_config.get('remove_formatting_markers', True):
            text = self._html_tags_pattern.sub('', text)
            text = self._bracket_ref_pattern.sub('', text)

        text = text.replace('\\n', ' ')
        text = text.replace('\\t', ' ')

        if self.cleaning_config.get('trim_whitespace', True):
            text = self._multiple_spaces.sub(' ', text)

        text = text.strip()

        return text

    def remove_duplicates(self, word_definition_pairs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        seen: Set[str] = set()
        unique_pairs: List[Dict[str, str]] = []

        for pair in word_definition_pairs:
            key = (pair['word'].lower().strip(), pair['definition'].lower().strip())
            if key not in seen:
                seen.add(key)
                unique_pairs.append(pair)

        removed_count = len(word_definition_pairs) - len(unique_pairs)
        if removed_count > 0:
            self.logger.info(f"Removed {removed_count} duplicate pairs")

        return unique_pairs

    def filter_by_confidence(self, pairs: List[Dict[str, Any]], threshold: float = 0.5) -> List[Dict[str, Any]]:
        filtered = [p for p in pairs if p.get('confidence', 1.0) >= threshold]
        self.logger.info(f"Filtered by confidence: {len(pairs)} -> {len(filtered)} pairs (threshold: {threshold})")
        return filtered

    def deduplicate_words(self, word_definition_pairs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        word_map: Dict[str, Dict[str, str]] = {}

        for pair in word_definition_pairs:
            word_lower = pair['word'].lower()
            if word_lower not in word_map:
                word_map[word_lower] = pair
            else:
                if len(pair['definition']) > len(word_map[word_lower]['definition']):
                    word_map[word_lower] = pair

        result = list(word_map.values())
        removed = len(word_definition_pairs) - len(result)
        if removed > 0:
            self.logger.info(f"Deduplicated words: removed {removed} duplicates")

        return result


class CleaningError(Exception):
    pass


def clean_word_definitions(pairs: List[Dict[str, str]]) -> CleaningResult:
    cleaner = DataCleaner()
    return cleaner.clean(pairs)


def deduplicate_pairs(pairs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    cleaner = DataCleaner()
    unique = cleaner.remove_duplicates(pairs)
    return cleaner.deduplicate_words(unique)