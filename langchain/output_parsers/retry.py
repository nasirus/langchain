from __future__ import annotations

from typing import Any

from langchain.chains.llm import LLMChain
from langchain.prompts.base import BasePromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import (
    BaseLanguageModel,
    BaseOutputParser,
    OutputParserException,
    PromptValue,
)

NAIVE_COMPLETION_RETRY = """Prompt:
{prompt}
Completion:
{completion}

Above, the Completion did not satisfy the constraints given in the Prompt.
Please try again:"""

NAIVE_COMPLETION_RETRY_WITH_ERROR = """Prompt:
{prompt}
Completion:
{completion}

Above, the Completion did not satisfy the constraints given in the Prompt.
Details: {error}
Please try again:"""

NAIVE_RETRY_PROMPT = PromptTemplate.from_template(NAIVE_COMPLETION_RETRY)
NAIVE_RETRY_WITH_ERROR_PROMPT = PromptTemplate.from_template(
    NAIVE_COMPLETION_RETRY_WITH_ERROR
)


class RetryOutputParser(BaseOutputParser):
    """Wraps a parser and tries to fix parsing errors.

    Does this by passing the original prompt and the completion to another
    LLM, and telling it the completion did not satisfy criteria in the prompt.
    """

    parser: BaseOutputParser
    retry_chain: LLMChain

    @classmethod
    def from_llm(
        cls,
        llm: BaseLanguageModel,
        parser: BaseOutputParser,
        prompt: BasePromptTemplate = NAIVE_RETRY_PROMPT,
    ) -> RetryOutputParser:
        chain = LLMChain(llm=llm, prompt=prompt)
        return cls(parser=parser, retry_chain=chain)

    def parse_with_prompt(self, completion: str, prompt_value: PromptValue) -> Any:
        try:
            parsed_completion = self.parser.parse(completion)
        except OutputParserException:
            new_completion = self.retry_chain.run(
                prompt=prompt_value.to_string(), completion=completion
            )
            parsed_completion = self.parser.parse(new_completion)

        return parsed_completion

    def parse(self, completion: str) -> Any:
        raise NotImplementedError(
            "This OutputParser can only be called by the `parse_with_prompt` method."
        )

    def get_format_instructions(self) -> str:
        return self.parser.get_format_instructions()


class RetryWithErrorOutputParser(BaseOutputParser):
    """Wraps a parser and tries to fix parsing errors.

    Does this by passing the original prompt, the completion, AND the error
    that was raised to another language and telling it that the completion
    did not work, and raised the given error. Differs from RetryOutputParser
    in that this implementation provides the error that was raised back to the
    LLM, which in theory should give it more information on how to fix it.
    """

    parser: BaseOutputParser
    retry_chain: LLMChain

    @classmethod
    def from_llm(
        cls,
        llm: BaseLanguageModel,
        parser: BaseOutputParser,
        prompt: BasePromptTemplate = NAIVE_RETRY_WITH_ERROR_PROMPT,
    ) -> RetryWithErrorOutputParser:
        chain = LLMChain(llm=llm, prompt=prompt)
        return cls(parser=parser, retry_chain=chain)

    def parse_with_prompt(self, completion: str, prompt_value: PromptValue) -> Any:
        try:
            parsed_completion = self.parser.parse(completion)
        except OutputParserException as e:
            new_completion = self.retry_chain.run(
                prompt=prompt_value.to_string(), completion=completion, error=repr(e)
            )
            parsed_completion = self.parser.parse(new_completion)

        return parsed_completion

    def parse(self, completion: str) -> Any:
        raise NotImplementedError(
            "This OutputParser can only be called by the `parse_with_prompt` method."
        )

    def get_format_instructions(self) -> str:
        return self.parser.get_format_instructions()
