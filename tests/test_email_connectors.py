import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.email_universal.impl import send_email as uni_send
from engines.connectors.email_universal.impl import create_draft as uni_draft
from engines.connectors.email_universal.impl import SendEmailInput as UniInput
from engines.connectors.microsoft_365.impl import create_draft as m365_draft
from engines.connectors.microsoft_365.impl import SendMicrosoftEmailInput as M365Input
from engines.connectors.gmail.impl import create_draft as gmail_draft
from engines.connectors.gmail.impl import SendGmailInput as GmailInput

def test_email_worker_flow():
    import asyncio
    asyncio.run(_async_test_email_worker_flow())

async def _async_test_email_worker_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    # --- Universal (SMTP/IMAP) ---
    with patch("engines.connectors.email_universal.impl.LocalSecretStore") as MockStore, \
         patch("smtplib.SMTP") as MockSMTP, \
         patch("imaplib.IMAP4_SSL") as MockIMAP:
        
        def get_secret_side_effect(key):
            if "port" in key:
                return "587"
            return "secret"
        MockStore.return_value.get_secret.side_effect = get_secret_side_effect
        
        # Test Send
        mock_smtp = MagicMock()
        MockSMTP.return_value.__enter__.return_value = mock_smtp
        await uni_send(ctx, UniInput(to_email="test@test.com", subject="Hi", body="Body"))
        mock_smtp.send_message.assert_called()
        
        # Test Draft
        mock_imap = MagicMock()
        MockIMAP.return_value = mock_imap
        await uni_draft(ctx, UniInput(to_email="test@test.com", subject="Draft", body="Body"))
        mock_imap.append.assert_called() # Check if append was called on 'Drafts'

    # --- Microsoft 365 ---
    with patch("engines.connectors.microsoft_365.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        MockStore.return_value.get_secret.return_value = "m365_tok"
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "draft_id_123"}
        mock_response.raise_for_status.return_value = None
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        MockClient.return_value = mock_client
        
        result = await m365_draft(ctx, M365Input(to_email="test@o365.com", subject="Sub", body="Body"))
        assert result["id"] == "draft_id_123"
        mock_client.post.assert_called()

    # --- Gmail ---
    with patch("engines.connectors.gmail.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        MockStore.return_value.get_secret.return_value = "gmail_tok"
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "g_draft_123"}
        mock_response.raise_for_status.return_value = None
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        MockClient.return_value = mock_client
        
        result = await gmail_draft(ctx, GmailInput(to_email="test@gmail.com", subject="GSub", body="GBody"))
        assert result["id"] == "g_draft_123"
        # Verify call structure (checking raw base64 presence)
        args, kwargs = mock_client.post.call_args
        assert kwargs["json"]["message"]["raw"] is not None
