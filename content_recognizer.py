import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ai_client import AIClient, AIResponse, create_ai_client
from logger import get_logger
from config import get_config


@dataclass
class WordDefinition:
    word: str
    definition: str
    confidence: float = 1.0
    source: str = "ai"


class ContentRecognizer:
    SYSTEM_PROMPT = """You are an expert at identifying English vocabulary words and their definitions from text.
Your task is to extract word-definition pairs from the given text.

Rules:
1. Only extract actual English vocabulary words (not proper nouns, not example sentences)
2. Each word must have a clear, concise definition
3. Filter out: notes, examples, related terms, usage notes, cross-references, and any meta-information
4. Definitions should be in the same language as the word (English definitions for English words)
5. If a word has multiple meanings, extract only the primary/most important one
6. Exclude any content that appears to be: footnotes, annotations, or editorial comments
7. For numbered lists, extract the word and its definition
8. Ignore grammar rules, sentence structures, and other non-vocabulary content

Output format - Return ONLY valid JSON array:
[
  {"word": "example", "definition": "a thing characteristic of its kind or illustrating a general rule"},
  {"word": "vocabulary", "definition": "the body of words used in a particular language"}
]

Important:
- Return ONLY the JSON array, no explanations or additional text
- If no valid word-definition pairs are found, return an empty array []
- Do not include any markdown formatting or code blocks in your response"""

    def __init__(self, ai_client: Optional[AIClient] = None):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.recognition_config = self.config.get_recognition_config()
        self._ai_client = ai_client
        self.MAX_TOKEN_SIZE = 4000  # 预留一些空间

    @property
    def ai_client(self) -> AIClient:
        if self._ai_client is None:
            self._ai_client = create_ai_client()
        return self._ai_client

    def recognize(self, content: str, use_ai: bool = True) -> List[WordDefinition]:
        if not use_ai:
            return self._parse_with_rules(content)
        
        cleaned_content = self._preprocess_content(content)

        if not cleaned_content.strip():
            self.logger.warning("Content is empty after preprocessing")
            return []

        self.logger.info(f"Processing content ({len(cleaned_content)} chars)")

        chunks = self._split_into_chunks(cleaned_content)
        self.logger.info(f"Split content into {len(chunks)} chunks")

        all_word_definitions = []
        for i, chunk in enumerate(chunks):
            self.logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            response = self.ai_client.call(
                prompt=self._build_prompt(chunk),
                system_prompt=self.SYSTEM_PROMPT
            )

            if not response.success:
                self.logger.error(f"AI recognition failed for chunk {i+1}: {response.error}")
                continue

            word_definitions = self._parse_response(response.content, chunk)
            all_word_definitions.extend(word_definitions)

        self.logger.info(f"Total extracted: {len(all_word_definitions)} word-definition pairs")
        return all_word_definitions

    def _parse_with_rules(self, content: str) -> List[WordDefinition]:
        """使用规则解析文本，不依赖AI"""
        self.logger.info("Using rule-based parsing (no AI)")
        word_definitions = []

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配格式：数字. 单词 释义
            # 例如：624. words 单词
            pattern = r'^\s*\d+\.\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(.*)$'
            match = re.match(pattern, line)
            if match:
                word = match.group(1).strip()
                definition = match.group(2).strip()

                if self._is_valid_word(word) and self._is_valid_definition(definition):
                    word_definitions.append(WordDefinition(
                        word=word,
                        definition=definition,
                        confidence=0.95,
                        source="rule-based"
                    ))

        self.logger.info(f"Rule-based parsing found {len(word_definitions)} word-definition pairs")
        return word_definitions

    def _split_into_chunks(self, content: str) -> List[str]:
        chunks = []
        current_chunk = []
        current_length = 0

        lines = content.split('\n')
        for line in lines:
            line_length = len(line)
            if current_length + line_length > self.MAX_TOKEN_SIZE:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
            current_chunk.append(line)
            current_length += line_length + 1  # +1 for newline

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def _preprocess_content(self, content: str) -> str:
        lines = content.split('\n')
        processed_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if self._is_noise_line(line):
                continue

            line = self._clean_line(line)
            if line:
                processed_lines.append(line)

        return '\n'.join(processed_lines)

    def _is_noise_line(self, line: str) -> bool:
        exclude_patterns = self.recognition_config.get('exclude_patterns', [])

        for pattern in exclude_patterns:
            if pattern.lower() in line.lower():
                return True

        if re.match(r'^[\d\.\)\}]+\s*$', line):
            return True

        if re.match(r'^https?://', line):
            return True

        if re.match(r'^[\w\.\-]+@[\w\.\-]+\.\w+$', line):
            return True

        grammar_patterns = [
            r'^被动语态',
            r'^进行时态',
            r'^现在进行时',
            r'^过去进行时',
            r'^现在完成时',
            r'^过去完成时',
            r'^名词\+定语从句',
            r'^动词\+宾语从句',
            r'^非限制性定语从句',
            r'^作用：',
            r'^so \+adj\+ that',
            r'^so that',
        ]

        for pattern in grammar_patterns:
            if re.match(pattern, line):
                return True

        return False

    def _clean_line(self, line: str) -> str:
        line = re.sub(r'<[^>]+>', '', line)

        line = re.sub(r'\[\d+\]|\[\w+\]', '', line)

        line = re.sub(r'\s+', ' ', line)

        return line.strip()

    def _build_prompt(self, content: str) -> str:
        return f"""Extract word-definition pairs from the following text. Focus on numbered list items and vocabulary words with definitions:

---
{content}
---

Return ONLY a JSON array of word-definition pairs. Each pair should have:
- "word": The English vocabulary word
- "definition": A clear, concise definition (1-2 sentences max)

Exclude any notes, examples, annotations, or non-vocabulary content."""

    def _parse_response(self, response_content: Optional[str], original_content: str) -> List[WordDefinition]:
        if not response_content:
            return []

        try:
            json_str = self._extract_json(response_content)
            data = json.loads(json_str)

            if not isinstance(data, list):
                self.logger.warning("Response is not a list, attempting fallback recognition")
                return self._fallback_recognition(original_content)

            word_definitions = []
            for item in data:
                if isinstance(item, dict) and 'word' in item and 'definition' in item:
                    word = item['word'].strip()
                    definition = item['definition'].strip()

                    if self._is_valid_word(word) and self._is_valid_definition(definition):
                        word_definitions.append(WordDefinition(
                            word=word,
                            definition=definition,
                            confidence=0.9,
                            source="ai"
                        ))

            self.logger.info(f"Extracted {len(word_definitions)} word-definition pairs")
            return word_definitions

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON: {e}, using fallback recognition")
            return self._fallback_recognition(original_content)

    def _extract_json(self, text: str) -> str:
        text = text.strip()

        if text.startswith('```'):
            lines = text.split('\n')
            text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])

        text = text.strip()

        if text.startswith('['):
            start_idx = 0
        else:
            start_idx = text.find('[')
            if start_idx == -1:
                start_idx = 0

        if start_idx > 0:
            text = text[start_idx:]

        last_bracket = text.rfind(']')
        if last_bracket != -1:
            text = text[:last_bracket + 1]

        return text

    def _is_valid_word(self, word: str) -> bool:
        if not word or len(word) < 2:
            return False

        if len(word) > self.recognition_config.get('max_word_length', 30):
            return False

        if not re.match(r'^[a-zA-Z\-\s]+$', word):
            return False

        return True

    def _is_valid_definition(self, definition: str) -> bool:
        if not definition or len(definition) < 1:
            return False

        if len(definition) > 500:
            return False

        return True

    def _fallback_recognition(self, content: str) -> List[WordDefinition]:
        self.logger.info("Using fallback pattern-based recognition")
        word_definitions = []

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            patterns = [
                r'^\d+\.\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*[\-\—\:]\s*(.*)$',
                r'^\d+\.\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*(?:n\.|adj\.|v\.|prep\.|adv\.)\s*(.*)$',
                r'^([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*[\-\—\:]\s*(.*)$',
                r'^([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*(?:n\.|adj\.|v\.|prep\.|adv\.)\s*(.*)$',
            ]

            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    word = match.group(1).strip()
                    definition = match.group(2).strip()

                    if self._is_valid_word(word) and self._is_valid_definition(definition):
                        if not any(wd.word.lower() == word.lower() for wd in word_definitions):
                            word_definitions.append(WordDefinition(
                                word=word,
                                definition=definition,
                                confidence=0.5,
                                source="fallback"
                            ))
                    break

        self.logger.info(f"Fallback recognition found {len(word_definitions)} pairs")
        return word_definitions


class RecognitionError(Exception):
    pass


def recognize_content(content: str, ai_client: Optional[AIClient] = None) -> List[WordDefinition]:
    recognizer = ContentRecognizer(ai_client)
    return recognizer.recognize(content)