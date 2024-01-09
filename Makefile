ifneq (,$(wildcard ./.env))
    include .env
    export
endif

config:
	gcloud config set project ${GCP_PROJECT_ID}
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

repo:
	gcloud artifacts repositories create retrieval-aug-agent \
		--repository-format docker

bucket:
	gcloud storage buckets create gs://${RAW_PDFS_BUCKET_NAME}

database:
	gcloud firestore databases create \
		--location ${GCP_MULTI_REGION}

build:
	gcloud builds submit . \
		--tag $$(gcloud config get-value artifacts/location)-docker.pkg.dev/retrieval-agent-demo/retrieval-aug-agent/image

deploy:
	gcloud run deploy retrieval-aug-agent \
		--image $$(gcloud config get-value artifacts/location)-docker.pkg.dev/retrieval-agent-demo/retrieval-aug-agent/image \
		--service-account retrieval-aug-agent@$$(gcloud config get-value project).iam.gserviceaccount.com \
		--allow-unauthenticated

all: config init service-account repo bucket database build deploy

.PHONY: config init service-account repo bucket database build deploy
