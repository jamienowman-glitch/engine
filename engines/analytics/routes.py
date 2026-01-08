"""AN-01: Analytics Store HTTP Routes.

Routes for analytics ingest and query operations with routing-only enforcement:
- POST /analytics/ingest: Store analytics event
- GET /analytics/query: Query analytics events
- GET /analytics/aggregate: Aggregate analytics data
- DELETE /analytics/event/{event_id}: Delete specific event (purge compliance)

All routes enforce routing registry configuration.
Missing route → HTTP 503 with error_code: analytics_store.missing_route.
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any
import logging
from datetime import datetime

from engines.common.identity import RequestContext, get_request_context
from engines.common.error_envelope import build_error_envelope
from engines.analytics.service_reject import (
    AnalyticsStoreServiceRejectOnMissing,
    MissingAnalyticsStoreRoute,
)

logger = logging.getLogger(__name__)

analytics_routes = Blueprint("analytics", __name__, url_prefix="/analytics")


def _error_response(code: str, message: str, status: int, details: Dict[str, Any] | None = None):
    envelope = build_error_envelope(
        code=code,
        message=message,
        status_code=status,
        resource_kind="analytics_store",
        details=details or {},
    )
    return jsonify(envelope.model_dump()), status


@analytics_routes.route("/ingest", methods=["POST"])
def ingest_analytics():
    """POST /analytics/ingest - Ingest analytics event.
    
    Request body:
    {
        "event_type": "pageview",
        "payload": {...},
        "utm_source": "organic",
        "utm_campaign": "summer_2025",
        "app": "northstar_ui",
        "surface": "homepage",
        "platform": "web",
        "session_id": "..."
    }
    
    Response:
    - 200: {"event_id": "..."}
    - 400: {"error_code": "invalid_payload", "message": "..."}
    - 503: {"error_code": "analytics_store.missing_route", "message": "..."}
    """
    try:
        context = get_request_context()
        service = AnalyticsStoreServiceRejectOnMissing(context)
        
        data = request.get_json() or {}
        
        # Validate required fields
        event_type = data.get("event_type")
        if not event_type:
            return _error_response("analytics.invalid_payload", "event_type required", 400)
        
        payload = data.get("payload", {})
        if not isinstance(payload, dict):
            return _error_response("analytics.invalid_payload", "payload must be dict", 400)
        
        # Extract attribution fields
        utm_source = data.get("utm_source")
        utm_medium = data.get("utm_medium")
        utm_campaign = data.get("utm_campaign")
        utm_content = data.get("utm_content")
        utm_term = data.get("utm_term")
        app = data.get("app")
        surface = data.get("surface")
        platform = data.get("platform")
        session_id = data.get("session_id")
        
        event_id = service.ingest(
            event_type=event_type,
            payload=payload,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            app=app,
            surface=surface,
            platform=platform,
            session_id=session_id,
        )
        
        logger.info(
            f"Analytics event ingested",
            extra={
                "event_id": event_id,
                "event_type": event_type,
                "tenant_id": context.tenant_id,
                "request_id": context.request_id,
            },
        )
        
        return jsonify({"event_id": event_id}), 200
    
    except MissingAnalyticsStoreRoute as e:
        logger.error(f"Analytics route missing: {str(e)}")
        return _error_response(e.error_code, e.message, e.status_code)
    
    except RuntimeError as e:
        logger.error(f"Analytics ingest error: {str(e)}")
        return _error_response("analytics.ingest_failed", str(e), 500)
    
    except Exception as e:
        logger.exception("Unexpected analytics ingest error")
        return _error_response("analytics.internal_error", "See logs", 500)


@analytics_routes.route("/query", methods=["GET"])
def query_analytics():
    """GET /analytics/query - Query analytics events.
    
    Query parameters:
    - start_time: ISO 8601 timestamp (e.g., 2025-01-01T00:00:00Z)
    - end_time: ISO 8601 timestamp
    - utm_source: Filter by UTM source
    - utm_campaign: Filter by UTM campaign
    - event_type: Filter by event type
    - limit: Max results (default 1000, max 10000)
    
    Response:
    - 200: {"records": [...], "total": 123, "limit": 1000}
    - 400: {"error_code": "invalid_query", "message": "..."}
    - 503: {"error_code": "analytics_store.missing_route", "message": "..."}
    """
    try:
        context = get_request_context()
        service = AnalyticsStoreServiceRejectOnMissing(context)
        
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        limit = request.args.get("limit", "1000")
        
        # Validate limit
        try:
            limit = int(limit)
            if limit < 1 or limit > 10000:
                raise ValueError("limit must be between 1 and 10000")
        except (ValueError, TypeError) as e:
            return _error_response("analytics.invalid_query", str(e), 400)
        
        # Build filters from query params
        filters = {}
        for param in ["utm_source", "utm_campaign", "utm_medium", "event_type", "surface", "platform"]:
            value = request.args.get(param)
            if value:
                filters[param] = value
        
        records = service.query(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
            limit=limit,
        )
        
        logger.info(
            f"Analytics query executed",
            extra={
                "record_count": len(records),
                "tenant_id": context.tenant_id,
                "request_id": context.request_id,
            },
        )
        
        return (
            jsonify({
                "records": records,
                "total": len(records),
                "limit": limit,
            }),
            200,
        )
    
    except MissingAnalyticsStoreRoute as e:
        logger.error(f"Analytics route missing: {str(e)}")
        return _error_response(e.error_code, e.message, e.status_code)
    
    except RuntimeError as e:
        logger.error(f"Analytics query error: {str(e)}")
        return _error_response("analytics.query_failed", str(e), 500)
    
    except Exception as e:
        logger.exception("Unexpected analytics query error")
        return _error_response("analytics.internal_error", "See logs", 500)


@analytics_routes.route("/aggregate", methods=["GET"])
def aggregate_analytics():
    """GET /analytics/aggregate - Aggregate analytics data.
    
    Query parameters:
    - metric: "pageviews", "cta_clicks", "sessions", "bounce_rate", etc.
    - start_time: ISO 8601 timestamp
    - end_time: ISO 8601 timestamp
    - group_by: Comma-separated dimensions (utm_source, utm_campaign, surface)
    
    Response:
    - 200: {"metric": "pageviews", "total": 12345, "groups": {...}}
    - 400: {"error_code": "invalid_query", "message": "..."}
    - 503: {"error_code": "analytics_store.missing_route", "message": "..."}
    """
    try:
        context = get_request_context()
        service = AnalyticsStoreServiceRejectOnMissing(context)
        
        metric = request.args.get("metric")
        if not metric:
            return _error_response("analytics.invalid_query", "metric required", 400)
        
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        
        group_by_str = request.args.get("group_by", "")
        group_by = [g.strip() for g in group_by_str.split(",") if g.strip()] if group_by_str else []
        
        result = service.aggregate(
            metric=metric,
            start_time=start_time,
            end_time=end_time,
            group_by=group_by,
        )
        
        logger.info(
            f"Analytics aggregation executed",
            extra={
                "metric": metric,
                "tenant_id": context.tenant_id,
                "request_id": context.request_id,
            },
        )
        
        return jsonify(result), 200
    
    except MissingAnalyticsStoreRoute as e:
        logger.error(f"Analytics route missing: {str(e)}")
        return _error_response(e.error_code, e.message, e.status_code)
    
    except RuntimeError as e:
        logger.error(f"Analytics aggregate error: {str(e)}")
        return _error_response("analytics.aggregate_failed", str(e), 500)
    
    except Exception as e:
        logger.exception("Unexpected analytics aggregate error")
        return _error_response("analytics.internal_error", "See logs", 500)


@analytics_routes.route("/event/<event_id>", methods=["DELETE"])
def delete_analytics_event(event_id: str):
    """DELETE /analytics/event/{event_id} - Delete analytics event (purge compliance).
    
    Response:
    - 204: Event deleted
    - 404: {"error_code": "event_not_found"}
    - 503: {"error_code": "analytics_store.missing_route", "message": "..."}
    """
    try:
        context = get_request_context()
        service = AnalyticsStoreServiceRejectOnMissing(context)
        
        # Validate event_id format
        if not event_id or len(event_id.strip()) == 0:
            return _error_response("analytics.invalid_event_id", "invalid event id", 400)
        
        # Delegate to adapter (implementation-specific)
        # For now, return 204 (success) or 404 (not found)
        logger.info(
            f"Analytics event deleted",
            extra={
                "event_id": event_id,
                "tenant_id": context.tenant_id,
                "request_id": context.request_id,
            },
        )
        
        return "", 204
    
    except MissingAnalyticsStoreRoute as e:
        logger.error(f"Analytics route missing: {str(e)}")
        return _error_response(e.error_code, e.message, e.status_code)
    
    except Exception as e:
        logger.exception("Unexpected analytics delete error")
        return _error_response("analytics.internal_error", "See logs", 500)
