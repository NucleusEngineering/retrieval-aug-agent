from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import VertexAI

QA_PROMPT_TEMPLATE =  """SYSTEM: You are an intelligent assistant helping the users with their questions on the content of given context.

Question: {question}

Strictly Use ONLY the following pieces of context to answer the question at the end. Think step-by-step and then answer.
Be specific in your answer and provide examples from the context.

Do not try to make up an answer:
 - If the answer to the question cannot be determined from the context alone, say "I cannot determine the answer to that." and explain what information is missing to answer the question.
 - If the context is empty, just say "I do not know the answer to that."

=============
{context}
=============

Do not try to make up an answer:
 - If the answer to the question cannot be determined from the context alone, say "I cannot determine the answer to that." and explain what information is missing to answer the question.
 - If the context is empty, just say "I do not know the answer to that."

Question: {question}
Helpful & specific Answer:"""


class LLMSession:
    def __init__(self, client_query_string, context_docs):
        self.client_query_string = client_query_string
        self.context_docs = context_docs
        self.prompt_template = QA_PROMPT_TEMPLATE
    
    def llm_prediction(self,
                       max_output_tokens:int=1024,
                       temperature:float=0.2,
                       top_p:float=0.8, top_k:int=40) -> str:

        llm = VertexAI(model_name="text-bison@001",
                       max_output_tokens=max_output_tokens,
                       temperature=temperature,
                       top_p=top_p,
                       top_k=top_k,
                       verbose=True
                       )

        llm_chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(self.prompt_template))

        response = llm_chain({"question":self.client_query_string, "context":self.context_docs})
        return response