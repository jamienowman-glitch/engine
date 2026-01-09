import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.ga4.impl import run_report, RunGA4ReportInput

def test_ga4_flow():
    import asyncio
    asyncio.run(_async_test_ga4_flow())

async def _async_test_ga4_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.ga4.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.side_effect = lambda k: "98765" if "property-id" in k else "ga_token"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = {"rows": [{"metricValues": [{"value": "100"}]}]}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await run_report(ctx, RunGA4ReportInput(
            date_ranges=[{"startDate": "30daysAgo", "endDate": "today"}],
            metrics=[{"name": "activeUsers"}]
        ))
        
        # Verify Headers
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer ga_token"
        assert call_kwargs["base_url"] == "https://analyticsdata.googleapis.com/v1beta"
        
        # Verify Payload
        mock_client_instance.post.assert_called_with("/properties/98765:runReport", json={
            "dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
            "dimensions": [],
            "metrics": [{"name": "activeUsers"}]
        })
        
        # Verify Result
        assert result["rows"][0]["metricValues"][0]["value"] == "100"
