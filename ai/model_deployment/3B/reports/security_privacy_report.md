# Security and Privacy Report

Date: 2026-05-16

## Summary

The 3B model service is protected by GCP firewall source allowlists and Bearer API key authentication. vLLM is available only on the private Docker network. The public entry point is the wrapper API on TCP port 8010.

## Network Controls

```text
Public API: http://34.21.166.229:8010
Public port: tcp:8010
Private vLLM port: tcp:8000 inside Docker network
```

Firewall rule for backend access:

```text
allow-clearread-summary-api-from-backend
```

Firewall rule for temporary workstation testing:

```text
allow-clearread-summary-api-from-local
```

The backend allowlist includes the provided backend source IP and Azure outbound IP ranges. If the backend hosting configuration changes, the GCP firewall source ranges should be reviewed.

## Authentication

The summarize endpoint requires:

```http
Authorization: Bearer <CLEARREAD_AI_SERVICE_API_KEY>
```

The service key is stored on the VM under the deployment user's secret directory and is excluded from this package.

## Logging and Data Handling

The wrapper records metadata such as request ID, item count, status, and elapsed time. The deployment package excludes runtime secrets, raw request bodies, and local environment files.

The public validation artifact for the real 16-block test was sanitized to retain metrics and response structure without retaining full raw input text.

## VM Hardening Actions

- Runtime environment files were restricted to mode `600`.
- Temporary upload and deployment scripts under `/tmp` were removed.
- The one-off CUDA runtime test image was removed after validation.
- Docker is enabled for service recovery after VM restart.

## Result

The current security posture is suitable for backend allowlist integration and project demonstration. A production domain and HTTPS reverse proxy can be added if the service is promoted beyond controlled project access.
