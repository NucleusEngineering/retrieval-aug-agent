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

import chunk
from os import path
from dotenv import dotenv_values

from google.cloud import bigquery
from google.cloud import aiplatform_v1
from google.cloud import storage
import google.auth

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


class DeletionSession:
    def __init__(self) -> None:
        self.secrets = dotenv_values(".env")

        if not firebase_admin._apps:
            credentials = firebase_admin.credentials.Certificate(
                self.secrets["GCP_CREDENTIAL_FILE"]
            )
            app = firebase_admin.initialize_app(credentials)

        self.credentials, self.project_id = google.auth.load_credentials_from_file(
            self.secrets['GCP_CREDENTIAL_FILE'])
        self.firestore_client = firestore.Client(
            project=self.secrets["GCP_PROJECT_ID"], credentials=self.credentials, database=self.secrets["FIRESTORE_DATABASE_ID"])

        self.firestore_collection_name = self.secrets["FIRESTORE_COLLECTION_NAME"]

    def __call__(self, document_name=None, ids_to_delete=None) -> None:
        """
        Orchestrate the deletion session.
        """

        # Check that exactly one argument is provided.
        if (document_name is None and ids_to_delete is None) or (
            document_name is not None and ids_to_delete is not None
        ):
            raise ValueError("Exactly one argument must be provided.")

        if ids_to_delete is None:
            document_name = str(document_name)
            ids_to_delete = self._search_doc_ids(document_name)

        # Delete original file from gcs bucket.
        print("Deleting from GCS...")
        self._delete_doc_from_gcs(document_name)

        # ids_to_delete = ['The-ultimate-guide-on tracking-problems-part1-chunk0', 'The-ultimate-guide-on tracking-problems-part1-chunk1', 'The-ultimate-guide-on tracking-problems-part1-chunk10', 'The-ultimate-guide-on tracking-problems-part1-chunk11', 'The-ultimate-guide-on tracking-problems-part1-chunk12', 'The-ultimate-guide-on tracking-problems-part1-chunk13', 'The-ultimate-guide-on tracking-problems-part1-chunk14', 'The-ultimate-guide-on tracking-problems-part1-chunk15', 'The-ultimate-guide-on tracking-problems-part1-chunk16', 'The-ultimate-guide-on tracking-problems-part1-chunk17', 'The-ultimate-guide-on tracking-problems-part1-chunk18', 'The-ultimate-guide-on tracking-problems-part1-chunk19', 'The-ultimate-guide-on tracking-problems-part1-chunk2', 'The-ultimate-guide-on tracking-problems-part1-chunk20', 'The-ultimate-guide-on tracking-problems-part1-chunk3', 'The-ultimate-guide-on tracking-problems-part1-chunk4', 'The-ultimate-guide-on tracking-problems-part1-chunk5', 'The-ultimate-guide-on tracking-problems-part1-chunk6', 'The-ultimate-guide-on tracking-problems-part1-chunk7', 'The-ultimate-guide-on tracking-problems-part1-chunk8', 'The-ultimate-guide-on tracking-problems-part1-chunk9', 'The-ultimate-guide-on tracking-problems-part2-chunk0', 'The-ultimate-guide-on tracking-problems-part2-chunk1', 'The-ultimate-guide-on tracking-problems-part2-chunk2']

        if len(ids_to_delete) == 0:
            print("No documents to delete in Firestore and Vector Search.")
            return None

        # Delete chunk embedding string matching from firestore.
        print("Deleting from firestore...")
        self._delete_docs_from_firestore(ids_to_delete)

        # Delete chunk embedding from vector store.
        print("Deleting from Vector Search...")
        self._delete_docs_from_vectorstore(ids_to_delete)

        print("Deleting Docs from BigQuery...")
        # self._delete_doc_from_bigquery(ids_to_delete)

        print("Deletion session complete.")
        return None

    def _search_doc_ids(self, document_name: str) -> list:
        """
        Method to search for document ids in in the firestore collection based on the document name.
        """

        cleaned_doc_name, _, _ = document_name.partition("-chunk")
        end_prefix = cleaned_doc_name[:-1] + str(int(cleaned_doc_name[-1]) + 1)

        print(f"Cleaned: {cleaned_doc_name}")
        print(f"End Prefix: {end_prefix}")

        db = self.firestore_client.collection(self.firestore_collection_name)
        query = db.where(filter=FieldFilter(u'id', u'>=', cleaned_doc_name)).where(u'id', u'<', end_prefix)

        list_of_ids = [doc_snapshot.id for doc_snapshot in query.stream()]

        print(f"ids to delete: {list_of_ids}")

        if len(list_of_ids) == 0:
            print("No documents exist for this name.")
            return []


        return list_of_ids

    def _delete_docs_from_firestore(self, ids_to_delete: list) -> None:
        """
        Method to delete the documents from the firestore collection.
        """
        # Get the document references you want to delete
        document_refs = [
            self.firestore_client.collection(self.firestore_collection_name).document(
                doc_id
            )
            for doc_id in ids_to_delete
        ]

        # Create a batch and add delete operations
        batch = self.firestore_client.batch()
        for ref in document_refs:
            batch.delete(ref)

        # Commit the batch
        batch.commit()

        print(f"Deleted from firestore.")
        return None

    def _delete_docs_from_vectorstore(self, ids_to_delete: list) -> None:
        """
        Method to delete the documents from the vectorstore.
        """
        # Create a client

        index_client = aiplatform_v1.IndexServiceClient(credentials=self.credentials, client_options=dict(
            api_endpoint=f"{self.secrets['GCP_REGION']}-aiplatform.googleapis.com"
        ))

        index_name = f"projects/{self.secrets['GCP_PROJECT_NUMBER']}/locations/{self.secrets['GCP_REGION']}/indexes/{self.secrets['VECTOR_SEARCH_INDEX_ID']}"

        # Initialize request argument(s)
        deletion_request = aiplatform_v1.RemoveDatapointsRequest(
            index=index_name,
            datapoint_ids=ids_to_delete,
        )

        # Make the request
        response = index_client.remove_datapoints(request=deletion_request)

        # Handle the response
        print(response)

        print(f"Deleted from vector store.")
        return None

    def _delete_doc_from_gcs(self, document_name) -> None:
        """
        Method to delete the selected document from the GCS bucket.
        """
        # store raw uploaded pdf in gcs

        storage_client = storage.Client(credentials=self.credentials)
        bucket = storage_client.bucket(self.secrets["RAW_PDFS_BUCKET_NAME"])

        blob = bucket.blob("documents/raw_uploaded/" + document_name + ".pdf")

        blob.delete()

        print(f"Deleted {document_name} from GCS.")
        return None

    def _delete_doc_from_bigquery(self, ids_to_delete: list) -> None:
        client = bigquery.Client(project=self.secrets['GCP_PROJECT_ID'],
                                 credentials=self.credentials, location=self.secrets["GCP_REGION"])

        formatted_id_list = ", ".join(["'{}'".format(id) for id in ids_to_delete])

        bq_query_str = f"""
            DELETE FROM `{self.secrets["GCP_PROJECT_ID"]}.{self.secrets["BIGQUERY_DATASET"]}.{self.secrets["BIGQUERY_TABLE"]}`
            WHERE id IN ({formatted_id_list})
            """

        query_job = client.query(query=bq_query_str)

        query_job.result() 
        print("Chunks deleted from BigQuery")

        return None


