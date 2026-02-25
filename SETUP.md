# Setup

## 1) Configure GitHub Secrets
In repository settings (`Settings -> Secrets and variables -> Actions`):

- Secret: `RESEND_API_KEY`
- Secret (optional but recommended): `NCBI_API_KEY`

## 2) Configure GitHub Variables
Add repository variables:

- `REPORT_RECIPIENT` = `tgutman100@gmail.com`
- `REPORT_SENDER` = sender identity in Resend. Start with `onboarding@resend.dev`, then switch to a verified domain sender for production.
- `REPORT_REPLY_TO` = optional reply-to address
- `NCBI_EMAIL` = optional contact email for NCBI E-utilities (recommended)

## 3) Enable Workflows
Two workflows are included:

- `.github/workflows/weekly-report.yml`
  - Schedule: Sunday at 08:00 Israel time
  - Sends weekly report email

- `.github/workflows/resend-policy-watchdog.yml`
  - Schedule: monthly
  - Checks `https://resend.com/pricing`
  - Sends alert if free-tier section appears changed

## 4) First Test
- Run `weekly-report` manually using `workflow_dispatch`.
- Confirm email arrives.
- Run `resend-policy-watchdog` manually and confirm snapshot updates.

## Notes
- GitHub Action cron is UTC; the workflow contains a timezone guard for `Asia/Jerusalem`.
- The pricing watchdog uses page-content comparison and may generate occasional false positives.
- If PubMed returns HTTP 429, add `NCBI_API_KEY` and `NCBI_EMAIL` to improve NCBI API reliability and limits.
