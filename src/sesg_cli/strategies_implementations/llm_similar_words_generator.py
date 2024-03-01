"""Generates similar words using LLMs."""
from dataclasses import dataclass

from langchain_community.llms import Ollama
from langchain_core.output_parsers.json import SimpleJsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sesg.similar_words.protocol import SimilarWordsGenerator


class Prompts:
    """
        Creates a wrapper for possibles prompts to pass to the llm model. 
        In this implementation is possible to define the amount of synonyms 
        to be generated. By default, it is 5.
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
    """Class to define a LlmSimilarWordGenerator."""

    def __init__(self,  # noqa: D107
                 enrichment_text: str,
                 model: str = "mistral",
                 prompt: ChatPromptTemplate = Prompts().prompt):
        self.model = model
        self.prompt = prompt

        self.llm: ChatOpenAI | Ollama

        self.enrichment_text: str = enrichment_text
        self.init_model()

    def init_model(self) -> None:
        """Defines a chain with the prompt, the model and the parser."""

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

    @staticmethod
    def _get_similar_words(response: dict, word: str) -> list[str]:
        """Get the similar words generate by the model.

        Args:
            response (dict): Response returned by the model.
            word (str): Word to be enriched.
        Raises:
            RuntimeError: If the model does not return a well structured response.
        Returns:
            similar_words (list[str]): List of similar words.
        """
        similar_words = response.get("synonyms", None)

        if similar_words is None:
            similar_words = next(
                (response[i]
                 for i in response if isinstance(response[i], list)),
                None
            )

        if similar_words is None:
            raise RuntimeError(
                f"No similar words returned or the response is not well structured. Response: {response}")

        similar_words = similar_words if word not in similar_words else similar_words.remove(
            word)

        return similar_words

    def __call__(self, word: str, retries: int = 3) -> list[str]:
        """Generates similar words using LLMs.

        Args:
            word (str): The word to be enriched.

        Returns:
            A list of similar words.
        """
        selected_sentences: list[str] = []

        for sentence in self.enrichment_text.split("."):
            if word in sentence or word in sentence.lower():
                selected_sentences.append(sentence + ".")
                break

        context = " ".join(selected_sentences)

        retries = retries
        while retries > 0:
            retries -= 1
            try:
                response = self.chain.invoke({
                    "context": context,
                    "number_similar_words": 5,
                    "word_to_be_enriched": word
                })

                similar_words = self._get_similar_words(response, word)
            except Exception as e:
                if retries == 0:
                    raise RuntimeError(
                        f"Model could not generate a JSON response. Parser error: {e}")
                continue

        return similar_words
