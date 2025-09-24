# azure_comm_integration.py
import os
from azure.communication.messages import NotificationMessagesClient
from azure.communication.callautomation import CallAutomationClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

# Set up the SMS client
sms_client = NotificationMessagesClient(
    endpoint=os.getenv("AZURE_COMM_ENDPOINT"),
    credential=DefaultAzureCredential()
)

# Set up the Call Automation client
call_client = CallAutomationClient.from_connection_string(
    os.getenv("AZURE_COMM_CONNECTION_STRING")
)

def send_sms(to_number, message):
    """
    Send SMS using Azure Communication Services NotificationMessagesClient.
    Parameters:
        to_number (str): Destination phone number in E.164 format (e.g., +1234567890)
        message (str): SMS message content
    Returns:
        response: The response object from the client.send() call
    """
    try:
        response = sms_client.send(
            to=to_number,
            message=message
        )
        return response
    except Exception as e:
        print(f"SMS send failed: {e}")
        return None

def start_call(source_identity, target_number, callback_url):
    """
    Initiate a call using Azure Communication Services CallAutomationClient.
    Parameters:
        source_identity (str): Azure Communication user ID string (e.g., "8:acs:userid")
        target_number (str): Phone number to call in E.164 format (e.g., +1234567890)
        callback_url (str): Publicly accessible webhook URL for call lifecycle events
    Returns:
        call_response: Response from the create_call() or None if failed
    """
    try:
        call_response = call_client.create_call(
            source={"communicationUser": {"id": source_identity}},
            targets=[{"phoneNumber": target_number}],
            callback_url=callback_url
        )
        return call_response
    except Exception as e:
        print(f"Call initiation failed: {e}")
        return None

def receive_message_webhook(request):
    """
    Process inbound SMS/WhatsApp webhook from Azure.
    Adjust this handler based on your actual web framework being used.
    """
    data = request.json
    sender = data.get('from', '')
    text = data.get('message', '')
    return {"sender": sender, "text": text}
