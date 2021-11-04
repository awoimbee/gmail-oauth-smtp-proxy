from __future__ import print_function
from smtpd import SMTPServer
from email.parser import BytesHeaderParser as EmailHeaderParser
from os import PathLike
from typing import List
import asyncore
import argparse
import base64
import requests
import logging
import re

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient import errors


logger = logging.getLogger(__name__)

GCP_API_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
FROM_EMAIL_REGEX = re.compile(r"^[^<]+ <(.+)>$")


def check_creds(creds):
    creds.refresh(Request())
    conn_info = requests.get(
        f"https://oauth2.googleapis.com/tokeninfo?access_token={creds.token}"
    ).json()
    logger.info("Successful login:", conn_info)


class ProxyServer(SMTPServer):
    def __init__(
        self,
        service_account_file: PathLike,
        sender_emails: List[str],
        subject: str,
        **kwargs,
    ):
        logger.info(f"Running on {kwargs['localaddr']}")
        kwargs.setdefault("remoteaddr", None)
        creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=GCP_API_SCOPES, subject=subject
        )
        check_creds(creds)

        self.sender_emails = sender_emails
        self.gmail_service = build("gmail", "v1", credentials=creds)

        super().__init__(**kwargs)
        logging.info("Ready to serve")

    def process_message(self, peer, mailfrom, rcpttos, data: bytes, **kwargs):
        from_header = EmailHeaderParser().parsebytes(data).get("From")
        reg_match = FROM_EMAIL_REGEX.match(from_header)
        if reg_match is None:
            raise ValueError(f"Invalid From header: {from_header}")
        from_email = reg_match.group(1)
        if from_email not in self.sender_emails:
            raise RuntimeError(
                f"Not allowed to SendAs '{from_email}' (available: {self.sender_emails})"
            )
        gmail_msg = {"raw": base64.urlsafe_b64encode(data).decode("utf-8")}
        try:
            self.gmail_service.users().messages().send(
                userId="me",
                body=gmail_msg,
            ).execute()
        except errors.HttpError as e:
            logger.error(f"Error sending message: {e}")
        logger.info(f"Email sent")


def main(args: argparse.Namespace):
    loglevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=loglevel)

    ProxyServer(
        localaddr=(args.host, args.port),
        service_account_file=args.service_account_file,
        sender_emails=args.sender_emails,
        subject=args.subject,
    )
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Proxies SMTP emails to gmail oauth API"
    )
    # Ports less than 1024 require root privileges:
    ap.add_argument("--port", "-p", type=int, default=2525)
    ap.add_argument("--host", "-H", default="0.0.0.0")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument(
        "--subject",
        "-u",
        required=True,
        type=str,
        # gmail -> settings -> send email as -> Add another email address
        help="The user to impersonate. This user should be able to SendAs every address in sender-emails",
    )
    ap.add_argument("--sender-emails", "-e", required=True,
    help="A list of email addresses that we are allowed to SendAs")
    ap.add_argument(
        "--service-account-file",
        "-f",
        required=True,
    )
    args = ap.parse_args()
    main(args)
