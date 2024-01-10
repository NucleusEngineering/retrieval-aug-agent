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

import math
import datetime
from dotenv import dotenv_values

import streamlit as st
import pandas as pd
import PyPDF2
from io import BytesIO
from io import StringIO

from google.cloud import storage
import google.auth


from rsc.SearchQuerySession import SearchQuerySession
from rsc.IngestionSession import IngestionSession
from rsc.retrievers.NotionRetriever import NotionRetrievalSession

from rsc.DeletionSession import DeletionSession


secrets = dotenv_values(".env")
credentials, _ = google.auth.load_credentials_from_file(secrets['GCP_CREDENTIAL_FILE'])


class DocPreview:
    def __init__(self, list_of_docs: list):
        self.list_of_docs = list_of_docs
        self.row_count = math.ceil(len(self.list_of_docs) / 3) 
        self.doc_count = len(self.list_of_docs)
        self.doc_index = 0

    def render(self):
        with st.container(border=True):

            for _ in range(self.row_count):
                
                col1, col2, col3 = st.columns(3)

                with col1:
                    self._render_doc_col()

                with col2:
                    self._render_doc_col()

                with col3:
                    self._render_doc_col()

    def _render_doc_col(self):
        if self.doc_index < self.doc_count:
            self._render_doc_item(doc_name_and_url=self.list_of_docs[self.doc_index])
            self.doc_index += 1
        else:
            pass

    def _render_doc_item(self, doc_name_and_url):
        doc_name = doc_name_and_url[0]
        doc_link = doc_name_and_url[1]

        st.write(f"[{doc_name}](%s)" % doc_link)
        st.image("PDF_file_icon.png", width=50)
        # print((doc_name))
        st.button('delete', key=f'delete_{doc_name}', on_click=delete_file, args=[doc_name])

def main(client_query:str, model_name: str) -> None:  

    with st.spinner('Processing... This might take a minute or two.'):

        query_session = SearchQuerySession(model_name=model_name)
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

    print(list(bucket.list_blobs()))
    
    files_with_links = [(extract_filename_from_url(blob.name), blob.generate_signed_url(expiration=datetime.timedelta(minutes=10))) for blob in bucket.list_blobs() if ".pdf" in str(blob.name)]    
    
    return files_with_links


def upload_new_file(new_file:bytes, new_file_name:str, max_pages_per_file:int) -> None:
    
    ingestion = IngestionSession() 

    pdf_file = BytesIO(new_file)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    num_pages = len(pdf_reader.pages)
    
    # print number of pages 
    print(f"Total Pages: {num_pages}") 

    # check if PDF file exceeds the page limit
    if num_pages > max_pages_per_file:
        output_file_index = 1
        output_file_name = f"{new_file_name[:-4]}-part{output_file_index}.pdf"
        pdf_writer = PyPDF2.PdfWriter()
        tmp = BytesIO()

        for page_num in range(num_pages):
            pdf_writer.add_page(pdf_reader.pages[page_num])

            if page_num % max_pages_per_file == max_pages_per_file - 1:
                pdf_writer.write(tmp)
                output_file_bytes = tmp.getvalue()
                ingestion(new_file_name=output_file_name, file_to_ingest=output_file_bytes, ingest_local_file=False)

                output_file_index += 1
                output_file_name = f"{new_file_name[:-4]}-part{output_file_index}.pdf"
                pdf_writer = PyPDF2.PdfWriter()
                tmp = BytesIO()

        # Write any remaining pages to the last output file
        if page_num % max_pages_per_file != max_pages_per_file - 1:
            pdf_writer.write(tmp)
            output_file_bytes = tmp.getvalue()
            ingestion(new_file_name=output_file_name, file_to_ingest=output_file_bytes, ingest_local_file=False)

        print("Splitting & Ingestion completed.")

    else:
        ingestion(new_file_name=new_file_name, file_to_ingest=new_file, ingest_local_file=False)
        print("PDF file has", num_pages, "pages or less, no splitting was needed. Ingestetion completed.")


    return None


def fetch_notion_database(database_id:str) -> None:
    notion_retrieval = NotionRetrievalSession()

    notion_data, notion_page_titles = notion_retrieval(database_id=database_id) 

    ingestion = IngestionSession()

    ingestion(new_file_name=database_id, ingest_notion_database=True, data_to_ingest=notion_data, notion_page_titles = notion_page_titles)

    return None


def delete_file(document_name:str) -> None:
    print(f'deletion {document_name}')
    
    deletion = DeletionSession()

    deletion(document_name=document_name)

    return None

st.title('These files are currently in your knowledge base.')

current_files = get_current_files(bucket_name=secrets["RAW_PDFS_BUCKET_NAME"])
df = pd.DataFrame(current_files)
st.dataframe(df)

DocPreview(list_of_docs=current_files).render()


st.title('Upload a new file to your knowledge base.')

with st.form("file_upload_form"):
    uploaded_file = st.file_uploader("Choose a file")
    
    button = st.form_submit_button('Upload', help=None, on_click=None, args=None, kwargs=None, type="primary", disabled=False, use_container_width=False)

    if button and uploaded_file is not None:
        upladed_file_name = uploaded_file.name
        uploaded_file_bytes = uploaded_file.getvalue()
        upload_new_file(new_file=uploaded_file_bytes, new_file_name=upladed_file_name, max_pages_per_file=15)

st.title('Upload data from your Notion database')

with st.form("notion_upload_form"):
    client_database_id = st.text_input("Database-ID:")

    button = st.form_submit_button('Upload data', help=None, on_click=None, args=None, kwargs=None, type="primary", disabled=False, use_container_width=False)

    if button:
        print (client_database_id )
        client_database_id = client_database_id
        fetch_notion_database(database_id=client_database_id)


st.title('Ask a question towards your knowledge base.')

with st.form("transcript_submission_form"):

    client_query = st.text_input("Question:")

    model_name = str(st.selectbox('Which Model would you like to ask?', ('text-bison@001', 'text-bison@002', 'text-unicorn@001', 'gemini-pro'), placeholder='text-bison@002'))

    button = st.form_submit_button('Ask', help=None, on_click=None, args=None, kwargs=None, type="primary", disabled=False, use_container_width=False)

    if button:
        main(client_query=client_query, model_name=model_name)
