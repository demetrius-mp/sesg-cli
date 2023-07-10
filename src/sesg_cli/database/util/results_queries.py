from itertools import product


class AlgorithmBaseQueryNotImplemented(Exception):
    """There is no base query for the algorithm provided."""


class ResultQuery:
    def __init__(
            self,
            slr: str,
            bonus_metrics: list[str] | None = None,
            bonus_algorithms: list[str] | None = None,
            row_num: int = 1,
    ):
        self.check_review: str = f"""select
                                case 
                                    when count(*)>0 then true
                                    else false
                                end	
                            from experiment e 
                            join slr s on s.id = e.slr_id 
                            where s."name" = '{slr}'"""

        self._qgs_query: str = f"""select e."name", s.id, s.title 
                                    from study s 
                                    join experiment_qgs eq on eq.study_id = s.id
                                    join experiment e on e.id = eq.experiment_id 
                                    join slr on slr.id = e.slr_id 
                                    where slr."name" = '{slr}'"""

        self._results_queries: dict[str, str] = {
            'lda': f"""select distinct on (ssp.search_string_id) ssp.search_string_id,
                    ssp.start_set_precision,
                    ssp.start_set_recall,
                    ssp.start_set_f1_score,
                    ssp.bsb_recall,
                    ssp.sb_recall,
                    lp.min_document_frequency as min_df,
                    lp.n_topics as n_topics,
                    fp.n_similar_words_per_word as n_similar_w,
                    fp.n_words_per_topic as n_w_per_topic,
                    ssp.n_scopus_results as n_scopus_results,
                    ssp.n_qgs_in_scopus as n_qgs_studies_in_scopus,
                    ssp.n_gs_in_scopus as n_gs_studies_in_scopus,
                    e."name"
                    from params
                    join lda_params lp ON lp.id = params.lda_params_id
                    join formulation_params fp ON fp.id = params.formulation_params_id
                    join search_string ON search_string.id = params.search_string_id
                    left join search_string_performance ssp ON ssp.search_string_id = search_string.id
                    join experiment e ON e.id = params.experiment_id
                    join slr s on s.id = e.slr_id
                    where s."name" = '{slr}'""",
            'bt': f"""select distinct on (ssp.search_string_id) ssp.search_string_id,
                    ssp.start_set_precision,
                    ssp.start_set_recall,
                    ssp.start_set_f1_score,
                    ssp.bsb_recall,
                    ssp.sb_recall,
                    bp.kmeans_n_clusters as n_clusters,
                    bp.umap_n_neighbors as n_neighbors,
                    fp.n_similar_words_per_word as n_similar_w,
                    fp.n_words_per_topic as n_w_per_topic,
                    ssp.n_scopus_results as n_scopus_results,
                    ssp.n_qgs_in_scopus as n_qgs_studies_in_scopus,
                    ssp.n_gs_in_scopus as n_gs_studies_in_scopus,
                    e."name"
                    from params
                    join bertopic_params bp ON bp.id = params.bertopic_params_id 
                    join formulation_params fp ON fp.id = params.formulation_params_id
                    join search_string ON search_string.id = params.search_string_id
                    left join search_string_performance ssp ON ssp.search_string_id = search_string.id
                    join experiment e ON e.id = params.experiment_id
                    join slr s on s.id = e.slr_id
                    where s."name" = '{slr}'"""
        }
        self._results_queries_by_row: dict[str, str] = {
            'lda': f"""select 
                            ssp.search_string_id as search_string_id,
                            ssp.start_set_precision,
                            ssp.start_set_recall,
                            ssp.start_set_f1_score,
                            ssp.bsb_recall,
                            ssp.sb_recall,
                            lp.min_document_frequency as min_df,
                            lp.n_topics as n_topics,
                            fp.n_similar_words_per_word as n_similar_w,
                            fp.n_words_per_topic as n_w_per_topic,
                            ssp.n_scopus_results as n_scopus_results,
                            ssp.n_qgs_in_scopus as n_qgs_studies_in_scopus,
                            ssp.n_gs_in_scopus as n_gs_studies_in_scopus,
                            e."name",
                            ROW_NUMBER() over (partition by e."name" order by ssp.{'placeholder'} desc) as row_num
                        from params
                            join lda_params lp ON lp.id = params.lda_params_id
                            join formulation_params fp ON fp.id = params.formulation_params_id
                            join search_string ON search_string.id = params.search_string_id
                            left join search_string_performance ssp ON ssp.search_string_id = search_string.id
                            join experiment e ON e.id = params.experiment_id
                            join slr s on s.id = e.slr_id
                        where 
                            s."name" = '{slr}'""",
            'bt': f"""select
                            ssp.search_string_id as search_string_id,
                            ssp.start_set_precision,
                            ssp.start_set_recall,
                            ssp.start_set_f1_score,
                            ssp.bsb_recall,
                            ssp.sb_recall,
                            bp.kmeans_n_clusters as n_clusters,
                            bp.umap_n_neighbors as n_neighbors,
                            fp.n_similar_words_per_word as n_similar_w,
                            fp.n_words_per_topic as n_w_per_topic,
                            ssp.n_scopus_results as n_scopus_results,
                            ssp.n_qgs_in_scopus as n_qgs_studies_in_scopus,
                            ssp.n_gs_in_scopus as n_gs_studies_in_scopus,
                            e."name",
                            ROW_NUMBER() over (partition by e."name" order by ssp.{'placeholder'} desc) as row_num
                        from params
                            join bertopic_params bp ON bp.id = params.bertopic_params_id 
                            join formulation_params fp ON fp.id = params.formulation_params_id
                            join search_string ON search_string.id = params.search_string_id
                            left join search_string_performance ssp ON ssp.search_string_id = search_string.id
                            join experiment e ON e.id = params.experiment_id
                            join slr s on s.id = e.slr_id
                        where 
                            s."name" = '{slr}'""",
        }

        self._slr: str = slr
        self._row_num: int = row_num

        self._set_metrics(bonus_metrics)
        self._set_algorithms(bonus_algorithms)

    def _set_metrics(self, bonus_metrics: list[str] | None):
        self._metrics: list[str] = ['start_set_precision', 'start_set_recall']

        if bonus_metrics:
            self._metrics.extend(bonus_metrics)

    def _set_algorithms(self, bonus_algorithms: list[str] | None):
        self._algorithms: list[str] = ['lda', 'bt']

        if bonus_algorithms:
            self._algorithms.extend(bonus_algorithms)

    def _generate_top_ten_query(self, algorithm: str, metric: str) -> str:
        """
        Generates queries for the top 10 best strings according to the algorithm base query
        and the metric to order the results.

        Args:
            algorithm: `lda` or `bt` (bertopic).
            metric: metrics avaible to order the results.

        Returns: the query added of the algorithm base query as subquery, the order by and limit statements.

        """
        algorithm_query = self._results_queries.get(algorithm, None)

        if not algorithm_query:
            raise AlgorithmBaseQueryNotImplemented()

        return f"select * from ({algorithm_query}) results " \
               f"order by {metric} desc limit 10"

    def _generate_query_by_row(self, algorithm: str, metric: str) -> str:
        """
        Generates queries to get the best X results from each experiment according to the algorithm base query
        and the metric to order the results..

        Args:
            algorithm: `lda` or `bt` (bertopic).
            metric: metrics avaible to order the results.

        Returns: the query added of the algorithm base query as subquery and the order by statement.

        """
        algorithm_query = self._results_queries_by_row.get(algorithm, None)

        if not algorithm_query:
            raise AlgorithmBaseQueryNotImplemented()

        algorithm_query = algorithm_query.replace('placeholder', metric)

        return f"""select * from ({algorithm_query}) results
                    where row_num <= {self._row_num} 
                    order by "name" asc"""

    def get_queries(self) -> dict[str, str]:
        """
        Generates a dictionary with all the queries needed to compose the Excel file for analysis.

        Returns: A dict with the queries needed, they are:
            - {algorithm}: all the {algorithm} results;
            - qgs: all the experiments' QGSs;
            - top_ten_{algorithm}_{metric}: top ten {algorithm} results ordered by the {metric};

        """
        for metric, algorithm in product(self._metrics, self._algorithms):
            self._results_queries[f'top_ten_{algorithm}_{metric}'] = self._generate_top_ten_query(algorithm,
                                                                                                  metric)
        self._results_queries['qgs'] = self._qgs_query

        return self._results_queries

    def get_queries_by_row(self) -> dict[str, str]:
        """
        Generates a dictionary with all the queries needed to compose the Excel file for analysis,
        by getting the best X results from each experiment.

        Returns: A dict with the queries needed, they are:
            - {algorithm}: all the {algorithm} results;
            - qgs: all the experiments' QGSs;
            - top_{row_num}_{algorithm}_{metric}: top {row_num} results of each exp of each {algorithm}
            ordered by the {metric};
        """
        for metric, algorithm in product(self._metrics, self._algorithms):
            self._results_queries[
                f'top_{self._row_num}_{algorithm}_{metric}'
            ] = self._generate_query_by_row(algorithm, metric)

        self._results_queries['qgs'] = self._qgs_query

        return self._results_queries


