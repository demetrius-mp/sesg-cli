from itertools import product
from pathlib import Path
from random import sample
from time import time
from typing import Any

import typer
from rich import print
from rich.progress import Progress

from sesg_cli.config import Config
from sesg_cli.database.connection import Session
from sesg_cli.database.models import (
    SLR,
    Experiment,
    Params,
    SearchString,
)
from sesg_cli.strategies import (
    SimilarWordGeneratorStrategy,
    TopicExtractionStrategy,
)
from sesg_cli.telegram_report import TelegramReport


app = typer.Typer(rich_markup_mode="markdown",
                  help="Start an experiment for a SLR. With multiple similar words generation strategies.")


@app.command()
def start(  # noqa: C901 - method too complex
        slr_name: str = typer.Argument(
            ...,
            help="Name of the Systematic Literature Review",
        ),
        experiment_name: str = typer.Argument(
            ...,
            help="Name of the new experiment.",
        ),
        config_toml_path: Path = typer.Option(
            Path.cwd() / "config.toml",
            "--config-toml-path",
            "-c",
            help="Path to a `config.toml` file.",
            dir_okay=False,
            file_okay=True,
            exists=True,
        ),
        topic_extraction_strategies_list: list[TopicExtractionStrategy] = typer.Option(
            [TopicExtractionStrategy.bertopic, TopicExtractionStrategy.lda],
            "--topic-strategy",
            "-ste",
            help="Which topic extraction strategies to use.",
        ),
        similar_word_strategies_list: list[SimilarWordGeneratorStrategy] = typer.Option(
            [SimilarWordGeneratorStrategy.bert, SimilarWordGeneratorStrategy.llm],
            "--similar-word-strategy",
            "-sws",
            help="Which similar word generation strategies to use.",
        ),
):
    """Starts an experiment and generates search strings.

    Will only generate strings using unseen parameters from the config file. If a string was already
    generated for this experiment using a set of parameters for the strategy, will skip it.
    """  # noqa: E501

    start_time = time()
    from sesg.search_string import generate_search_string, set_pub_year_boundaries
    from sesg.similar_words.bert_strategy import BertSimilarWordsGenerator
    from sesg.topic_extraction import (
        extract_topics_with_bertopic,
        extract_topics_with_lda,
    )
    from transformers import BertForMaskedLM, BertTokenizer, logging  # type: ignore

    from sesg_cli.similar_words_generator_cache import SimilarWordsGeneratorCache
    from sesg_cli.strategies_implementations.llm_similar_words_generator import (
        LlmSimilarWordsGenerator,
    )

    logging.set_verbosity_error()

    config = Config.from_toml(config_toml_path)

    telegram_report = TelegramReport(
        slr_name=slr_name,
        experiment_name=experiment_name,
        strategies=list(product([s.value for s in topic_extraction_strategies_list],
                                [s.value for s in similar_word_strategies_list])),
    )

    with Session() as session:
        slr = SLR.get_by_name(slr_name, session)
        print(f"Found GS with size {len(slr.gs)}.")

        experiment = Experiment.get_or_create_by_name(
            name=experiment_name,
            slr_id=slr.id,
            session=session,
        )

        if experiment.id is None:
            qgs_size = len(slr.gs) // 3
            experiment.qgs = sample(slr.gs, k=qgs_size)

            session.add(experiment)
            session.commit()
            session.refresh(experiment)

        print(
            f"Creating QGS with size {len(experiment.qgs)} containing the following studies:"  # noqa: E501
        )
        for study in experiment.qgs:
            print(f'Study(id={study.id}, title="{study.title}")')

        print()

        docs = experiment.get_docs()
        enrichment_text = experiment.get_enrichment_text()

        if len(docs) < 10:
            print("[blue]Less than 10 documents. Duplicating the current documents.")
            print()
            docs = [*docs, *docs]

        print("Loading tokenizer and language model...")
        print()

        telegram_report.send_new_execution_report()

        with Progress() as progress:
            for strategies_set in product(similar_word_strategies_list, topic_extraction_strategies_list):
                similar_word_strategy = strategies_set[0]
                topic_extraction_strategy = strategies_set[1]

                config_params_list = Params.create_with_strategy(
                    config=config,
                    experiment_id=experiment.id,
                    session=session,
                    similar_word_strategy=similar_word_strategy,
                    topic_extraction_strategy=topic_extraction_strategy,
                )

                n_params = len(config_params_list)
                task_id = progress.add_task(
                    f"Found [bright_cyan]{n_params}[/bright_cyan] parameters variations for {topic_extraction_strategy} with {similar_word_strategy}...",
                    # noqa: E501
                    total=n_params,
                )

                if similar_word_strategy == SimilarWordGeneratorStrategy.bert:
                    bert_tokenizer: Any = BertTokenizer.from_pretrained(
                        "bert-base-uncased")
                    bert_model: Any = BertForMaskedLM.from_pretrained(
                        "bert-base-uncased")

                    bert_model.eval()

                    similar_word_generator = BertSimilarWordsGenerator(
                        enrichment_text=enrichment_text,
                        bert_model=bert_model,
                        bert_tokenizer=bert_tokenizer,
                    )

                elif similar_word_strategy == SimilarWordGeneratorStrategy.llm:
                    similar_word_generator = LlmSimilarWordsGenerator(
                        enrichment_text=enrichment_text)

                else:
                    raise RuntimeError(
                        "Invalid Similar Word Generation Strategy. Must be either ['bert','llm']."
                        # noqa: E501
                    )

                similar_words_generator = SimilarWordsGeneratorCache(
                    similar_word_generator=similar_word_generator,
                    experiment_id=experiment.id,
                    session=session,
                    generator=similar_word_strategy,
                )

                for i, params in enumerate(config_params_list):
                    progress.update(
                        task_id,
                        advance=1,
                        description=f"{topic_extraction_strategy} - {similar_word_strategy}: Using parameter variation [bright_cyan]{i + 1}[/] of [bright_cyan]{n_params}[/]",
                        # noqa: E501
                        refresh=True,
                    )

                    existing_params = Params.get_one_or_none(
                        experiment_id=params.experiment_id,
                        formulation_params_id=params.formulation_params_id,
                        generator=params.similar_word_strategy,
                        bertopic_params_id=params.bertopic_params_id,
                        lda_params_id=params.lda_params_id,
                        session=session,
                    )

                    if i+1 in (n_params*0.25, n_params*0.50, n_params*0.75):
                        telegram_report.send_progress_report(strategy=f"{topic_extraction_strategy.value} - {similar_word_strategy.value}",
                                                             percentage=int(
                                                                 ((i+1)/n_params)*100),
                                                             exec_time=time()-start_time)

                    if existing_params is not None:
                        progress.update(
                            task_id,
                            description=f"{topic_extraction_strategy} - {similar_word_strategy}: Skipped parameter variation [bright_cyan]{i + 1}[/] of [bright_cyan]{n_params}[/]",
                            # noqa: E501
                            refresh=True,
                        )
                        continue

                    if (
                            topic_extraction_strategy == TopicExtractionStrategy.bertopic
                            and params.bertopic_params is not None
                    ):
                        topics_list = extract_topics_with_bertopic(
                            docs,
                            kmeans_n_clusters=params.bertopic_params.kmeans_n_clusters,
                            umap_n_neighbors=params.bertopic_params.umap_n_neighbors,
                        )

                    elif (
                            topic_extraction_strategy == TopicExtractionStrategy.lda
                            and params.lda_params is not None
                    ):
                        topics_list = extract_topics_with_lda(
                            docs,
                            min_document_frequency=params.lda_params.min_document_frequency,
                            n_topics=params.lda_params.n_topics,
                        )

                    else:
                        raise RuntimeError(
                            "Invalid Topic Extraction Strategy or the params instance does not have neither a lda_params or bertopic_params"
                            # noqa: E501
                        )

                    formulation_params = params.formulation_params

                    string = generate_search_string(
                        topics=topics_list,
                        n_similar_words_per_word=formulation_params.n_similar_words_per_word,
                        n_words_per_topic=formulation_params.n_words_per_topic,
                        similar_words_generator=similar_words_generator,
                    )

                    string = f"TITLE-ABS-KEY({string})"
                    string = set_pub_year_boundaries(
                        string=string,
                        max_year=slr.max_publication_year,
                        min_year=slr.min_publication_year,
                    )

                    db_search_string = SearchString.get_or_create_by_string(
                        string,
                        session,
                    )

                    db_search_string.params_list.append(params)

                    session.add(db_search_string)
                    session.commit()

                progress.remove_task(task_id)

    telegram_report.send_finish_report(exec_time=time()-start_time)
