# Smart IT Helpdesk – Gmail Email Automation via n8n

Production workflow for sending secure, structured, and templated emails via **n8n Cloud** and **Gmail OAuth2**.

---

## 1. Workflow Architecture & Nodes

The workflow executes in sequence:
1. **Webhook (`POST /helpdesk/send-email`):**
   - Authentication: Header Auth (`X-Helpdesk-Secret`).
   - Rejects unauthenticated requests with `401 Unauthorized`.
2. **Validate Email Payload (Code Node):**
   - Validates email formats (`to`, `reply_to`).
   - Rejects unexpected root attributes to prevent arbitrary parameter/SMTP injection.
   - Enforces `html` or `text` formatting.
   - Compiles predefined templates (`account_registration`, `account_approval`, `account_rejection`, `ticket_assignment`, `ticket_status_update`, `password_reset`).
   - Sanitizes dynamic strings against injection.
3. **If Payload Valid:**
   - Routes valid requests to Gmail delivery.
   - Routes invalid/malformed requests to `Respond 400 Bad Request`.
4. **Gmail - Send Message:**
   - Uses connected **Gmail OAuth2** credentials.
   - Dynamic parameter mapping: `To`, `Subject`, `Email Type`, `Message`, `Reply-To`.
   - Error handling: `continueErrorOutput` enabled so failures don't crash the workflow.
5. **Respond Nodes:**
   - **200 OK:** `{"success": true, "message": "Email accepted for sending"}`
   - **400 Bad Request:** `{"success": false, "error": "<specific validation error>"}`
   - **502 Bad Gateway:** `{"success": false, "error": "Email dispatch failed. Please verify provider connectivity and try again."}` (Redacts tokens, credentials, and internal stack traces).

---

## 2. Secure Execution Data Retention

In workflow settings (`docs/n8n-workflow-smart-helpdesk-gmail.json`):
- `saveDataErrorExecution`: `"none"`
- `saveDataSuccessExecution`: `"none"`
- `saveManualExecutions`: `false`

This ensures **password reset links**, user emails, and internal data are pruned immediately and never persisted to n8n database execution logs.

---

## 3. How to Import the Workflow into n8n Cloud

1. Open your **n8n Cloud** workspace (e.g., `https://<your-instance>.app.n8n.cloud`).
2. Go to **Workflows** > Click **Add Workflow** (or **Import from File**).
3. Click the **...** menu in the top right > **Import from File** (or **Import from URL** / Paste).
4. Select `docs/n8n-workflow-smart-helpdesk-gmail.json`.

---

## 4. Gmail OAuth2 Setup Guide

### Step A: Google Cloud Console Configuration
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com).
2. Create or select your project (e.g. `Smart IT Helpdesk`).
3. Enable the **Gmail API**:
   - Go to **APIs & Services > Library**.
   - Search for `Gmail API` and click **Enable**.
4. Configure the **OAuth Consent Screen**:
   - Select **External** (or **Internal** if using Google Workspace).
   - Enter App Name: `Smart IT Helpdesk Mailer`.
   - Enter User support email and Developer contact info.
   - In **Scopes**, add `https://www.googleapis.com/auth/gmail.send`.
   - Add your test Google account under **Test users**.
5. Create **OAuth 2.0 Credentials**:
   - Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Web application**.
   - Name: `n8n Cloud Mailer`.
   - **Authorized redirect URIs:**
     - For n8n Cloud: `https://app.n8n.cloud/rest/oauth2-credential/callback`
     *(Note: Always confirm against the OAuth Redirect URI displayed on your n8n credential creation modal)*
   - Copy the generated **Client ID** and **Client Secret**.

### Step B: Connect in n8n Cloud
1. In n8n, navigate to **Credentials > Add Credential > Gmail OAuth2 API**.
2. Paste the **Client ID** and **Client Secret**.
3. Click **Connect My Account**.
4. Log into your Google account and grant the requested send permissions.
5. Save the credential with name `Helpdesk Gmail OAuth2`.

---

## 5. Webhook Authentication Setup

1. In n8n, navigate to **Credentials > Add Credential > Header Auth**.
2. Configure:
   - **Name:** `X-Helpdesk-Secret`
   - **Value:** Generate a strong random secret (e.g., `openssl rand -hex 32`).
3. Save the credential as `Helpdesk Header Auth (X-Helpdesk-Secret)`.
4. Link this credential in the `Webhook` node.

---

## 6. Test Payloads & cURL Commands

Replace `<N8N_WEBHOOK_URL>` and `<YOUR_SECRET>` with your actual test webhook URL and secret.

### Test 1: Account Registration Template (HTML)
```bash
curl -X POST "https://<your-instance>.app.n8n.cloud/webhook/helpdesk/send-email" \
  -H "Content-Type: application/json" \
  -H "X-Helpdesk-Secret: <YOUR_SECRET>" \
  -d '{
    "to": "test.recipient@example.com",
    "template": "account_registration",
    "recipient_name": "Jane Doe",
    "email_type": "html"
  }'
```

### Test 2: Ticket Assignment Template (HTML)
```bash
curl -X POST "https://<your-instance>.app.n8n.cloud/webhook/helpdesk/send-email" \
  -H "Content-Type: application/json" \
  -H "X-Helpdesk-Secret: <YOUR_SECRET>" \
  -d '{
    "to": "tech.user@example.com",
    "template": "ticket_assignment",
    "recipient_name": "Alex Tech",
    "template_data": {
      "ticket_id": "TICK-2026-0042",
      "ticket_title": "Network switch failure in Rack 4",
      "priority": "Critical"
    }
  }'
```

### Test 3: Password Reset Link
```bash
curl -X POST "https://<your-instance>.app.n8n.cloud/webhook/helpdesk/send-email" \
  -H "Content-Type: application/json" \
  -H "X-Helpdesk-Secret: <YOUR_SECRET>" \
  -d '{
    "to": "user@example.com",
    "template": "password_reset",
    "template_data": {
      "reset_url": "https://helpdesk.company.com/reset-password?token=example_secure_token"
    }
  }'
```

### Test 4: Custom Plain-Text Email
```bash
curl -X POST "https://<your-instance>.app.n8n.cloud/webhook/helpdesk/send-email" \
  -H "Content-Type: application/json" \
  -H "X-Helpdesk-Secret: <YOUR_SECRET>" \
  -d '{
    "to": "employee@example.com",
    "subject": "Scheduled IT Maintenance Notice",
    "message": "Routine server maintenance will take place Saturday at 02:00 UTC.",
    "email_type": "text"
  }'
```

### Test 5: Rejection of Invalid Payload (Missing Subject/Message)
```bash
curl -X POST "https://<your-instance>.app.n8n.cloud/webhook/helpdesk/send-email" \
  -H "Content-Type: application/json" \
  -H "X-Helpdesk-Secret: <YOUR_SECRET>" \
  -d '{
    "to": "employee@example.com"
  }'
```
*Expected response: HTTP 400 with `{"success": false, "error": "Email 'subject' cannot be empty."}`*

### Test 6: Rejection of Unauthorized Request
```bash
curl -X POST "https://<your-instance>.app.n8n.cloud/webhook/helpdesk/send-email" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "employee@example.com",
    "subject": "Test",
    "message": "Test"
  }'
```
*Expected response: HTTP 401 Unauthorized.*
