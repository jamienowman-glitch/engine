from __future__ import annotations
import smtplib
import imaplib
import email
from email.message import EmailMessage
from email.mime.text import MIMEText
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class ReadEmailInput(BaseModel):
    limit: int = 10

class SendEmailInput(BaseModel):
    to_email: str
    subject: str
    body: str

# --- Connector Logic ---

def _get_credentials(ctx: RequestContext):
    secrets = LocalSecretStore()
    user = secrets.get_secret(f"email-user-{ctx.tenant_id}") or secrets.get_secret("email-user")
    password = secrets.get_secret(f"email-pass-{ctx.tenant_id}") or secrets.get_secret("email-pass")
    
    smtp_host = secrets.get_secret("smtp-host")
    smtp_port = int(secrets.get_secret("smtp-port") or 587)
    
    imap_host = secrets.get_secret("imap-host")
    
    if not user or not password or not smtp_host or not imap_host:
        raise ValueError("Missing Email Credentials/Config in secrets.")
        
    return user, password,CBV, smtp_host, smtp_port, imap_host

def _get_credentials_dict(ctx: RequestContext):
    secrets = LocalSecretStore()
    return {
        "user": secrets.get_secret(f"email-user-{ctx.tenant_id}") or secrets.get_secret("email-user"),
        "pass": secrets.get_secret(f"email-pass-{ctx.tenant_id}") or secrets.get_secret("email-pass"),
        "smtp_host": secrets.get_secret("smtp-host"),
        "smtp_port": int(secrets.get_secret("smtp-port") or 587),
        "imap_host": secrets.get_secret("imap-host")
    }

# --- Handlers ---

async def read_inbox(ctx: RequestContext, input_data: ReadEmailInput) -> List[Dict[str, Any]]:
    creds = _get_credentials_dict(ctx)
    
    # Standard IMAP SSL
    mail = imaplib.IMAP4_SSL(creds["imap_host"])
    mail.login(creds["user"], creds["pass"])
    mail.select("inbox")
    
    status, messages = mail.search(None, "UNSEEN")
    email_ids = messages[0].split()
    
    results = []
    # Fetch latest N
    for e_id in email_ids[-input_data.limit:]:
        status, msg_data = mail.fetch(e_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                results.append({
                    "subject": msg["subject"],
                    "from": msg["from"],
                    "date": msg["date"]
                })
    
    mail.logout()
    return results

async def send_email(ctx: RequestContext, input_data: SendEmailInput) -> Dict[str, str]:
    creds = _get_credentials_dict(ctx)
    
    msg = EmailMessage()
    msg.set_content(input_data.body)
    msg["Subject"] = input_data.subject
    msg["From"] = creds["user"]
    msg["To"] = input_data.to_email
    
    with smtplib.SMTP(creds["smtp_host"], creds["smtp_port"]) as server:
        server.starttls()
        server.login(creds["user"], creds["pass"])
        server.send_message(msg)
        
    return {"status": "sent", "to": input_data.to_email}

async def create_draft(ctx: RequestContext, input_data: SendEmailInput) -> Dict[str, str]:
    creds = _get_credentials_dict(ctx)
    
    msg = EmailMessage()
    msg.set_content(input_data.body)
    msg["Subject"] = input_data.subject
    msg["From"] = creds["user"]
    msg["To"] = input_data.to_email
    
    # Use IMAP Append to create draft
    mail = imaplib.IMAP4_SSL(creds["imap_host"])
    mail.login(creds["user"], creds["pass"])
    
    # Append to 'Drafts' folder with \Draft flag
    # Note: Folder name might vary (Drafts, [Gmail]/Drafts, etc.) - attempting standard 'Drafts'
    # In a robust app, we'd discover this.
    try:
        # Time is now
        date_time = imaplib.Time2Internaldate(time.time())
        mail.append('Drafts', '\\Draft', date_time, msg.as_bytes())
    except Exception as e:
        mail.logout()
        raise ValueError(f"Failed to create draft. Check folder name. Error: {e}")
        
    mail.logout()
    return {"status": "saved_draft", "folder": "Drafts"}
