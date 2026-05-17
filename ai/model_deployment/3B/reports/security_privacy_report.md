# Security and Privacy Report

Date: 2026-05-16

## Executive Summary

This report summarises the security and privacy controls applied to the ClearRead 3B model service deployment. The service was deployed as a backend-facing HTTP service with firewall source allowlists, bearer-token authentication, internal container networking for vLLM, controlled runtime files, and sanitised validation records.

The security objective was to make the model endpoint available to the project backend while keeping model runtime access, service credentials, and validation data under controlled handling.

## Purpose

The project backend needs to send text chunks to the model service and receive summaries and key points. Since this service processes user-provided text, the deployment needed clear access control, predictable logging, and careful handling of local secrets and test records.

This report covers the controls implemented during the 3B deployment and the security checks completed before handoff.

## Service Access Design

The public entry point is the wrapper API on TCP port 8010. vLLM runs inside the Docker network and receives requests from the wrapper container.

| Component | Network position | Purpose |
|---|---|---|
| Wrapper API | Public VM port `8010` | Backend-facing API endpoint |
| vLLM backend | Docker network port `8000` | Model inference backend |
| Docker internal network | `clearread-internal` | Container-to-container service communication |

The backend-facing API endpoint is:

```text
http://34.21.166.229:8010
```

The intended production request path is:

```text
Project backend -> GCP firewall allowlist -> wrapper API -> internal vLLM backend -> wrapper API response
```

## Network Controls

GCP firewall rules were used to restrict source access to the wrapper API port. The backend source IP and Azure outbound IP ranges were added for project backend access. A temporary workstation testing rule was also used during validation.

| Firewall rule | Purpose |
|---|---|
| `allow-clearread-summary-api-from-backend` | Allows project backend traffic to TCP 8010 |
| `allow-clearread-summary-api-from-local` | Allows temporary workstation validation traffic to TCP 8010 |

The backend allowlist used the provided project backend source details:

```text
Backend teammate IP: 124.170.25.96
Backend virtual IP: 20.211.64.21
Backend outbound IP ranges: provided Azure outbound IP list
```

The allowlist approach keeps the VM endpoint tied to known backend sources. When the backend hosting configuration changes, the firewall source ranges should be reviewed and updated by the deployment owner.

## Authentication

The summarisation endpoint requires bearer-token authentication:

```http
Authorization: Bearer <CLEARREAD_AI_SERVICE_API_KEY>
```

The service key is stored on the VM in the deployment user's secret directory:

```text
~/.clearread-secrets/clearread_ai_service_api_key.txt
```

The deployment environment file references the key through `CLEARREAD_AI_SERVICE_API_KEYS`. Runtime environment files use restricted file permissions on the VM. The repository package contains template environment files for handoff and keeps runtime secret files outside version control.

## Data Handling and Privacy

The wrapper records operational metadata needed for service monitoring, including request ID, item count, status, model name, service version, and elapsed time. These records support debugging and validation while keeping request content handling focused on the active API call.

The validation package keeps metrics and response structure for the real 16-block test. The full raw input text from the local dataset is kept outside the deployment package. This keeps the handoff material useful for evaluation while reducing exposure of raw text samples.

The deployed endpoint returns structured JSON containing per-block status, summary, key points, schema guard action, and error field. The response format supports dynamic frontend handling while preserving a stable backend contract.

## Security Work Completed

| Area | Work completed | Result |
|---|---|---|
| Firewall | Backend and workstation source allowlists configured for TCP 8010 | Completed |
| Authentication | Bearer-token check added to summarisation endpoint | Completed |
| Internal model access | vLLM kept behind the wrapper on Docker network | Completed |
| Runtime files | Environment and key files stored on VM with restricted permissions | Completed |
| Repository hygiene | Runtime `.env` files, keys, model weights, caches, and compiled files excluded | Completed |
| Validation records | Test evidence kept as metrics and response structure | Completed |
| VM cleanup | Temporary upload files and one-off runtime test images removed after validation | Completed |
| Recovery | Docker service restart enabled, with restart and check scripts available | Completed |

## Observations and Resolutions

The deployment required a clear separation between handoff files and runtime secrets. Template files were kept in the repository, and active keys remained on the VM. This gives the team enough information to operate the service while keeping credential material in the runtime environment.

The wrapper service provides a controlled public surface. vLLM stays inside Docker networking, so backend traffic reaches the model through the authenticated wrapper rather than direct model-server access.

The firewall allowlist depends on stable backend source IP information. The current rule set matches the known backend and workstation testing sources. Future backend infrastructure changes should include a firewall source-range review.

The deployment records avoid full raw dataset storage in the report package. Test outcomes, timings, and result counts are retained for assessment evidence.

## Result

The ClearRead 3B service has appropriate controls for project backend integration and school demonstration. Access is controlled by source allowlists and bearer authentication, model serving is isolated behind the wrapper API, runtime secrets are stored outside the repository package, and validation records are documented with privacy-aware evidence.
