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


class DocPreview:
    def __init__(self):
        pass

    def render(self):
        row_count = 2

        with st.container(border=True):
            st.write("This is inside the container")

            for i in range(row_count):
                
                    col1, col2, col3 = st.columns(3)

                    # Add widgets to the columns
                    with col1:
                        st.header("A cat")
                        st.image("PDF_file_icon.png")
                        st.button('delete', key=f'delete_col1_{i}')

                    with col2:
                        st.header("A dog")
                        st.image("PDF_file_icon.png")
                        st.button('delete', key=f'delete_col2_{i}')

                    with col3:
                        # st.header("An owl")
                        # st.image("https://static.streamlit.io/examples/owl.jpg")
                        # st.button('delete', key=f'delete_col3_{i}')
                        pass




def main(client_query:str) -> None:  

    with st.spinner('Processing... This might take a minute or two.'):

        query_session = SearchQuerySession()
        answer, sources = query_session(client_query=client_query)

        df = pd.DataFrame({"Sources": sources})
        st.dataframe(df)

    st.write(answer['text'])

    return None

def extract_filename_from_url(text):
  """
  Extracts the string between the last `/` and `.pdf` from a text.

  Args:
    text: The text to extract from.

  Returns:
    The extracted string, or None if not found.
  """
  # Find the last occurrence of `&%`
  last_percent = text.rfind("/")

  # Find the next occurrence of `.pdf`
  next_pdf = text.find(".pdf", last_percent)

  # Extract the substring if both patterns were found
  if last_percent != -1 and next_pdf != -1:
    return text[last_percent + 1:next_pdf]
  else:
    return text 


def get_current_files(bucket_name, secrets=secrets, credentials=credentials) -> list:
    bucket = storage.Client(project=secrets['GCP_PROJECT_ID'], credentials=credentials).bucket(bucket_name)
    
    files_with_links = [(extract_filename_from_url(blob.name), blob.generate_signed_url(expiration=datetime.timedelta(minutes=10))) for blob in bucket.list_blobs()]    
    
    return files_with_links


def upload_new_file(new_file:bytes, new_file_name:str) -> None:
    
    ingestion = IngestionSession()

    ingestion(new_file_name=new_file_name, file_to_ingest=new_file, ingest_local_file=False)

    return None


st.title('These files are currently in your knowledge base.')

df = pd.DataFrame(get_current_files(bucket_name=secrets["RAW_PDFS_BUCKET_NAME"]))
st.dataframe(df)

# st.title('Knowledge Base Columns.')
# DocPreview().render()


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
