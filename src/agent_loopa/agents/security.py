"""Security Agent — OWASP Top 10 scan."""

from __future__ import annotations

from agent_loopa.agents.base import BaseAgent
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.models.verdicts import SecurityFinding, SecurityReport, SecuritySeverity, VerdictStatus

_OWASP_CATEGORIES = [
    "A01:2021-Broken Access Control",
    "A02:2021-Cryptographic Failures",
    "A03:2021-Injection",
    "A04:2021-Insecure Design",
    "A05:2021-Security Misconfiguration",
    "A06:2021-Vulnerable and Outdated Components",
    "A07:2021-Identification and Authentication Failures",
    "A08:2021-Software and Data Integrity Failures",
    "A09:2021-Security Logging and Monitoring Failures",
    "A10:2021-Server-Side Request Forgery",
]


class SecurityAgent(BaseAgent):
    name = "security"

    def _default_system_prompt(self) -> str:
        return (
            "You are a security engineer specializing in application security. "
            "Audit the provided code against the OWASP Top 10 (2021) and common CWEs. "
            "Look for: injection vulnerabilities, insecure deserialization, hardcoded secrets, "
            "path traversal, command injection, SQL injection, XSS, SSRF, broken auth, "
            "insecure cryptography, and improper error handling.\n\n"
            "Respond with valid JSON in exactly this format:\n"
            "{\n"
            '  "status": "pass" | "fail",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "findings": [\n'
            '    {\n'
            '      "severity": "critical" | "high" | "medium" | "low" | "info",\n'
            '      "owasp_category": "A01:2021-...",\n'
            '      "description": "...",\n'
            '      "location": "function_name or line hint",\n'
            '      "recommendation": "..."\n'
            '    }\n'
            "  ],\n"
            '  "owasp_categories_checked": ["A01:2021-...", ...],\n'
            '  "summary": "..."\n'
            "}\n\n"
            "status is 'pass' if there are no critical or high severity findings."
        )

    async def run(self, input: AgentInput) -> AgentOutput:
        if not input.code:
            return AgentOutput(
                agent_name=self.name,
                iteration=input.iteration,
                security_report=SecurityReport(
                    status=VerdictStatus.WARNING,
                    confidence=0.5,
                    summary="No code provided for security scan.",
                ),
            )

        prompt = (
            f"Perform a security audit of this {input.language} code:\n\n"
            f"```{input.language}\n{input.code.content}\n```\n\n"
            f"Check against all OWASP Top 10 (2021) categories:\n"
            + "\n".join(f"- {c}" for c in _OWASP_CATEGORIES)
            + "\n\nRespond with JSON only."
        )
        raw, tokens = await self._call_llm(prompt)
        data = self._parse_json_response(raw)

        findings = []
        for f in data.get("findings", []):
            try:
                severity = SecuritySeverity(f.get("severity", "info").lower())
            except ValueError:
                severity = SecuritySeverity.INFO
            findings.append(
                SecurityFinding(
                    severity=severity,
                    owasp_category=f.get("owasp_category", ""),
                    description=f.get("description", ""),
                    location=f.get("location", ""),
                    recommendation=f.get("recommendation", ""),
                )
            )

        status_str = data.get("status", "pass").lower()
        # Auto-fail if any critical/high findings
        has_critical = any(
            f.severity in (SecuritySeverity.CRITICAL, SecuritySeverity.HIGH) for f in findings
        )
        if has_critical:
            status_str = "fail"

        report = SecurityReport(
            status=VerdictStatus.PASS if status_str == "pass" else VerdictStatus.FAIL,
            confidence=float(data.get("confidence", 0.8)),
            findings=findings,
            owasp_categories_checked=data.get("owasp_categories_checked", _OWASP_CATEGORIES),
            summary=data.get("summary", ""),
        )

        return AgentOutput(
            agent_name=self.name,
            iteration=input.iteration,
            security_report=report,
            raw_response=raw,
            tokens_used=tokens,
        )
