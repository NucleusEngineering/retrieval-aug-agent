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

from google.cloud import aiplatform


class VectorSearchSession:
    def __init__(
        self,
        gcp_project_id,
        gcp_project_number,
        index_endpoint_id,
        deployed_index_id,
        credentials,
        gcp_region="europe-west1",
        api_endpoint="1665184178.europe-west1-886845446187.vdb.vertexai.goog",
    ):
        self.gcp_project_id = (
            gcp_project_id  # the gcp project that hosts the matching engine instance
        )
        self.gcp_project_number = gcp_project_number  # the gcp project number that hosts the matching engine instance
        self.credentials = (
            credentials  # gcp credentials to access the matching engine instance
        )
        self.gcp_region = gcp_region  # vector search index region
        self.index_endpoint_id = (
            index_endpoint_id  # vector search index index endpoint if (numeric)
        )
        self.deployed_index_id = (
            deployed_index_id  # vector search index deployed index id (aphanumeric)
        )
        self.api_endpoint = api_endpoint  # gcp me api endpoint, depending on region

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

        index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=f"projects/{self.gcp_project_number}/locations/europe-west1/indexEndpoints/{self.index_endpoint_id}",
            project=self.gcp_project_id,
            location=self.gcp_region,
            credentials=self.credentials,
        )

        res = index_endpoint.find_neighbors(
            deployed_index_id=self.deployed_index_id,
            queries=[query_vec],
            num_neighbors=num_neighbors,
        )

        matched_ids = [match.id for match in res[0] if match.distance >= match_thresh]

        print(f"Matched ids: {matched_ids}")

        return matched_ids
