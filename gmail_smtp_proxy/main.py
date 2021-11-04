import asyncore
import typing
import json
import base64
import requests
import logging
import re
from __future__ import print_function
from smtpd import SMTPServer
from email.parser import BytesHeaderParser as EmailHeaderParser

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient import errors


logger = logging.getLogger(__name__)

GCP_API_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
SUBJECT="arthur@extrality.ai"
SENDER_EMAILS=["no-reply@extrality.ai"]
SERVICE_ACCOUNT_FILE = "service_account.json"

FROM_EMAIL_REGEX = re.compile(r"^[^<]+ <(.+)>$")

def check_creds(creds):
    creds.refresh(Request())
    conn_info = requests.get(f"https://oauth2.googleapis.com/tokeninfo?access_token={creds.token}").json()
    logger.info("Successful login:", conn_info)


class ProxyServer(SMTPServer):
    def __init__(self, *args, **kwargs):
        with open(SERVICE_ACCOUNT_FILE) as f:
            info = json.load(f)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=GCP_API_SCOPES,
            subject=SUBJECT
        )
        check_creds(creds)
        self.gmail_service = build('gmail', 'v1', credentials=creds)

        super().__init__(*args, **kwargs)
        logging.info("Ready to serve")


    def process_message(
        self,
        peer: typing.Tuple[str, int, int],
        mailfrom: str,
        rcpttos: typing.List[str],
        data: bytes,
        **kwargs
    ):
        from_header = EmailHeaderParser().parsebytes(data).get("From")

        from_email = FROM_EMAIL_REGEX.match(from_header).group(1)
        assert from_email in SENDER_EMAILS, f"Not allowed to SendAs {from_email}"

        gmail_mgs = {'raw': base64.urlsafe_b64encode(data).decode("utf-8")}
        try:
            self.gmail_service.users().messages().send(
                # requires settings -> send email as -> Add another email address
                userId="me",
                body=gmail_mgs
            ).execute()
        except errors.HttpError as e:
            logger.error(f"Error sending message: {e}")



def main():
    server = ProxyServer(
        ("localhost", 25),
        None
    )
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
