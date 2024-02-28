"""Generates similar words using LLMs."""
import time
from dataclasses import dataclass

from langchain_community.llms import Ollama
from langchain_core.output_parsers.json import SimpleJsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from sesg.similar_words.protocol import SimilarWordsGenerator


class Prompts():
    """_summary_.

    Returns:
        _description_.
    """
    base_prompt = {
        "system": "You are a helpful synonym generator. Answer with a JSON object and nothing more. Follow this example 'synonyms': ['house', 'home']",
        "human": "Given the following context: {context}. Generate this amount of synonyms: {number_similar_words} for this topic: {word_to_be_enriched}."
    }

    def __init__(self, prompt_text: dict = base_prompt) -> None:  # noqa: D107
        self.prompt_text: dict = prompt_text
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.prompt_text["system"]),
                ("human", self.prompt_text["human"])
            ]
        )


@dataclass
class LlmSimilarWordsGenerator(SimilarWordsGenerator):
    """_summary_.

    Args:
        SimilarWordsGenerator (_type_): _description_.


    Returns:
        _description_.
    """

    def __init__(self, # noqa: D107
                 enrichment_text: str,
                 model: str = "mistral",
                 prompt: ChatPromptTemplate = Prompts().prompt):
        self.model = model
        self.prompt = prompt

        self.llm: ChatOpenAI | Ollama

        self.enrichment_text: str = enrichment_text
        self.init_model()

    def init_model(self) -> None:
        """_summary_."""
        json_parser = SimpleJsonOutputParser()

        self.llm = ChatOpenAI(
            model=self.model) if "gpt" in self.model else Ollama(model=self.model)

        """
        TODO: If we use a model that cannot return json parsed answers. 
        Use this:

        ```
        str_parser = StrOutputParser()

        if "llama" in self.model:
            self.chain = self.prompt | self.llm | str_parser
        else:
        ```

        This will lead to the need of a parser method to structure
        the answer. 

        """

        self.chain = self.prompt | self.llm | json_parser

    def __call__(self, word: str) -> list[str]:
        """_summary_.

        Args:
            word (str): _description_.


        Returns:
            _description_.
        """
        if " " in word:
            return []

        selected_sentences: list[str] = []

        for sentence in self.enrichment_text.split("."):
            if word in sentence or word in sentence.lower():
                selected_sentences.append(sentence + ".")
                break

        context = " ".join(selected_sentences)

        start = time.time()
        response = self.chain.invoke({
            "context": context,
            "number_similar_words": 5,
            "word_to_be_enriched": word
        })
        print(f'{response= }')
        print(f'Exec time: {time.time() - start}')
        # todo: add verificador das chaves/valores do retorno
        # todo: remover sinonimos que sejam igual a palavra do topico .remove()
        similar_words = response.get("synonyms", None)
        print("similar words: ",similar_words)

        if similar_words is None:
            raise RuntimeError(f"No similar words returned or the response is not well structured. Response: {response}")

        return similar_words
