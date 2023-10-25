import datetime
from dotenv import dotenv_values

import streamlit as st
import pandas as pd

from google.cloud import storage
import google.auth

from rsc.SearchQuerySession import SearchQuerySession
from rsc.IngestionSession import IngestionSession

secrets = dotenv_values(".env")
credentials, _ = google.auth.load_credentials_from_file(secrets['GCP_CREDENTIAL_FILE'])

def main(client_query:str) -> None:  

    with st.spinner('Processing... This might take a minute or two.'):

        query_session = SearchQuerySession()
        answer, sources = query_session(client_query=client_query)

        df = pd.DataFrame({"Sources": sources})
        st.dataframe(df)

    st.write(answer['text'])

    return None


def get_current_files(bucket_name, secrets=secrets, credentials=credentials) -> list:

    bucket = storage.Client(project=secrets['GCP_PROJECT_ID'], credentials=credentials).bucket(bucket_name)
    files_with_links = [(blob.path.split("/")[-1], blob.generate_signed_url(expiration=datetime.timedelta(minutes=10))) for blob in bucket.list_blobs()]

    return files_with_links


def upload_new_file(new_file:bytes, new_file_name:str) -> None:
    
    ingestion = IngestionSession()

    ingestion(new_file_name=new_file_name, file_to_ingest=new_file, ingest_local_file=False)

    return None


st.title('These files are currently in your knowledge base.')

df = pd.DataFrame(get_current_files(bucket_name=secrets["RAW_PDFS_BUCKET_NAME"]))
st.dataframe(df)


st.title('Upload a new file to your knowledge base.')

with st.form("file_upload_form"):
    uploaded_file = st.file_uploader("Choose a file")
    
    button = st.form_submit_button('Upload', help=None, on_click=None, args=None, kwargs=None, type="primary", disabled=False, use_container_width=False)

    if button:
        upladed_file_name = uploaded_file.name
        uploaded_file_bytes = uploaded_file.getvalue()
        upload_new_file(new_file=uploaded_file_bytes, new_file_name=upladed_file_name)


st.title('Ask a question towards your knowledge base.')

with st.form("transcript_submission_form"):

    client_query = st.text_input("Question:")

    button = st.form_submit_button('Ask', help=None, on_click=None, args=None, kwargs=None, type="primary", disabled=False, use_container_width=False)

    if button:
        main(client_query=client_query)
