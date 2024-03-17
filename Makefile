ifneq (,$(wildcard ./.env))
    include .env
    export
endif

config:
	gcloud config set project ${GCP_PROJECT_ID}
	gcloud config set ai/region ${GCP_REGION}
	gcloud config set run/region ${GCP_REGION}
	gcloud config set artifacts/location ${GCP_REGION}

init:
	gcloud services enable {firestore,documentai,storage,aiplatform,compute,run,cloudbuild,artifactregistry}.googleapis.com

service-account:
	gcloud iam service-accounts create retrieval-aug-agent
	gcloud projects add-iam-policy-binding $$(gcloud config get-value project) \
		--member serviceAccount:retrieval-aug-agent@$$(gcloud config get-value project).iam.gserviceaccount.com \
		--role roles/aiplatform.user
	gcloud projects add-iam-policy-binding $$(gcloud config get-value project) \
		--member serviceAccount:retrieval-aug-agent@$$(gcloud config get-value project).iam.gserviceaccount.com \
		--role roles/datastore.user
	gcloud projects add-iam-policy-binding $$(gcloud config get-value project) \
		--member serviceAccount:retrieval-aug-agent@$$(gcloud config get-value project).iam.gserviceaccount.com \
		--role roles/storage.objectAdmin
	gcloud projects add-iam-policy-binding $$(gcloud config get-value project) \
		--member serviceAccount:retrieval-aug-agent@$$(gcloud config get-value project).iam.gserviceaccount.com \
		--role roles/documentai.editor

repo:
	gcloud artifacts repositories create retrieval-aug-agent \
		--repository-format docker

bucket:
	gcloud storage buckets create gs://${RAW_PDFS_BUCKET_NAME} \
		--location ${GCP_REGION}
	gsutil cp ./index_creation/null.json gs://${RAW_PDFS_BUCKET_NAME}/path/init.json

database:
	gcloud firestore databases create \
		--location ${GCP_MULTI_REGION}

index:
	gcloud alpha ai indexes create \
		--display-name retrieval-agent-index \
		--description "RAG DEMO: Brand name PDFs: 768d streaming update index on Vertex Vector Search" \
		--index-update-method stream_update \
		--metadata-file ./index_creation/index-metadata.json 

endpoint:
	gcloud alpha ai index-endpoints create \
		--display-name retrieval-agent-demo \
		--description "Endpoint for RAG-DEMO Vector Search index" \
		--public-endpoint-enabled
	gcloud alpha ai index-endpoints deploy-index $$(gcloud alpha ai index-endpoints list --format json | jq -r '.[].name' | grep --color=never -Po '\K(\d+)$$') \
		--deployed-index-id retrieval_aug_agent \
		--index $$(gcloud alpha ai indexes list --format json | jq -r '.[].name') \
		--display-name retrieval-aug-agent
	printf "\n\tINFO\tIndex is $$(gcloud alpha ai indexes list --format json | jq -r '.[].name' |  grep --color=never -Po '\K(\d+)$$')\n\n"
	printf "\n\tINFO\tEndpoint is $$(gcloud alpha ai index-endpoints list --format json | jq -r '.[].name' | grep -Po '\K(\d+)$$')\n\n"

build:
	gcloud builds submit . \
		--tag $$(gcloud config get-value artifacts/location)-docker.pkg.dev/retrieval-agent-demo/retrieval-aug-agent/image

deploy:
	gcloud run deploy retrieval-aug-agent \
		--image $$(gcloud config get-value artifacts/location)-docker.pkg.dev/retrieval-agent-demo/retrieval-aug-agent/image \
		--service-account retrieval-aug-agent@$$(gcloud config get-value project).iam.gserviceaccount.com \
		--allow-unauthenticated

all: config init service-account repo bucket database index endpoint build deploy

.PHONY: config init service-account repo bucket database index endpoint build deploy
