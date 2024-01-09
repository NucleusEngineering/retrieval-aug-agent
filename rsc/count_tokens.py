project = "project-id"
location = "us-central1"
content = "Hello World!"

from google.cloud import aiplatform_v1beta1

client = aiplatform_v1beta1.PredictionServiceClient(
    client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
)

print(client.count_tokens(
    endpoint=f"projects/{project}/locations/{location}/publishers/google/models/text-bison@001",
    instances=[{"content": content}],
))