from google.cloud import aiplatform

class VectorSearchSession:
    def __init__(self,
                 gcp_project_id,
                 gcp_project_number,
                 index_endpoint_id,
                 deployed_index_id,
                 credentials,
                 gcp_region="europe-west3",
                 api_endpoint="1734329425.europe-west3-412810111069.vdb.vertexai.goog",
                 ):
        
        self.gcp_project_id = gcp_project_id # the gcp project that hosts the matching engine instance
        self.gcp_project_number = gcp_project_number # the gcp project number that hosts the matching engine instance
        self.credentials = credentials # gcp credentials to access the matching engine instance
        self.gcp_region = gcp_region # vector search index region
        self.index_endpoint_id = index_endpoint_id # vector search index index endpoint if (numeric)
        self.deployed_index_id = deployed_index_id # vector search index deployed index id (aphanumeric)
        self.api_endpoint = api_endpoint # gcp me api endpoint, depending on region

    def find_matches(self, query_vec: list, num_neighbors: int = 10, match_thresh: float = .6) -> list:
        """
        Finding nearest neighbours based on input vector (embedded client query).

        Parameters
        ----------
        query_vec : list
            query vector
        num_neighbors : int
            number of nearest neighbours to return
        match_thresh : float
            threshold for matching

        Returns
        -------
        matched_ids : list
            list of matched ids
        """
        print (self.gcp_project_number)
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=f"projects/{self.gcp_project_number}/locations/europe-west3/indexEndpoints/{self.index_endpoint_id}",
                                                                project=self.gcp_project_id,
                                                                location=self.gcp_region,
                                                                credentials=self.credentials
                                                                )
        res = index_endpoint.find_neighbors(deployed_index_id=self.deployed_index_id, queries=[query_vec], num_neighbors=num_neighbors)

        matched_ids = [match.id for match in res[0] if match.distance >= match_thresh]

        return matched_ids

    def stream_upsert(self, id, embedding):
        # streaming upsert of input embedding
        pass
    
