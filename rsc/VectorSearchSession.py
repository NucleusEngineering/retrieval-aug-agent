# Copyright 2024 Google

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from dotenv import dotenv_values
import time

from google.cloud import aiplatform
import google.auth

from google.cloud import bigquery

from langchain.vectorstores.utils import DistanceStrategy
from langchain_community.vectorstores import BigQueryVectorSearch
from langchain_google_vertexai import VertexAIEmbeddings

try:
    from rsc.EmbeddingSession import EmbeddingSession
except:
    from EmbeddingSession import EmbeddingSession


class VectorSearchSession:

    def __init__(self,
                 gcp_project_id,
                 gcp_project_number,
                 index_endpoint_id,
                 deployed_index_id,
                 credentials,
                 gcp_region,
                 api_endpoint,
                 ):
        
        self.secrets = dotenv_values(".env")
        self.gcp_project_id = gcp_project_id # the gcp project that hosts the matching engine instance
        self.gcp_project_number = gcp_project_number # the gcp project number that hosts the matching engine instance
        self.gcp_region = gcp_region # the gcp region in which the instance is deployed
        self.credentials = credentials # gcp credentials to access the matching engine instance
        self.gcp_region = gcp_region # vector search index region
        self.index_endpoint_id = index_endpoint_id # vector search index index endpoint if (numeric)
        self.deployed_index_id = deployed_index_id # vector search index deployed index id (aphanumeric)
        self.api_endpoint = api_endpoint # gcp me api endpoint, depending on region

    def find_matches(
        self, query_vec: list, num_neighbors: int = 10, match_thresh: float = 0.6
    ) -> list:
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
        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=f"projects/{self.gcp_project_number}/locations/{self.gcp_region}/indexEndpoints/{self.index_endpoint_id}",
                                                                project=self.gcp_project_id,
                                                                location=self.gcp_region,
                                                                credentials=self.credentials
                                                                )
        
        start_time = time.time()
        res = index_endpoint.find_neighbors(deployed_index_id=self.deployed_index_id, queries=[query_vec], num_neighbors=num_neighbors)
        end_time = time.time()
        duration_seconds = end_time - start_time

        matched_ids = [match.id for match in res[0] if match.distance >= match_thresh]
        
        print("#### Vertex Vector Search ####")
        print(f"Matched ids: {matched_ids}")
        print(f"Vector Search VS Seconds: {duration_seconds}")

        return matched_ids
    
    def bq_find_matches(self, string_query:str, query_vec: list, num_neighbors: int = 10, match_thresh: float = 0.6):
        
        embedding_model = VertexAIEmbeddings(
            model_name="textembedding-gecko@001",
            project=self.secrets['GCP_PROJECT_ID'],
            credentials=self.credentials
        )

        store = BigQueryVectorSearch(
            embedding=embedding_model,
            credentials=self.credentials,
            project_id=self.secrets['GCP_PROJECT_ID'],
            dataset_name=self.secrets['BIGQUERY_DATASET'],
            table_name=self.secrets['BIGQUERY_TABLE'],
            location=self.secrets['GCP_REGION'],
            distance_strategy=DistanceStrategy.EUCLIDEAN_DISTANCE,
        )

        bq_query_str = f"""SELECT
        *
        FROM
        VECTOR_SEARCH( TABLE {self.secrets['BIGQUERY_DATASET']}.{self.secrets['BIGQUERY_TABLE']},
            'embedding',
            (
            SELECT
            ml_generate_embedding_result
            FROM
            ML.GENERATE_EMBEDDING( MODEL `{self.secrets['GCP_PROJECT_ID']}.retrieval_augmented_agent.emb-model`,
                (
                SELECT
                "{string_query}" AS content),
                STRUCT(TRUE AS flatten_json_output) )),
        top_k => {num_neighbors},
        distance_type => 'COSINE',""" + """OPTIONS => '{"use_brute_force":true}');"""

        client = bigquery.Client(project=self.secrets['GCP_PROJECT_ID'], credentials=self.credentials, location=self.secrets["GCP_REGION"])

        start_time = time.time()
        rows = client.query_and_wait(query=bq_query_str)
        end_time = time.time()
        duration_seconds = end_time - start_time

        matched_ids = [row[1]["id"] for row in rows]
        print("#### BQ Vector Search ####")
        print(f"Matched ids: {matched_ids}")
        print(f"BigQuery VS Seconds: {duration_seconds}")

        return matched_ids




if __name__ == "__main__":

    secrets = dotenv_values(".env")
    credentials, _ = google.auth.load_credentials_from_file(
    secrets["GCP_CREDENTIAL_FILE"])

    vecs = vector_search_session = VectorSearchSession(
            gcp_project_id=secrets["GCP_PROJECT_ID"],
            gcp_project_number=secrets["GCP_PROJECT_NUMBER"],
            credentials=credentials,
            index_endpoint_id=secrets["VECTOR_SEARCH_INDEX_ENDPOINT_ID"],
            deployed_index_id=secrets["VECTOR_SEARCH_DEPLOYED_INDEX_ID"],
            gcp_region = secrets["GCP_REGION"],
            api_endpoint = secrets["GCP_MATCHING_ENGINE_ENDPOINT"]
        )
    
    client_query = "What are some typical cringe moments in tracking engineering?"

    embedding_session = EmbeddingSession()
    
    embedded_query = embedding_session.get_vertex_embedding(
            text_to_embed=client_query
        )
    
    num_neig = 5

    bq_matches = vecs.bq_find_matches(string_query=client_query, query_vec=embedded_query, num_neighbors=num_neig)
    vertex_matches = vecs.find_matches(query_vec=embedded_query, num_neighbors=num_neig)

    print(f"Exact Same Results: {bq_matches==vertex_matches}")
        
    print("Hello World!")
