import google.auth

import os

cwd = os.getcwd()
print(cwd)

gcp_credential_file = "<link-to-sa-credential-file>"
gcp_project_id = "<project-id>"
gcp_project_number = "<project-number>"
vector_search_index_endpoint_id="<index-endpoint-id>" # numeric
vector_search_deployed_index_id = "<deployed-index-id>" # alphanumeric
firestore_collection_name = "<firestore-collection-name>"
document_ai_processor_id = "<document-ai-processor-id>"
document_ai_processor_version = "<document-ai-processor-version>"
raw_pdfs_bucket_name = "<raw-pdf-bucket-name>"

credentials, project_id = google.auth.load_credentials_from_file(gcp_credential_file)