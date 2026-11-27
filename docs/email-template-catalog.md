# Email Template Catalog — Smart IT Helpdesk

All 6 templates are rendered inside the **Validate Email Payload** Code node in [`docs/n8n-workflow-smart-helpdesk-gmail.json`](n8n-workflow-smart-helpdesk-gmail.json) using table-based, inline-CSS HTML (with automatic plain-text fallback when `"email_type": "text"`).

---

## Design Tokens

| Token | Hex | Usage |
|-------|-----|-------|
| Background | `#F3F6FB` | Outer email canvas |
| Card Surface | `#FFFFFF` | Main content container |
| Border | `#E2E8F0` | Dividers & info table border |
| Text Dark | `#1E293B` | Headings & primary copy |
| Text Muted | `#64748B` | Footers & secondary hints |

---

## Templates

### 1. `account_registration`
- **Accent Color**: `#2563EB` (Primary Blue)
- **Default Subject**: `Registration Received - Smart IT Helpdesk`
- **Trigger**: `POST /api/v1/auth/register`
- **Variables**: `recipient_name`
- **Content**: Confirms receipt of registration and informs the user their account is pending administrator approval.

### 2. `account_approval`
- **Accent Color**: `#16A34A` (Success Green)
- **Default Subject**: `Your Helpdesk Account Has Been Approved`
- **Trigger**: `PATCH /api/v1/admin/users/{user_id}/approve`
- **Variables**: `recipient_name`, `template_data.role`
- **Content**: Notifies the user that their account is approved, displays the assigned role (`employee` / `technician`), and provides a login CTA.

### 3. `account_rejection`
- **Accent Color**: `#DC2626` (Error Red)
- **Default Subject**: `Helpdesk Account Registration Update`
- **Trigger**: `PATCH /api/v1/admin/users/{user_id}/reject`
- **Variables**: `recipient_name`, `template_data.rejection_reason` (optional)
- **Content**: Informs the user their registration was not approved and displays the optional rejection reason if provided.

### 4. `ticket_assignment`
- **Accent Color**: `#7C3AED` (Violet)
- **Default Subject**: `New Support Ticket Assigned to You`
- **Trigger**: `PATCH /api/v1/tickets/{ticket_id}/assign`
- **Variables**: `recipient_name`, `template_data.ticket_id`, `template_data.ticket_title`, `template_data.ticket_priority`
- **Content**: Alerts the assigned technician with a structured summary table (Ticket ID, Title, color-coded Priority badge).

### 5. `ticket_status_update`
- **Accent Color**: `#0891B2` (Cyan)
- **Default Subject**: `Your Support Ticket Has Been Updated`
- **Trigger**: `PATCH /api/v1/tickets/{ticket_id}/status`
- **Variables**: `recipient_name`, `template_data.ticket_id`, `template_data.ticket_title`, `template_data.new_status`
- **Content**: Notifies the ticket requester of the status change with a color-coded status badge (`open`, `assigned`, `in_progress`, `pending`, `resolved`, `closed`).

### 6. `password_reset`
- **Accent Color**: `#D97706` (Warning Amber)
- **Default Subject**: `Reset Your Smart IT Helpdesk Password`
- **Trigger**: `POST /api/v1/auth/forgot-password`
- **Variables**: `template_data.reset_url` (required; must start with `https://` or `http://localhost`)
- **Content**: Provides a prominent **Reset My Password** CTA button, notes the 30-minute expiration and one-time-use policy, and advises ignoring unintended requests.
