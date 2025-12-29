# SEO4AIEO & FUME Primitives

This repo now carries the baseline fields and event shapes for SEO/analytics without implementing connectors yet.

- DatasetEvent fields: `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `seo_slug`, `seo_title`, `seo_description`, `asset_alt_text`, `analytics_event_type`, `analytics_platform`.
- Analytics platforms: GA4, Meta, Snap, TikTok (and future connectors) map onto `analytics_platform`.
- Event types (suggested): `page_view`, `click`, `purchase`, `lead`, `signup`, `custom`.
- SEO helpers live in `engines/seo/helpers.py` with placeholder functions to be wired to LLM agents later.

Usage pattern (engine-side):
- When emitting a `DatasetEvent`, populate UTM/SEO/analytics fields from request metadata.
- PII is stripped by `engines.guardrails.pii_text`.
- Logging engine persists events through Nexus and emits structured logs; downstream connectors can subscribe and forward to GA4/Meta/etc.
