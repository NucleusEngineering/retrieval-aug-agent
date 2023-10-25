import vertexai
from vertexai.language_models import TextEmbeddingModel

import google.auth

from dotenv import dotenv_values

class EmbeddingSession:
    def __init__(self):
        self.secrets = dotenv_values(".env")
        self.credentials, self.project_id = google.auth.load_credentials_from_file(self.secrets['GCP_CREDENTIAL_FILE'])
        vertexai.init(project=self.secrets["GCP_PROJECT_ID"], credentials=self.credentials)
        return None

    def get_vertex_embedding(self, text_to_embed:str) -> list:
        """
        Get the embedding for a given text.

        Args:
            text_to_embed (str): The text to embed.

        Returns:
            list: Array containing embedding dimensions.
        """

        model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
        embedding = model.get_embeddings([text_to_embed])
        return embedding[0].values
    

if __name__ == "__main__":
    embedding = EmbeddingSession().get_vertex_embedding(text_to_embed="Hello World!")
    print(embedding)
    print("Hello World!")