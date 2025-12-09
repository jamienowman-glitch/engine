"""Security feed ingestor for scanner outputs."""
from __future__ import annotations

from typing import Any, Dict, List

from engines.security.schemas import SecurityFinding, SecurityScanRun


class SecurityFeedIngestor:
    def __init__(self, ghas_client=None, semgrep_client=None, sonar_client=None):
        self._ghas_client = ghas_client
        self._semgrep_client = semgrep_client
        self._sonar_client = sonar_client

    def ingest_ghas(self, tenant_id: str, repo: str) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        if not self._ghas_client:
            return findings
        raw = self._ghas_client.list_findings(repo)
        for item in raw:
            findings.append(
                SecurityFinding(
                    id=item.get("id", ""),
                    tenant_id=tenant_id,
                    source="ghas",
                    severity=item.get("severity", "unknown"),
                    location=item.get("location", ""),
                    description=item.get("description", ""),
                    cwe=item.get("cwe"),
                    status=item.get("status", "open"),
                )
            )
        return findings

    def ingest_semgrep(self, tenant_id: str, repo: str) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        if not self._semgrep_client:
            return findings
        raw = self._semgrep_client.list_findings(repo)
        for item in raw:
            findings.append(
                SecurityFinding(
                    id=item.get("id", ""),
                    tenant_id=tenant_id,
                    source="semgrep",
                    severity=item.get("severity", "unknown"),
                    location=item.get("location", ""),
                    description=item.get("message", ""),
                    cwe=item.get("cwe"),
                    status=item.get("status", "open"),
                )
            )
        return findings

    def ingest_sonar(self, tenant_id: str, project_key: str) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        if not self._sonar_client:
            return findings
        raw = self._sonar_client.list_findings(project_key)
        for item in raw:
            findings.append(
                SecurityFinding(
                    id=item.get("key", ""),
                    tenant_id=tenant_id,
                    source="sonar",
                    severity=item.get("severity", "unknown"),
                    location=item.get("component", ""),
                    description=item.get("message", ""),
                    cwe=item.get("cwe"),
                    status=item.get("status", "open"),
                )
            )
        return findings

    def record_scan_run(self, source: str, repo_ref: str, findings_ref: str) -> SecurityScanRun:
        return SecurityScanRun(run_id=f"{source}-{repo_ref}", source=source, repo_ref=repo_ref, findings_ref=findings_ref)
