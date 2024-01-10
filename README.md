# Retrieval Augmented QA & Agent

This is an implementation of the Retrieval Augmented Generation (RAG) pattern to power a Q&A across mutliple knowledge management platforms.

On top we are building (wip) an Retrieval Augmented Agent that is able to take actions instructured by natural language in the underlying knowledge base.

At this point we developed integrations to connect a bucket of PDFs and a Notion DB as knowledge base to answer questions and take actions.

Expected behaviour will be that the model responds to questions and takes actions exclusively based on the data contained in the knowledge base.

## Solution Demo

The Streamlit UI allows adding and deleting PDF files to and from the knowlegdge base. To connect a Notion DB enter the respective Database ID.

Once your knowledgebase is connected succesfully select an LLM and enter a query.

![user interface demo](./ui_demo.png)

## Architecture RAG Q&A
The full tooling is using Google Cloud Platform (GCP) native technology.

* Document OCR: [Document AI](https://cloud.google.com/document-ai/docs/overview)
* Generation of Content & User Query embeddings: [PaLM Embedding Model](https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings)
* Storing and making vector embeddings searchable: [Vertex Vector Search](https://cloud.google.com/vertex-ai/docs/vector-search/overview)
* Ledger connecting embeddings to original content strings: [Firestore](https://firebase.google.com/docs/firestore)
* generating a conversational response to the users original question based on the content identified as relevant: [PaLM text model](https://cloud.google.com/vertex-ai/docs/generative-ai/text/test-text-prompts)

![Retrieval Augmented Generation (RAG) based QA Architecture](./rag_qa.png)

## Set Up RAG Q&A
To set up the Retrieval Augmented Generation (RAG) based QA Architecture execute the following steps:

* Important requirements: make sure that all resources are deplyed in the same region or multi-region.

1. **Create a GCP service account and grant the relevant permissions**
    * Disclaimer: This method was chosen to simplify the demo process. In general we recommend to avoid using service account keys whenever possible. For best practices check our [documentation on IAM roles & permissions](https://cloud.google.com/iam/docs/roles-overview).

    * [Docs to create a service account](https://cloud.google.com/iam/docs/service-accounts-create#iam-service-accounts-create-console)
    * Assign the following IAM roles to the service account:
        * Document AI API User
        * Firebase Admin SDK Administrator Service Agent
        * Service Account Token Creator
        * Storage Admin
        * Vertex AI User

2. **Authenticate your Google Cloud Service Account**
    * Disclaimer: This method was chosen to simplify the demo process. In general we recommend to avoid using service account keys whenever possible. For best practices check our [documentation on service accounts](https://cloud.google.com/iam/docs/best-practices-service-accounts).

    * Create a service account key to authenticate your demo environment. Relevant documentation can be found [here](https://cloud.google.com/iam/docs/keys-create-delete).

3. **Create your Google Cloud Storage buckets**
    * Create a multiregional storage bucket for the documents of your knowledge base
    * Create a regional bucket to store the vectors for your vector search index:
        * Folder structure of the bucket has to be: 
        >> *── batch_root── delete*
    * [Documentation on how to create a bucket](https://cloud.google.com/storage/docs/creating-buckets#storage-create-bucket-console)

4. **Upload the embeddings_0.json file into your 'batch_root' folder in the regional bucket.**

5. **Create a Vector Search Index & Endpoint**
    * Use the created regional storage bucket and select batch_root/ as the root folder for the Vector Search Index
    * Set the parameters for the index:
        * Algorithm type: tree-AH
        * Dimensions: 768
        * Approx. neighbors count: 100
        * Update method: Stream
    * Create a Vector Search Endpoint in the same region
    * Deploy the index to the endpoint
    * For more information about Vector Search check out the documentation [here](https://cloud.google.com/vertex-ai/docs/vector-search/create-manage-index)

6. **Set up a document OCR processor in Document AI**
    * Create a OCR processor in Document AI in the same region
    * [Documentation here](https://cloud.google.com/document-ai/docs/enterprise-document-ocr)

7. **Create a Firestore Database**
    * Set up a firestore database and collection in the same region in native mode
    * [Documentation here](https://firebase.google.com/docs/firestore/quickstart)

8. **Insert all variables into your .env file**

9. **Run `pip install -r requirements. txt` to install all packages in your local or virtual environment**

10. **Execute `streamlit run main.py` to run the Frontend Demo**
    
    
    




