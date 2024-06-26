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

# from EmbeddingSession import EmbeddingSession
# from VectorSearchSession import VectorSearchSession
# from LLMSession import LLMSession

from rsc.EmbeddingSession import EmbeddingSession
from rsc.VectorSearchSession import VectorSearchSession
from rsc.LLMSession import LLMSession

from dotenv import dotenv_values

import firebase_admin
from firebase_admin import firestore
import google.auth


class SearchQuerySession:
    def __init__(self, model_name: str):
        self.embedding_session = EmbeddingSession()
        self.secrets = dotenv_values(".env")
        self.credentials, _ = google.auth.load_credentials_from_file(
            self.secrets["GCP_CREDENTIAL_FILE"]
        )
        self.vector_search_session = VectorSearchSession(
            gcp_project_id=self.secrets["GCP_PROJECT_ID"],
            gcp_project_number=self.secrets["GCP_PROJECT_NUMBER"],
            credentials=self.credentials,
            index_endpoint_id=self.secrets["VECTOR_SEARCH_INDEX_ENDPOINT_ID"],
            deployed_index_id=self.secrets["VECTOR_SEARCH_DEPLOYED_INDEX_ID"],
            gcp_region = self.secrets["GCP_REGION"],
            api_endpoint = self.secrets["GCP_MATCHING_ENGINE_ENDPOINT"]
        )
        self.firestore_collection_name = self.secrets["FIRESTORE_COLLECTION_NAME"]
        self.model_name = model_name

    def __call__(self, client_query, image=None) -> tuple:
        if image is not None:
            answer, sources = self._main(client_query, image)
        else: 
            answer, sources = self._main(client_query)
        print(answer)
        print(sources)
        return answer, sources

    def _main(self, client_query, image=None):
        """
        Orchestrates answer generation steps.
        """
        # Generate Client Query Embedding.
        
        print("+++++ Generating Client Query Embedding... +++++")
        client_query_embedding = self.embedding_session.get_vertex_embedding(
            text_to_embed=client_query
        )

        # Find nearest matches for client query embedding.
        print("+++++ Finding Client Query Matches... +++++")
        matched_ids = self.vector_search_session.find_matches(
            query_vec=client_query_embedding, num_neighbors=10, match_thresh=0.6
        )

        # Get matched documents from Firestore.
        print("+++++ Pulling Docs from Firestore... +++++")
        relevant_docs_content, relevant_docs_names = self._get_doc_from_firestore(
            matched_ids
        )
        joined_docs_content = " ".join(relevant_docs_content)
        
        # call LLM with final prompt
        print("+++++ Prompting LLM with final prompt... +++++")   
        llm_answer = LLMSession(
            client_query_string=client_query,
            context_docs=joined_docs_content,
            model_name=self.model_name,
            image = image,
        ).llm_prediction(max_output_tokens=1024, temperature=0.1, top_p=0.6, top_k=20)

        return llm_answer, relevant_docs_names

    def _get_doc_from_firestore(self, matched_ids):
        # method to get document from firestore
        if not firebase_admin._apps:
            credentials = firebase_admin.credentials.Certificate(
                self.secrets["GCP_CREDENTIAL_FILE"]
            )
            app = firebase_admin.initialize_app(credentials)

        # Setup & auth firestore client.
        db = firestore.Client(project=self.secrets["GCP_PROJECT_ID"], credentials=self.credentials, database=self.secrets["FIRESTORE_DATABASE_ID"])

        # Pull relevant docs from Firestore collection.
        relevant_docs = []
        for id in matched_ids:
            doc = (
                db.collection(self.firestore_collection_name)
                .document(id)
                .get()
                .to_dict()
            )
            if doc is not None:  # dropping empty documents
                relevant_docs.append(doc)

        relevant_docs_content = []
        relevant_docs_names = []

        for doc in relevant_docs:
            relevant_docs_content.append(doc["page_content"])
            if doc["document_name"] not in relevant_docs_names:
                relevant_docs_names.append(doc["document_name"])

        return relevant_docs_content, relevant_docs_names


if __name__ == "__main__":
    # cwd = os.getcwd()
    # print(cwd)

    # os.chdir("../retrieval-aug-agent")

    # cwd = os.getcwd()
    # print(cwd)

    query_session = SearchQuerySession(model_name="gemini-pro")
    query_session(client_query="Who won the nobel peace prize in 2023?")
    print("Hello World!")
