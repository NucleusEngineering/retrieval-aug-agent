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

from click import prompt
from dotenv import dotenv_values
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
#from langchain.llms import VertexAI
from langchain_community.llms import VertexAI
from vertexai.preview.generative_models import GenerativeModel, Part
from anthropic import AnthropicVertex

import base64

QA_PROMPT_TEMPLATE = """SYSTEM: You are an intelligent assistant helping to answer questions related to a given knowledge base and provided images. 
Question: {question}

-Strictly Use ONLY the following pieces of context or the provided image input to answer the question at the end. Think step-by-step and then answer.
Be specific in your answer and provide examples from the context.

=============
{context}
=============

Do not try to make up an answer:
 - If the answer to the question cannot be determined from the context or the provided image alone, say "I cannot determine the answer to that." and explain what information is missing to answer the question.
 - If the context is empty and there is no provided image, just say "I do not know the answer to that."

Question: {question}
Helpful & specific Answer:"""


class LLMSession:
    def __init__(self, client_query_string: str, context_docs, model_name: str, image):
        self.client_query_string = client_query_string
        self.context_docs = context_docs
        self.prompt_template = QA_PROMPT_TEMPLATE
        self.model_name = model_name
        self.secrets = dotenv_values(".env")
        if image is not None:
            self.image_data = Part.from_data(
                mime_type="image/png",
                data=image)
        else: 
            self.image_data = None
    def llm_prediction(
        self,
        max_output_tokens: int = 1024,
        temperature: float = 0.2,
        top_p: float = 0.8,
        top_k: int = 40,
    ) -> dict:
        if self.model_name == "gemini-1.0-pro":
            model = GenerativeModel("gemini-1.0-pro-002")
            responses = model.generate_content(
                self.prompt_template.format(
                    question=self.client_query_string, context=self.context_docs
                ),
                generation_config={
                    "max_output_tokens": 2048,
                    "temperature": 1,
                    "top_p": 1,
                },
            )
            response = {"text": responses.text}
        elif self.model_name == "gemini-1.5-pro":
            model = GenerativeModel("gemini-1.5-pro-001")
            if self.image_data is not None:
                responses = model.generate_content(
                    [self.image_data, self.prompt_template.format(
                        question=self.client_query_string, context=self.context_docs
                    )],
                    generation_config={
                        "max_output_tokens": 2048,
                        "temperature": 1,
                        "top_p": 1,
                    },
                )
                response = {"text": responses.text}
            else:
                responses = model.generate_content(
                    self.prompt_template.format(
                        question=self.client_query_string, context=self.context_docs
                    ),
                    generation_config={
                        "max_output_tokens": 2048,
                        "temperature": 1,
                        "top_p": 1,
                    },
                )
                response = {"text": responses.text}

        elif self.model_name == "gemini-1.5-flash":
            model = GenerativeModel("gemini-1.5-flash-001")
            if self.image_data is not None:
                responses = model.generate_content(
                    [self.image_data, self.prompt_template.format(
                        question=self.client_query_string, context=self.context_docs
                    )],
                    generation_config={
                        "max_output_tokens": 2048,
                        "temperature": 1,
                        "top_p": 1,
                    },
                )
                response = {"text": responses.text}
            else:
                responses = model.generate_content(
                    self.prompt_template.format(
                        question=self.client_query_string, context=self.context_docs
                    ),
                    generation_config={
                        "max_output_tokens": 2048,
                        "temperature": 1,
                        "top_p": 1,
                    },
                )
                response = {"text": responses.text}

        elif self.model_name == "claude3-sonnet":
            client = AnthropicVertex(region=str("us-central1"), project_id=str(self.secrets["GCP_PROJECT_ID"]))
            response = client.messages.create(
                model="claude-3-sonnet@20240229",
                max_tokens=max_output_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                messages=[
                    {
                        "role": "user",
                        "content": self.prompt_template.format(
                            question=self.client_query_string, context=self.context_docs
                        ),
                    }
                ],
            )
            return {"text": response.content[0].text}
        else:
            llm = VertexAI(
                model_name=self.model_name,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                verbose=True,
            )

            llm_chain = LLMChain(
                llm=llm, prompt=PromptTemplate.from_template(self.prompt_template)
            )

            response = llm_chain(
                {"question": self.client_query_string, "context": self.context_docs}
            )
        return response

    def llm_function_call(self, tools: list):
        model = GenerativeModel("gemini-pro")

        print("++++ Function Call Session Prompt ++++")
        print(self.client_query_string)

        model_response = model.generate_content(
            self.client_query_string, generation_config={"temperature": 0}, tools=tools
        )

        print(model_response)

        try:
            return model_response.text
        except:
            return self._extract_arguments_from_model_response(model_response)

    def _extract_arguments_from_model_response(self, model_response) -> dict:
        """
        Extract the raw function name and function calling arguments from the model response.
        """
        res = model_response.candidates[0].content.parts[0].function_call.args

        func_arguments = {
            "function_name": model_response.candidates[0]
            .content.parts[0]
            .function_call.name,
            "function_arguments": {i: res[i] for i in res},
        }

        return func_arguments


if __name__ == "__main__":
    prompt = "Which is the city with the most bridges?"
    llm = LLMSession(
        client_query_string=prompt, context_docs=None, model_name="claude3-sonnet"
    )
    response = llm.llm_prediction()
    print(response)
