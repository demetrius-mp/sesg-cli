class ResultQuery:
    def __init__(self, slr: str):
        self.results_queries = {
            'lda': f"""select distinct on (ssp.search_string_id) ssp.search_string_id,
                    ssp.start_set_precision as st_precision,
                    ssp.start_set_recall as st_recall,
                    ssp.start_set_f1_score as st_f1_score,
                    ssp.bsb_recall as bsb_recall,
                    ssp.sb_recall as final_recall,
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
                    ssp.start_set_precision as st_precision,
                    ssp.start_set_recall as st_recall,
                    ssp.start_set_f1_score as st_f1_score,
                    ssp.bsb_recall as bsb_recall,
                    ssp.sb_recall as final_recall,
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
                    where s."name" = '{slr}'""",
            'qgs': f"""select e."name", s.id, s.title 
                    from study s 
                    join experiment_qgs eq on eq.study_id = s.id
                    join experiment e on e.id = eq.experiment_id 
                    join slr on slr.id = e.slr_id 
                    where slr."name" = '{slr}'"""
        }
        self.slr = slr

    def _generate_top_ten_query(self, algorithm: str, metric: str) -> str:
        """
        Generates queries for the top 10 best strings according to the algorithm base query
        and the metric to order the results.

        Args:
            algorithm: `lda` or `bt` (bertopic).
            metric: `st_precision` or `st_recall`

        Returns: the query added of the algorithm base query as subquery, the order by and limit statements.

        """
        return f"select * from ({self.results_queries.get(algorithm)}) results " \
               f"order by {metric} desc limit 10"

    def get_queries(self) -> dict:
        """
        Generates a dictionary with all the queries needed to compose the excel file for analysis

        Returns: a dict with the queries needed, they are:
            - lda: all the LDA resutls;
            - bt: all the Bertopic results;
            - qgs: all the experiments' QGSs;
            - top_ten_lda_st_precision: top 10 LDA results order by the start_set_precision;
            - top_ten_lda_st_recall: top 10 LDA results order by the start_set_recall;
            - top_ten_bt_st_precision: top 10 BERTopic results order by the start_set_precision;
            - top_ten_bt_st_recall: top 10 BERTopic results order by the start_set_recall;

        """
        self.results_queries['top_ten_lda_st_precision'] = self._generate_top_ten_query('lda', 'st_precision')
        self.results_queries['top_ten_lda_st_recall'] = self._generate_top_ten_query('lda', 'st_recall')
        self.results_queries['top_ten_bt_st_precision'] = self._generate_top_ten_query('bt', 'st_precision')
        self.results_queries['top_ten_bt_st_recall'] = self._generate_top_ten_query('bt', 'st_recall')

        return self.results_queries
