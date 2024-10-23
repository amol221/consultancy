from twilio.rest import Client
import os

def send_whatsapp_notification(user_email, transaction_id):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=f"User {user_email} updated transaction ID: {transaction_id}",
        from_='whatsapp:+14155238886',  # Twilio sandbox number
        to='whatsapp:+1234567890'  # Admin's number
    )
    return message.sid