if __name__ == "__main__":
    delete = DeletionSession()
    # delete(
    #     document_name="Physicist Narges Mohammadi awarded Nobe... for human-rights work – Physics World-part0.pdf"
    # )

    delete(document_name="The-ultimate-guide-on tracking-problems-part2")

    # print("###")
    # to_be_deleted = [str(i) for i in list(range(2055))]
    # print(to_be_deleted)
    # delete(ids_to_delete=to_be_deleted)

    # to_be_deleted = ['Physicist Narges Mohammadi awarded Nobe... for human-rights work – Physics World-0',
    #                    'Physicist Narges Mohammadi awarded Nobe... for human-rights work – Physics World-1',
    #                    'Physicist Narges Mohammadi awarded Nobe... for human-rights work – Physics World-2',
    #                    'Physicist Narges Mohammadi awarded Nobe... for human-rights work – Physics World-3',
    #                    'Physicist Narges Mohammadi awarded Nobe... for human-rights work – Physics World-4',
    #                    'Physicist Narges Mohammadi awarded Nobe... for human-rights work – Physics World-5']

    # ids = delete._search_doc_ids(document_name="Physicist Narges Mohammadi awarded Nobe... for human-rights work – Physics World (1)-part0")

    # delete._delete_doc_from_bigquery(ids_to_delete=ids)

    print("Hello World!")
