from vertexai.language_models import TextEmbeddingModel

class EmbeddingSession:
    def __init__(self):
        pass

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