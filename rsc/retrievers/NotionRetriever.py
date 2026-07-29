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

import requests
from dotenv import dotenv_values
from notion.client import NotionClient

class NotionRetrievalSession:
    def __init__(self,
                 chunk_size=1000,
                 chunk_overlap=50):
        
        self.secrets = dotenv_values(".env")
        self.notion_token = self.secrets['NOTION_TOKEN']
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.notion_base_api_url = "https://api.notion.com/v1"
        self.headers = headers = {
            "Authorization": "Bearer " + self.notion_token,
            "Content-Type": "application/json",
            "Notion-Version": "2022-02-22"
        }

    def __call__(self, database_id: str):
       
        headers = {
            "Authorization": "Bearer " + self.notion_token,
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }   

        def get_pages(num_pages=None):
            """
            If num_pages is None, get all pages, otherwise just the defined number.
            """
            url = f"https://api.notion.com/v1/databases/{database_id}/query"

            get_all = num_pages is None
            page_size = 100 if get_all else num_pages

            payload = {"page_size": page_size}
            response = requests.post(url, json=payload, headers=headers)

            data = response.json()

            results = data["results"]
            while data["has_more"] and get_all:
                payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
                url = f"https://api.notion.com/v1/databases/{database_id}/query"
                response = requests.post(url, json=payload, headers=headers)
                data = response.json()
                results.extend(data["results"])

            return results

        pages = get_pages()

        def find_key(key, dictionary):
            value = dictionary.get(key)
            if value is not None:
                return key, value
            for child_key, child_value in dictionary.items():
                if isinstance(child_value, dict):
                    sub_key, sub_value = find_key(key, child_value)
                    if sub_key:
                        return f"{child_key}.{sub_key}", sub_value
            return None, None

        #iterate through all Notion pages within database 
        database_content = []
        database_pages = []
        for page in pages:
            page_content = []
            page_title = []
            #page_id = page["id"]
            props = page["properties"]
            #iterate through all properties within page to find content 

            #content from text fields:
            for majorkey, subdict in props.items(): 
                key, value = find_key("rich_text", subdict)
                #check if array is empty in rich text
                if not value == None:
                    prop_content = value[0].get("text").get("content")
                    prop_content_with_key = majorkey + " : " + prop_content 
                    page_content.append(prop_content_with_key)

            #content from title fields
            for majorkey, subdict in props.items(): 
                key, value = find_key("title", subdict)
                #check if array is empty in rich text
                if not value == None:
                    prop_content = value[0].get("text").get("content")
                    prop_content_with_key = majorkey + " : " + prop_content 
                    page_content.append(prop_content_with_key)
                    page_title = prop_content 

            #content from select fields
            for majorkey, subdict in props.items(): 
                key, value = find_key("select", subdict)
                #check if array is empty in rich text
                if not value == None:
                    prop_content = value.get("name")
                    prop_content_with_key = majorkey + " : " + prop_content 
                    page_content.append(prop_content_with_key)

            database_content.append(page_content)
            database_pages.append(page_title)
        return database_content, database_pages
    
    def _check_db_connection(self, database_id: str) -> None:
        headers = {
            "Authorization": "Bearer " + self.notion_token,
            "Content-Type": "application/json",
            "Notion-Version": "2022-02-22"
        }

        readUrl=f"https://api.notion.com/v1/databases/{database_id}"
        res=requests.request("GET",readUrl,headers=headers)
        print(res)
        return None
    
    def _get_all_dbs(self) -> None:
        # Replace with your actual API key
        search_endpoint = f"{self.notion_base_api_url}/search"

        headers = {
            "Authorization": "Bearer " + self.notion_token,
            "Content-Type": "application/json",
            "Notion-Version": "2022-02-22"
        }

        payload = {
            "filter": {"value": "page", "property": "object"}
        }

        response = requests.post(search_endpoint, headers=headers, json=payload)

        print(response)

        if response.status_code == 200:
            data = response.json()
            database_ids = [result['id'] for result in data['results']]
            print(database_ids)
        else:
            print("Error in search:", response.text)
        return None

    def _retrieve_page(self, page_id: str) -> None:
        retrieve_page_endpoint = f"{self.notion_base_api_url}/pages/{page_id}"
        response = requests.get(retrieve_page_endpoint, headers=self.headers)

        if response.status_code == 200:
            page_data = response.json()
            print(page_data)
        else:
            print(f"Error fetching page: {response.status_code}, Response text: {response.text}")

        return None

if __name__ == "__main__":
    notion_ret = NotionRetrievalSession()
    # notion_ret(database_id="5604e108753649fab53d445740577961")
    # notion_ret._check_db_connection(database_id="322b60a0f2b849d38737283a43962ad2")
    # notion_ret._get_all_dbs()

    notion_ret._retrieve_page(page_id="f56de35561834507bb730c0c80686395")

    print("Hello World!")