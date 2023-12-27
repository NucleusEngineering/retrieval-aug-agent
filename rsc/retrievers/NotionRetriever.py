import requests
from datetime import datetime, timezone
from dotenv import dotenv_values


class NotionRetrievalSession:
    def __init__(self,
                 chunk_size=1000,
                 chunk_overlap=50):
        
        self.secrets = dotenv_values(".env")
        self.notion_token = self.secrets['NOTION_TOKEN']
        self.notion_database_id = self.secrets["NOTION_DATABASE_ID"]
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def __call__(self):
       
        headers = {
            "Authorization": "Bearer " + self.notion_token,
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }   

        def get_pages(num_pages=None):
            """
            If num_pages is None, get all pages, otherwise just the defined number.
            """
            url = f"https://api.notion.com/v1/databases/{self.notion_database_id}/query"

            get_all = num_pages is None
            page_size = 100 if get_all else num_pages

            payload = {"page_size": page_size}
            response = requests.post(url, json=payload, headers=headers)

            data = response.json()

            results = data["results"]
            while data["has_more"] and get_all:
                payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
                url = f"https://api.notion.com/v1/databases/{self.notion_database_id}/query"
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
        for page in pages:
            page_content = []
            page_id = page["id"]
            props = page["properties"]
            #iterate through all properties within page to find content 
            for majorkey, subdict in props.items(): 
                key, value = find_key("rich_text", subdict)
                #check if array is empty in rich text
                if not value == None:
                    prop_content = value[0].get("text").get("content")
                    prop_content_with_key = majorkey + " : " + prop_content 
                    page_content.append(prop_content_with_key)
        
            database_content.append(page_content)
        print(database_content)
        return database_content


test = NotionRetrievalSession()
test()


#next steps:
# -chunk the notion strings



    