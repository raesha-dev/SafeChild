# cosmos_db_integration.py
from azure.cosmos import CosmosClient
import os
from dotenv import load_dotenv
load_dotenv()


cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
cosmos_key = os.getenv("COSMOS_KEY")
client = CosmosClient(cosmos_endpoint, credential=cosmos_key)
database = client.get_database_client("SafeChildDB")
container = database.get_container_client("Reports")

def save_report_cosmos(phone, message, urgency, status, location, created_at):
    container.upsert_item({
        "id": f"{phone}_{created_at}",
        "phone": phone,
        "message": message,
        "urgency": urgency,
        "status": status,
        "location": location,
        "created_at": created_at.isoformat()
    })

# Call this from your savereport

