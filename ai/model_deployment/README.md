# ClearRead Model Deployment Packages

This directory contains packaged deployment evidence for the ClearRead model service work.

## Package Layout

```text
model_deployment/
  8B/   Previous 8B deployment package and supporting evidence
  3B/   Current 3B production deployment package and supporting evidence
```

The `3B` package is the current production service package for Iteration 3. It contains the API wrapper, deployment templates, selected operational scripts, configuration records, model manifests, and formal validation reports.

Large model artifacts are represented through manifests and hashes. Runtime secrets and local environment files are excluded from this repository.
