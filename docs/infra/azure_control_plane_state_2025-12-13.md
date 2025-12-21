# Azure Control-Plane Foundation — Northstar (State as of 2025-12-13)

## Identity / CLI
- Operator auth: Azure CLI interactive login (`az login`)
- Azure CLI version: 2.81.0
- Azure CLI config dir: /Users/jaynowman/.azure
- Cloud: AzureCloud

## Tenant
- Tenant display name: Default Directory
- Tenant ID: 532fccc4-7f99-401d-b680-58ebf453877a
- Tenant default domain: jamienowmangmail.onmicrosoft.com

## Subscription
- Subscription name: Azure subscription 1
- Subscription ID: 64cce95c-7395-41e4-87c4-0141783036b9
- State: Enabled
- Default subscription: True

## Defaults
- Default location: centralus
- Source: /Users/jaynowman/.azure/config

## Management Groups (created)
- mg-northstar (display: Northstar)
  - mg-platform (display: Platform)
  - mg-landingzones (display: Landing Zones)

## Resource Groups (created; all centralus)
Platform RGs:
- rg-platform-net
- rg-platform-sec
- rg-platform-mgmt

Landing Zone RGs:
- rg-lz-prod
- rg-lz-nonprod
- rg-lz-sandbox

## Resource Providers (Registered)
- Microsoft.CognitiveServices
- Microsoft.MachineLearningServices
- Microsoft.Storage
- Microsoft.KeyVault
- Microsoft.Network
- Microsoft.Authorization
- Microsoft.ManagedIdentity
- Microsoft.OperationsManagement
- Microsoft.Insights
- Microsoft.ContainerService
- Microsoft.App
- Microsoft.Search

## Safety rails

### RG Locks (CanNotDelete)
- rg-platform-net: lock-rg-platform-net-cannotdelete
- rg-platform-sec: lock-rg-platform-sec-cannotdelete
- rg-platform-mgmt: lock-rg-platform-mgmt-cannotdelete

### Cost Budget (Monthly)
- Budget name: ns-monthly
- Scope: subscription 64cce95c-7395-41e4-87c4-0141783036b9
- Amount: 200
- Category: Cost
- Time grain: Monthly
- Time period: 2025-12-01T00:00:00Z → 2035-12-01T00:00:00Z
- Notifications (email: jamienowman@gmail.com):
  - Actual: 50%, 80%, 90%, 100%
  - Forecasted: 90%

Notes:
- Azure CLI `az consumption budget create-with-rg` rejected the notifications schema (thresholdType) in this CLI build.
- REST is canonical for budgets:
  - GET/PUT: /providers/Microsoft.Consumption/budgets/ns-monthly?api-version=2024-08-01

## Non-human identities (“agent accounts”)
- None created yet (by design).
- Future pattern:
  - Agents in Azure: Managed Identity
  - Agents in CI: OIDC federation
  - Agents off-Azure: service principal only if required
