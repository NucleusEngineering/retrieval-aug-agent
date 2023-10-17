from VectorSearchSession import VectorSearchSession
from EmbeddingSession import EmbeddingSession
import secrets_1

import os 
import json

from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google.cloud import storage
from google.cloud import aiplatform_v1

import firebase_admin
from firebase_admin import firestore

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import streamlit as st


class IngestionSession:
    def __init__(self,
                 docai_processor_id=secrets_1.document_ai_processor_id,
                 docai_processor_version=secrets_1.document_ai_processor_version,
                 chunk_size=1000,
                 chunk_overlap=50):
        
        self.vector_search_session = VectorSearchSession(gcp_project_id=secrets_1.gcp_project_id,
                                                         gcp_project_number=secrets_1.gcp_project_number,
                                                         credentials=secrets_1.credentials,
                                                         index_endpoint_id=secrets_1.vector_search_index_endpoint_id,
                                                         deployed_index_id=secrets_1.vector_search_deployed_index_id)
        
        self.docai_processor_id = docai_processor_id
        self.docai_processor_version = docai_processor_version
        self.embedding_session = EmbeddingSession()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def __call__(self, file_to_ingest, new_file_name: str) -> None:

        print("+++++ Upload raw PDF... +++++")
        self._store_raw_upload(file_to_ingest=file_to_ingest, new_file_name=new_file_name)

        print("+++++ Document OCR... +++++")
        document_string = self._ocr_pdf(processor_id=self.docai_processor_id,
                      processor_version=self.docai_processor_version,
                      file_path=file_to_ingest)
        
        print("+++++ Chunking Document... +++++")
        list_of_chunks = self._chunk_doc(stringified_doc=document_string,
                                         file_name=new_file_name,
                                         chunk_size=self.chunk_size,
                                         chunk_overlap=self.chunk_overlap)

        print("+++++ Store Embeddings & Document Identifiers in Firestore... +++++")
        self._firestore_index_embeddings(list_of_chunks)
        
        print("+++++ Generating Document Embeddings... +++++")
        embeddings_to_ingest = self._chunk_to_index_input(list_of_chunks)

        print("+++++ Updating Vector Search Index... +++++")
        self._vector_index_streaming_upsert(embeddings_to_ingest)

        return None

    def _process_document(self,
                          location: str,
                          processor_id: str,
                          processor_version: str,
                          file_path: str,
                          mime_type: str,
                          process_options = None) -> documentai.Document:
        
        client = documentai.DocumentProcessorServiceClient(
            credentials=secrets_1.credentials,
            client_options=ClientOptions(
                api_endpoint=f"{location}-documentai.googleapis.com"
            )
        )

        file_path = file_path.getvalue()

        name = client.processor_version_path(
            secrets_1.project_id, location, processor_id, processor_version
        )

        # # Read the file into memory
        # with open(file_path, "rb") as image:
        #     image_content = image.read()

        image_content = file_path

        # Configure the process request
        request = documentai.ProcessRequest(name=name,
                                            raw_document=documentai.RawDocument(content=image_content,
                                                                                mime_type=mime_type),
                                            process_options=process_options)

        result = client.process_document(request=request)

        return result.document

    def _ocr_pdf(self,
                 processor_id: str,
                 processor_version: str,
                 file_path: str,
                 location: str = "eu",
                 mime_type: str = "application/pdf") -> str:
        
        process_options = documentai.ProcessOptions(
            ocr_config=documentai.OcrConfig(
                enable_native_pdf_parsing=True,
                enable_image_quality_scores=True,
                enable_symbol=True,
                premium_features=documentai.OcrConfig.PremiumFeatures(
                    compute_style_info=True,
                    enable_math_ocr=False,
                    enable_selection_mark_detection=True,
                ),
            )
        )

        # Online processing request to Document AI
        document = self._process_document(
            location=location,
            processor_id=processor_id,
            processor_version=processor_version,
            file_path=file_path,
            mime_type=mime_type,
            process_options=process_options,
        )

        return document.text

    def _chunk_doc(self, stringified_doc:str, file_name, chunk_size, chunk_overlap) -> list:
        # method to chunk a given doc

        doc =  Document(page_content=stringified_doc)
        doc.metadata["document_name"] = file_name.split("/")[-1]

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                                       chunk_overlap=chunk_overlap,
                                                       separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""])
        
        doc_splits = text_splitter.split_documents([doc])

        for idx, split in enumerate(doc_splits):
            split.metadata["chunk_identifier"] = file_name.split("/")[-1].split(".pdf")[0] + "-" + str(idx)

        return doc_splits
    
    def _generate_embedding(self, text_to_embed):
        # method to generate embedding for a given text
        embedding = self.embedding_session.get_vertex_embedding(text_to_embed=text_to_embed)
        return embedding
    
    def _chunk_to_index_input(self, list_of_chunks: list) -> list:
        # turning chunk strings into jsons ready to be indexed by vector search
        
        # generate embeddings & merge with chunk embedding identifier
        embedded_docs = [json.dumps({"id": d.metadata["chunk_identifier"],
                                     "embedding": self._generate_embedding(d.page_content)})+ "\n" for d in list_of_chunks]

        return embedded_docs
    
    def _store_raw_upload(self, file_to_ingest, new_file_name) -> None:
        # store raw uploaded pdf in gcs

        storage_client = storage.Client(credentials=secrets_1.credentials)
        bucket = storage_client.bucket(secrets_1.raw_pdfs_bucket_name)

        # if isinstance(file_to_ingest, str):
        #     blob = bucket.blob("documents/raw_uploaded/" + new_file_name.split("/")[-1])
        #     blob.upload_from_filename(file_to_ingest)
        # else:
        # with open(file_to_ingest, 'r') as f:
        
        blob = bucket.blob("documents/raw_uploaded/" + new_file_name.split("/")[-1])
        blob.upload_from_file(file_to_ingest)

        return None

    def _firestore_index_embeddings(self, doc_splits: list) -> None:
        # upload embeddings to firestore

        if not firebase_admin._apps:
            app = firebase_admin.initialize_app()

        db = firestore.Client(project=secrets_1.project_id, credentials=secrets_1.credentials)
        
        for split in doc_splits:
            data = {"id": split.metadata["chunk_identifier"],
                    "document_name": split.metadata["document_name"],
                    "page_content": split.page_content}

            # Add a new doc in collection with embedding, doc name & chunk identifier
            db.collection(secrets_1.firestore_collection_name).document(str(split.metadata["chunk_identifier"])).set(data)

        print(f"Added {[split.metadata['chunk_identifier'] for split in doc_splits]}")
        
        return None

    def _vector_index_streaming_upsert(self, upsert_datapoints:list) -> None:
        # method to upsert embeddings to vector search index

        index_client = aiplatform_v1.IndexServiceClient(credentials=secrets_1.credentials, client_options=dict(
            api_endpoint=f"europe-west1-aiplatform.googleapis.com"
        ))
        # index_client.

        # index_name = f"projects/{secrets_1.gcp_project_number}/locations/europe-west1/indexEndpoints/{secrets_1.vector_search_index_endpoint_id}"
        index_name = f"projects/{secrets_1.gcp_project_number}/locations/europe-west1/indexes/3441260288706347008"
        
        insert_datapoints_payload = []

        for dp in upsert_datapoints:
            dp_dict = json.loads(dp)
            insert_datapoints_payload.append(aiplatform_v1.IndexDatapoint(datapoint_id=dp_dict["id"], feature_vector=dp_dict["embedding"], restricts= []))

        upsert_request = aiplatform_v1.UpsertDatapointsRequest(index=index_name, datapoints=insert_datapoints_payload)

        index_client.upsert_datapoints(request=upsert_request)

        return None


if __name__ == "__main__":

    cwd = os.getcwd()
    print(cwd)

    ingestion = IngestionSession()

    storage_client = storage.Client(credentials=secrets_1.credentials)
    bucket = storage_client.bucket(secrets_1.raw_pdfs_bucket_name)

    # blob = bucket.blob("documents/raw_uploaded/" + new_file_name.split("/")[-1])
    # file_bytes = blob.download_as_bytes()

    with open("./woher-kommen-bekannte-markennamen.pdf", 'rb') as f:
        file_bytes = f.read()
        ingestion(file_to_ingest=file_bytes, new_file_name="woher-kommen-bekannte-markennamen.pdf")

    # ingestion(file_to_ingest="./woher-kommen-bekannte-markennamen.pdf", new_file_name="woher-kommen-bekannte-markennamen.pdf")

    # ingestion._firestore_index_embeddings(doc_splits=ingestion._chunk_doc()
    ingestion._vector_index_streaming_upsert([])
    print("Hello World!")