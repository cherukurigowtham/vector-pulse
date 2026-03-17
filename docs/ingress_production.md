Production Ingress Guidance for Vector-Pulse

- Overview
  - This document outlines recommended production ingress TLs, certificate management, and traffic flow for Vector-Pulse deployments.

- TLS Termination
  - Terminate TLS at a gateway (Ingress controller, API gateway, or service mesh) with a valid certificate (e.g., from Let's Encrypt or a private CA).
  - End-to-end encryption from client to app should be ensured; the API may remain behind TLS at the gateway with mTLS where applicable.

- Ingress considerations
  - Use a single public entry point per environment; map gateways to the vector-pulse API service.
  - Enable HTTP to HTTPS redirection at the gateway to enforce TLS.
  - Configure health/check endpoints for readiness and liveness as part of the gateway health checks.

- Identification and security
  - Enable access controls in the gateway (IP allowlists, API keys, or OAuth) to protect internal endpoints.
  - Consider rate-limiting and WAF rules to guard against abuse.

- Observability and auditing
  - Ensure traces, metrics, and logs are collected through a central platform; route logs and traces from gateway to your observability stack.

- Rollout notes
  - Start with a staging ingress and run through a controlled canary to validate TLS, redirects, and health endpoints before production rollout.
- TLS Termination
  - Terminate TLS at a gateway (Ingress controller, API gateway, or service mesh) with a valid certificate (e.g., from Let's Encrypt or a private CA).
- Ingress considerations
  - Use a single public entry point per environment; map gateways to the vector-pulse API service.
  - Enable HTTP to HTTPS redirection at the gateway to enforce TLS.
- Identification and security
  - Enable access controls in the gateway (IP allowlists, API keys, or OAuth) to protect internal endpoints.
- Observability and auditing
  - Ensure traces, metrics, and logs are collected through a central platform; route logs and traces from gateway to your observability stack.
- Rollout notes
  - Start with a staging ingress and run through a controlled canary to validate TLS, redirects, and health endpoints before production rollout.
- Implementation Notes
  - In production, ensure the Vector-Pulse API is not directly exposed to the public internet without authentication.
  - Use a certificate management tool (cert-manager) to automate renewals.
