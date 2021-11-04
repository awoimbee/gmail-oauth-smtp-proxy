# SMTP to GMail oauth API proxy

This project enables you to send emails from servers, via GMail, without using application password(s).

## Requirements

- Google Workspace
- A [service account](https://console.cloud.google.com/iam-admin/serviceaccounts)
- Domain-wide delegation with the `https://www.googleapis.com/auth/gmail.send` scope
- Enabling the [GMail API](https://console.cloud.google.com/apis/api/gmail.googleapis.com)

## TODO

- check if the `subject` has access to the `sender-emails` (https://issuetracker.google.com/issues/205021375)
- EZ integration with identity-federation: https://cloud.google.com/iam/docs/configuring-workload-identity-federation

## Build the container

```bash
DOCKER_BUILDKIT=1 docker build . -t gmail_smtp_proxy:latest
```
