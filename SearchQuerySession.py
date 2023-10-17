from EmbeddingSession import EmbeddingSession
from VectorSearchSession import VectorSearchSession
from LLMSession import LLMSession

import secrets_1

import firebase_admin
from firebase_admin import firestore

class SearchQuerySession:
    def __init__(self):
        self.embedding_session = EmbeddingSession()
        self.vector_search_session = VectorSearchSession(gcp_project_id=secrets_1.gcp_project_id,
                                                         gcp_project_number=secrets_1.gcp_project_number,
                                                         credentials=secrets_1.credentials,
                                                         index_endpoint_id=secrets_1.vector_search_index_endpoint_id,
                                                         deployed_index_id=secrets_1.vector_search_deployed_index_id)
        self.firestore_collection_name = secrets_1.firestore_collection_name

    def __call__(self, client_query) -> dict:
        answer, sources = self._main(client_query)
        print(answer)
        print(sources)
        return answer, sources

    def _main(self, client_query):
        """
        Orchestrates answer generation steps.
        """
        # Generate Client Query Embedding.
        print("+++++ Generating Client Query Embedding... +++++")
        client_query_embedding = self.embedding_session.get_vertex_embedding(text_to_embed=client_query)

        # Find nearest matches for client query embedding.
        print("+++++ Finding Client Query Matches... +++++")
        matched_ids = self.vector_search_session.find_matches(query_vec=client_query_embedding,
                                                              num_neighbors=10,
                                                              match_thresh=.7)
        
        # Get matched documents from Firestore.
        print("+++++ Pulling Docs from Firestore... +++++")
        relevant_docs_content, relevant_docs_names = self._get_doc_from_firestore(matched_ids)
        joined_docs_content = " ".join(relevant_docs_content)

        # call LLM with final prompt
        print("+++++ Prompting LLM with final prompt... +++++")
        llm_answer = LLMSession(client_query_string=client_query, context_docs=joined_docs_content).llm_prediction(max_output_tokens=1024,
                                                                                                                    temperature=0.1,
                                                                                                                    top_p=0.6,
                                                                                                                    top_k=20)
        
        return llm_answer, relevant_docs_names
    
    def _get_doc_from_firestore(self, matched_ids):
        # method to get document from firestore
        if not firebase_admin._apps:
            app = firebase_admin.initialize_app()

        # Setup & auth firestore client.
        db = firestore.Client(project=secrets_1.project_id, credentials=secrets_1.credentials)

        # Pull relevant docs from Firestore collection.
        relevant_docs = []
        for id in matched_ids:
            doc = db.collection(self.firestore_collection_name).document(id).get().to_dict()
            if doc is not None: # dropping empty documents
                relevant_docs.append(doc)

        relevant_docs_content = []
        relevant_docs_names = []

        for doc in relevant_docs:
            relevant_docs_content.append(doc['page_content'])
            if doc['document_name'] not in relevant_docs_names:
                relevant_docs_names.append(doc['document_name'])
            
        # relevant_docs_names = [doc["document_name"] for doc in relevant_docs if doc["document_name"] not in relevant_docs]
        # relevant_docs_content = [doc["page_content"] for doc in relevant_docs]

        return relevant_docs_content, relevant_docs_names


if __name__ == "__main__":
    query_session = SearchQuerySession()
    query_session(client_query="How were knights being paid?")
    print("Hello World!")
