import sys
from typing import Any

from rich import print
from rich.progress import Progress
from sesg import graph
from sesg.metrics import Metrics, preprocess_string, similarity_score
from sesg.scopus import (
    APIKeyExpiredResponse,
    BadRequestError,
    ExceededTimeoutRetriesError,
    MultiClientScopusSearchAbstractClass,
    OutOfAPIKeysError,
    PayloadTooLargeError,
    ScopusClient,
    SuccessResponse,
    TimeoutResponse,
)
from sqlalchemy.orm import Session

from sesg_cli.database.models import SearchString, SearchStringPerformance, Study


class SearchStringPerformanceFactory:
    def __init__(
        self,
        qgs: list[Study],
        gs: list[Study],
    ) -> None:
        self.qgs = qgs
        self.processed_qgs = [preprocess_string(s.title) for s in qgs]

        self.gs = gs
        self.processed_gs = [preprocess_string(s.title) for s in gs]

        self.study_mapping: dict[int, Study] = dict()
        citation_edges: list[tuple[int, int]] = list()
        for s in gs:
            self.study_mapping[s.id] = s
            citation_edges.extend((s.id, ref.id) for ref in s.references)

        self.directed_adjacency_list = graph.edges_to_adjacency_list(
            edges=citation_edges,
        )
        self.undirected_adjacency_list = graph.edges_to_adjacency_list(
            edges=citation_edges,
            directed=False,
        )

    def __call__(
        self,
        search_string: SearchString,
        scopus_studies_list: list[SuccessResponse.Entry],
    ) -> Any:
        processed_scopus_titles = [
            preprocess_string(s.title) for s in scopus_studies_list
        ]

        qgs_in_scopus = similarity_score(
            small_set=self.processed_qgs,
            other_set=processed_scopus_titles,
        )
        qgs_in_scopus = [self.qgs[i] for i, _ in qgs_in_scopus]

        gs_in_scopus = similarity_score(
            small_set=self.processed_gs,
            other_set=processed_scopus_titles,
        )
        gs_in_scopus = [self.gs[i] for i, _ in gs_in_scopus]

        gs_in_bsb = graph.serial_breadth_first_search(
            adjacency_list=self.directed_adjacency_list,
            starting_nodes=[s.id for s in gs_in_scopus],
        )
        gs_in_bsb = [self.study_mapping[s_id] for s_id in gs_in_bsb]

        gs_in_sb = graph.serial_breadth_first_search(
            adjacency_list=self.undirected_adjacency_list,
            starting_nodes=[s.id for s in gs_in_scopus],
        )
        gs_in_sb = [self.study_mapping[s_id] for s_id in gs_in_sb]

        metrics = Metrics(
            gs_size=len(self.gs),
            n_scopus_results=len(scopus_studies_list),
            n_qgs_studies_in_scopus=len(qgs_in_scopus),
            n_gs_studies_in_scopus=len(gs_in_scopus),
            n_gs_studies_in_scopus_and_bsb=len(gs_in_bsb),
            n_gs_studies_in_scopus_and_bsb_and_fsb=len(gs_in_sb),
        )

        return SearchStringPerformance(
            n_qgs_in_scopus=len(qgs_in_scopus),
            n_gs_in_scopus=len(gs_in_scopus),
            n_gs_in_bsb=len(gs_in_bsb),
            n_gs_in_sb=len(gs_in_sb),
            qgs_in_scopus=qgs_in_scopus,
            gs_in_scopus=gs_in_scopus,
            gs_in_bsb=gs_in_bsb,
            gs_in_sb=gs_in_sb,
            n_scopus_results=metrics.n_scopus_results,
            scopus_precision=metrics.scopus_precision,
            scopus_recall=metrics.scopus_recall,
            scopus_f1_score=metrics.scopus_f1_score,
            bsb_recall=metrics.scopus_and_bsb_recall,
            sb_recall=metrics.scopus_and_bsb_and_fsb_recall,
            search_string_id=search_string.id,
        )


class MultiClientScopusSearch(MultiClientScopusSearchAbstractClass):
    def __init__(
        self,
        clients_list: list[ScopusClient],
        progress: Progress,
        session: Session,
        db_search_strings_list: list[SearchString],
        search_string_performance_factory: SearchStringPerformanceFactory,
    ) -> None:
        search_strings_list = [s.string for s in db_search_strings_list]
        super().__init__(clients_list, search_strings_list)

        self.search_string_performance_factory = search_string_performance_factory
        self.db_search_strings_list = db_search_strings_list
        self.session = session
        self.progress = progress
        self.overall_progress_task = progress.add_task(
            "Overall progress",
            total=len(self.search_strings_list),
        )
        self.clients_progress_tasks = [
            progress.add_task(
                description=f"Client {i + 1}",
            )
            for i in range(len(self.clients_list))
        ]

    def on_search_initialize(
        self,
        client_index: int,
        search_string_index: int,
    ):
        description = (
            f"Client {client_index + 1} "
            f"(String {search_string_index + 1} of {len(self.search_strings_list)})"  # noqa: E501
        )

        self.progress.update(
            self.clients_progress_tasks[client_index],
            description=description,
        )
        self.progress.advance(self.clients_progress_tasks[client_index])

    def on_first_success_response(
        self,
        client_index: int,
        data: SuccessResponse,
    ):
        self.progress.update(
            self.clients_progress_tasks[client_index],
            total=data.number_of_pages,
            refresh=True,
        )

    def on_api_key_expired_response(
        self,
        client_index: int,
        data: APIKeyExpiredResponse,
    ):
        print(f"API Key {data.api_key} expired.")

    def on_timeout_response(
        self,
        client_index: int,
        search_string_index: int,
        attempts_left: int,
        data: TimeoutResponse,
    ):
        description = (
            f"Client {client_index + 1} timed out ({attempts_left} attempts left)"
        )

        self.progress.update(
            self.clients_progress_tasks[client_index],
            description=description,
        )

    def on_bad_request_error(
        self,
        client_index: int,
        search_string: str,
        error: BadRequestError,
    ):
        print("The following string raised a BadRequestError")
        print(search_string)

    def on_payload_too_large_error(
        self,
        client_index: int,
        search_string: str,
        error: PayloadTooLargeError,
    ):
        print("The following string raised a BadRequestError")
        print(search_string)

    def on_exceeded_timeout_retries_error(
        self,
        client_index: int,
        error: ExceededTimeoutRetriesError,
    ):
        print("Exceeded the maximum number of timeout retries in a row.")
        sys.exit()

    def on_out_of_api_keys_error(
        self,
        client_index: int,
        error: OutOfAPIKeysError,
    ):
        print("Ran out of API keys.")
        sys.exit()

    def on_search_complete(
        self,
        client_index: int,
        search_string_index: int,
        results: list[SuccessResponse.Entry],
    ):
        search_string = self.db_search_strings_list[search_string_index]
        performance = self.search_string_performance_factory(
            search_string=search_string,
            scopus_studies_list=results,
        )
        self.session.add(performance)
        self.session.commit()

        self.progress.reset(self.clients_progress_tasks[client_index])
        self.progress.advance(self.overall_progress_task)

    def on_all_complete(self):
        for t in self.clients_progress_tasks:
            self.progress.remove_task(t)

        self.progress.remove_task(self.overall_progress_task)

    def on_all_start(self):
        ...

    def on_success_response(
        self,
        client_index: int,
        data: SuccessResponse,
    ):
        self.progress.advance(self.clients_progress_tasks[client_index])
