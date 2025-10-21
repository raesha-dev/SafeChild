# azure_comm_integration.py
import os
from azure.communication.messages import NotificationMessagesClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
load_dotenv()


# Set up credentials in your .env file:
# AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET, AZURE_COMM_ENDPOINT

client = NotificationMessagesClient(
    endpoint=os.getenv("AZURE_COMM_ENDPOINT"),
    credential=DefaultAzureCredential()
)

# Example SMS/WhatsApp send
def send_sms(to_number, message):
    response = client.send(
        to=to_number,
        message=message
    )
    return response

def receive_message_webhook(request):
    # Parse inbound message/webhook payload from Azure
    # Use request.json or equivalent if using Flask/Starlette, etc.
    data = request.json
    sender = data['from']
    text = data['message']
    # Forward to AI processing...
    return {"sender": sender, "text": text}
