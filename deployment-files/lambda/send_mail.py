import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def lambda_handler(event, context):
    # Gmail SMTP server details
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # Sender email credentials (use environment variables for security)
    sender_email = os.environ['GMAIL_ADDRESS']
    sender_password = os.environ['GMAIL_PASSWORD']

    body = json.loads(event.get('body'))

    # Email content
    recipient_email = body.get('recipient_email')
    subject = body.get('subject')
    body = body.get('mail_body')

    # Create email
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the Gmail SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Upgrade the connection to secure
        server.login(sender_email, sender_password)  # Log in to Gmail
        server.sendmail(sender_email, recipient_email, message.as_string())  # Send email
        server.quit()  # Close the connection

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({
                'message': f"Email sent successfully to {recipient_email}"
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({
                'message': f"Failed to send email: {str(e)}",
                'event': event
            })
        }
