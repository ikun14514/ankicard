import json
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from logger import get_logger
from config import get_config
from ai_client import AIClient, create_ai_client


@dataclass
class QuizCard:
    word: str
    correct_definition: str
    distractors: List[str]
    all_options: List[str] = None

    def __post_init__(self):
        if self.all_options is None:
            self.all_options = self._shuffle_options()

    def _shuffle_options(self) -> List[str]:
        options = [self.correct_definition] + self.distractors
        random.shuffle(options)
        return options


class DistractorGenerator:
    SYSTEM_PROMPT = """你是一个专业的词汇学习内容创作者，专门为单词记忆应用生成混淆选项。

你的任务是为每个单词生成几个看起来合理但不正确的释义选项，这些选项要能真正测试学习者对单词的掌握程度。

生成混淆选项的原则：
1. 混淆选项应该与正确选项有一定的相关性，但不能完全相同
2. 混淆选项应该看起来像是合理的释义，不能明显是错误的
3. 混淆选项不应该只是正确选项的同义词或反义词（除非特别要求）
4. 混淆选项的长度和格式应该与正确选项相似
5. 对于中文释义，可以使用形近字、同音词、相关但不同的概念作为混淆选项

注意事项：
- 确保混淆选项不重复
- 确保混淆选项不包含正确答案本身
- 生成的混淆选项总数应该符合要求的数量

请确保你的回复只包含JSON数据，不包含任何其他说明文字。"""

    def __init__(self, ai_client: Optional[AIClient] = None):
        self.logger = get_logger(__name__)
        self.ai_client = ai_client or create_ai_client()

    def generate_distractors(
        self,
        word: str,
        correct_definition: str,
        num_distractors: int = 3,
        all_words: Optional[List[str]] = None
    ) -> List[str]:
        """
        为单词生成混淆选项

        Args:
            word: 目标单词
            correct_definition: 正确释义
            num_distractors: 混淆选项数量
            all_words: 可选的单词列表，如果提供可以使用列表中其他单词的释义作为混淆选项

        Returns:
            混淆选项列表
        """
        try:
            if all_words and len(all_words) > num_distractors + 1:
                # 尝试使用列表中其他单词的释义作为混淆选项
                distractors = self._get_distractors_from_list(word, all_words, num_distractors)
                if len(distractors) == num_distractors:
                    return distractors

            # 使用AI生成混淆选项
            return self._generate_distractors_with_ai(word, correct_definition, num_distractors)

        except Exception as e:
            self.logger.error(f"Failed to generate distractors for {word}: {e}")
            # 回退到简单的混淆选项生成
            return self._generate_simple_distractors(word, correct_definition, num_distractors)

    def _get_distractors_from_list(
        self,
        target_word: str,
        all_words: List[Dict[str, str]],
        num_distractors: int
    ) -> List[str]:
        """
        从单词列表中获取混淆选项

        Args:
            target_word: 目标单词
            all_words: 单词列表，包含单词和释义
            num_distractors: 混淆选项数量

        Returns:
            混淆选项列表
        """
        # 找到目标单词的索引
        target_index = -1
        for i, word_item in enumerate(all_words):
            if word_item.get('word') == target_word:
                target_index = i
                break

        if target_index == -1:
            return []

        # 获取其他单词的释义作为混淆选项
        distractors = []
        for i, word_item in enumerate(all_words):
            if i != target_index and len(distractors) < num_distractors:
                distractors.append(word_item.get('definition', ''))

        return distractors

    def _generate_distractors_with_ai(
        self,
        word: str,
        correct_definition: str,
        num_distractors: int
    ) -> List[str]:
        """
        使用AI生成混淆选项

        Args:
            word: 目标单词
            correct_definition: 正确释义
            num_distractors: 混淆选项数量

        Returns:
            混淆选项列表
        """
        prompt = f"""请为单词 "{word}" 生成 {num_distractors} 个混淆选项。

正确释义是：{correct_definition}

请生成符合以下要求的混淆选项：
1. 混淆选项看起来像是合理的释义
2. 混淆选项与正确释义相关但不相同
3. 混淆选项不能是正确释义本身
4. 混淆选项之间不应该重复

请以JSON数组格式返回，格式如下：
["混淆选项1", "混淆选项2", "混淆选项3"]

只返回JSON数组，不包含任何其他文字。"""

        response = self.ai_client.call(prompt, self.SYSTEM_PROMPT)

        if not response.success:
            raise Exception(f"AI call failed: {response.error}")

        try:
            # 解析JSON响应
            json_str = response.content.strip()
            # 移除可能的markdown代码块标记
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]

            distractors = json.loads(json_str.strip())

            # 验证返回的混淆选项数量
            if len(distractors) < num_distractors:
                # 如果AI生成的数量不足，补充简单的混淆选项
                self.logger.warning(f"AI only generated {len(distractors)} distractors, falling back to simple generation")
                simple_distractors = self._generate_simple_distractors(word, correct_definition, num_distractors - len(distractors))
                distractors.extend(simple_distractors)

            return distractors[:num_distractors]

        except Exception as e:
            self.logger.error(f"Failed to parse AI response: {e}")
            return self._generate_simple_distractors(word, correct_definition, num_distractors)

    def _generate_simple_distractors(
        self,
        word: str,
        correct_definition: str,
        num_distractors: int
    ) -> List[str]:
        """
        简单的混淆选项生成，作为AI生成失败时的后备

        Args:
            word: 目标单词
            correct_definition: 正确释义
            num_distractors: 混淆选项数量

        Returns:
            混淆选项列表
        """
        self.logger.info(f"Using simple distractor generation for {word}")

        # 简单的混淆选项生成策略
        templates = [
            f"与{correct_definition}相关但不同的概念",
            f"看起来像是{correct_definition}的另一个意思",
            f"与{correct_definition}有一定联系但不完全相同的释义",
            f"容易与{correct_definition}混淆的解释"
        ]

        # 如果释义是中文，可以添加一些简单的变化
        if any('\u4e00' <= c <= '\u9fff' for c in correct_definition):
            templates = [
                f"{correct_definition[0] if len(correct_definition) > 0 else ''}义",
                f"相似于{correct_definition}但不完全相同的意思",
                f"与{correct_definition}有一定联系但不同的解释",
                f"看起来像是{correct_definition}但实际不同的释义"
            ]

        # 如果模板数量不够，重复使用
        while len(templates) < num_distractors:
            templates.extend(templates)

        return templates[:num_distractors]

    def create_quiz_card(
        self,
        word: str,
        correct_definition: str,
        num_distractors: int = 3,
        all_words: Optional[List[str]] = None
    ) -> QuizCard:
        """
        创建完整的选择题卡片

        Args:
            word: 目标单词
            correct_definition: 正确释义
            num_distractors: 混淆选项数量
            all_words: 可选的单词列表

        Returns:
            QuizCard对象
        """
        distractors = self.generate_distractors(word, correct_definition, num_distractors, all_words)
        quiz_card = QuizCard(
            word=word,
            correct_definition=correct_definition,
            distractors=distractors
        )
        return quiz_card

    def generate_quiz_cards(
        self,
        word_definitions: List[Dict[str, str]],
        num_distractors: int = 3,
        use_other_words_as_distractors: bool = True
    ) -> List[QuizCard]:
        """
        为单词列表生成选择题卡片

        Args:
            word_definitions: 单词列表，每个元素包含'word'和'definition'
            num_distractors: 每个单词的混淆选项数量
            use_other_words_as_distractors: 是否使用其他单词的释义作为混淆选项

        Returns:
            QuizCard列表
        """
        quiz_cards = []
        all_words = word_definitions if use_other_words_as_distractors else None

        for word_item in word_definitions:
            quiz_card = self.create_quiz_card(
                word=word_item['word'],
                correct_definition=word_item['definition'],
                num_distractors=num_distractors,
                all_words=all_words
            )
            quiz_cards.append(quiz_card)
            self.logger.info(f"Generated quiz card for {word_item['word']}")

        self.logger.info(f"Generated {len(quiz_cards)} quiz cards total")
        return quiz_cards


def create_distractor_generator(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None
) -> DistractorGenerator:
    ai_client = create_ai_client(api_key, base_url, model)
    return DistractorGenerator(ai_client)
