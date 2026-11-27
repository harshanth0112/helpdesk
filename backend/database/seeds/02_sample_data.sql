-- ============================================================================
-- SMART IT HELPDESK MANAGEMENT SYSTEM - SAMPLE DEVELOPMENT DATA (PHASE 2)
-- Script: 02_sample_data.sql
-- Description: Inserts realistic seed data into users, categories, tickets,
--              comments, attachments, audit_logs, refresh_tokens, and password_reset_tokens.
-- Passwords: Standard bcrypt hash representing '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y' (hash of 'SecretPass123!')
-- ============================================================================

-- Clean existing data in reverse dependency order (idempotent for testing)
TRUNCATE TABLE 
    password_reset_tokens,
    refresh_tokens,
    audit_logs,
    attachments,
    comments,
    tickets,
    categories,
    users
RESTART IDENTITY CASCADE;

-- ----------------------------------------------------------------------------
-- 1. SEED USERS
-- Roles: admin, technician, employee
-- ----------------------------------------------------------------------------
INSERT INTO users (id, email, password_hash, first_name, last_name, role, phone, department, is_active)
VALUES 
    (1, 'admin@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'Sarah', 'Connor', 'admin', '+1-555-0101', 'IT Operations', true),
    (2, 'tech.alex@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'Alex', 'Rivera', 'technician', '+1-555-0102', 'IT Support', true),
    (3, 'tech.maya@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'Maya', 'Patel', 'technician', '+1-555-0103', 'Network Engineering', true),
    (4, 'tech.liam@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'Liam', 'Chen', 'technician', '+1-555-0104', 'Cloud Infrastructure', true),
    (5, 'emp.john@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'John', 'Doe', 'employee', '+1-555-0201', 'Finance', true),
    (6, 'emp.emily@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'Emily', 'Watson', 'employee', '+1-555-0202', 'Marketing', true),
    (7, 'emp.robert@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'Robert', 'Taylor', 'employee', '+1-555-0203', 'Human Resources', true),
    (8, 'emp.sophia@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'Sophia', 'Kim', 'employee', '+1-555-0204', 'Product Design', true),
    (9, 'emp.david@helpdesk.local', '$2b$12$e8q4l1M8U07OaPmsbQhRCOaUfDfqnS.U4xQZq0e6V5k9Kx4Qv.b6y', 'David', 'Miller', 'employee', '+1-555-0205', 'Engineering', false);

SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));


-- ----------------------------------------------------------------------------
-- 2. SEED CATEGORIES
-- ----------------------------------------------------------------------------
INSERT INTO categories (id, name, description, is_active)
VALUES
    (1, 'Hardware & Devices', 'Workstations, laptops, monitors, docks, keyboards, printers', true),
    (2, 'Software & Applications', 'Operating systems, productivity suites, dev tools, license activations', true),
    (3, 'Network & Connectivity', 'Wi-Fi, VPN tunnels, DNS resolution, LAN cabling', true),
    (4, 'Access & Security', 'SSO credentials, MFA resets, permission grants, phishing reports', true),
    (5, 'Email & Collaboration', 'Google Workspace, Outlook, Slack, Zoom integration', true);

SELECT setval('categories_id_seq', (SELECT MAX(id) FROM categories));


-- ----------------------------------------------------------------------------
-- 3. SEED TICKETS
-- Demonstrates:
--   - Requesters (emp.john, emp.emily, emp.robert, emp.sophia) creating multiple tickets
--   - Technicians (tech.alex, tech.maya, tech.liam) assigned multiple tickets
--   - Priorities: low, medium, high, critical
--   - Statuses: open, assigned, in_progress, pending, resolved, closed
-- ----------------------------------------------------------------------------
INSERT INTO tickets (
    id, ticket_number, title, description, status, priority, 
    category_id, requester_id, assigned_to, resolved_at, closed_at, created_at, updated_at
)
VALUES
    (
        1, 'TICK-2026-0001', 'Dual monitor display flickers on dock connection',
        'External monitor 2 blacks out intermittently when plugging into the Thunderbolt docking station.',
        'in_progress', 'high', 1, 5, 2, NULL, NULL,
        NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 day'
    ),
    (
        2, 'TICK-2026-0002', 'VPN tunnel drop after macOS Sonoma update',
        'Cisco AnyConnect disconnects every 15 minutes with Gateway Unreachable error code 412.',
        'assigned', 'critical', 3, 5, 3, NULL, NULL,
        NOW() - INTERVAL '2 days', NOW() - INTERVAL '12 hours'
    ),
    (
        3, 'TICK-2026-0003', 'Request Adobe Creative Cloud Photoshop license',
        'Need annual subscription seat allocated for upcoming product branding collateral.',
        'resolved', 'medium', 2, 6, 2, NOW() - INTERVAL '4 hours', NULL,
        NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 hours'
    ),
    (
        4, 'TICK-2026-0004', 'MFA token lost due to phone replacement',
        'User replaced mobile hardware over the weekend and cannot complete Okta Push verify.',
        'closed', 'high', 4, 7, 4, NOW() - INTERVAL '1 day', NOW() - INTERVAL '6 hours',
        NOW() - INTERVAL '5 days', NOW() - INTERVAL '6 hours'
    ),
    (
        5, 'TICK-2026-0005', 'Figma enterprise workspace seat invitation',
        'New hire onboarded into Product Design requires organization member permissions.',
        'open', 'low', 2, 8, NULL, NULL, NULL,
        NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours'
    ),
    (
        6, 'TICK-2026-0006', 'Floor 4 Conference Room Wi-Fi SSID unreachable',
        'Access point in Boardroom B appears offline; SSIDs not broadcasting in 5GHz band.',
        'in_progress', 'critical', 3, 6, 3, NULL, NULL,
        NOW() - INTERVAL '1 day', NOW() - INTERVAL '2 hours'
    ),
    (
        7, 'TICK-2026-0007', 'Keyboard spacebar sticking on ThinkPad X1',
        'Mechanical switch on laptop spacebar is defective; request external keyboard or key replacement.',
        'pending', 'low', 1, 7, 2, NULL, NULL,
        NOW() - INTERVAL '2 days', NOW() - INTERVAL '10 hours'
    ),
    (
        8, 'TICK-2026-0008', 'Git commit signing GPG key verification error',
        'GitHub Enterprise rejects commits due to expired subkey on developer smart card.',
        'assigned', 'medium', 4, 8, 4, NULL, NULL,
        NOW() - INTERVAL '12 hours', NOW() - INTERVAL '4 hours'
    );

SELECT setval('tickets_id_seq', (SELECT MAX(id) FROM tickets));


-- ----------------------------------------------------------------------------
-- 4. SEED COMMENTS
-- Demonstrates multiple comments per ticket (public requester updates & internal technician notes)
-- ----------------------------------------------------------------------------
INSERT INTO comments (id, ticket_id, user_id, comment_text, is_internal, created_at)
VALUES
    (1, 1, 5, 'Tried swapping the HDMI and DisplayPort cables; issue persists across both ports.', false, NOW() - INTERVAL '2 days 20 hours'),
    (2, 1, 2, 'Checking docking station firmware version. Will push Dell Display Manager update remotely.', false, NOW() - INTERVAL '2 days 18 hours'),
    (3, 1, 2, 'Internal Note: Vendor bulletin indicates known chipset defect on dock rev A02. Might need hardware replacement.', true, NOW() - INTERVAL '1 day 12 hours'),
    (4, 2, 3, 'Internal Note: Escalated to network operations tier-2; checking ASA firewall route tables.', true, NOW() - INTERVAL '1 day 6 hours'),
    (5, 2, 3, 'Please run the Cisco diagnostic bundle and attach the resulting DART zip file.', false, NOW() - INTERVAL '1 day 2 hours'),
    (6, 3, 2, 'Photoshop license provisioned in Adobe Admin Console. User invited via company email.', false, NOW() - INTERVAL '4 hours'),
    (7, 4, 4, 'Identity verified via secondary manager confirmation. Hardware token cleared and QR provisioned.', false, NOW() - INTERVAL '1 day');

SELECT setval('comments_id_seq', (SELECT MAX(id) FROM comments));


-- ----------------------------------------------------------------------------
-- 5. SEED ATTACHMENTS
-- Demonstrates multiple attachments per ticket
-- ----------------------------------------------------------------------------
INSERT INTO attachments (id, ticket_id, uploaded_by, file_name, file_path, file_size_bytes, mime_type, created_at)
VALUES
    (1, 1, 5, 'screen_flicker_capture.mp4', '/uploads/tickets/1/screen_flicker_capture.mp4', 12450300, 'video/mp4', NOW() - INTERVAL '2 days 22 hours'),
    (2, 1, 5, 'dock_system_specs.txt', '/uploads/tickets/1/dock_system_specs.txt', 4096, 'text/plain', NOW() - INTERVAL '2 days 21 hours'),
    (3, 2, 5, 'cisco_anyconnect_logs.dart.zip', '/uploads/tickets/2/cisco_anyconnect_logs.dart.zip', 3145728, 'application/zip', NOW() - INTERVAL '18 hours'),
    (4, 3, 6, 'manager_approval_email.pdf', '/uploads/tickets/3/manager_approval_email.pdf', 245100, 'application/pdf', NOW() - INTERVAL '4 days');

SELECT setval('attachments_id_seq', (SELECT MAX(id) FROM attachments));


-- ----------------------------------------------------------------------------
-- 6. SEED AUDIT LOGS
-- Demonstrates multiple audit events per ticket
-- ----------------------------------------------------------------------------
INSERT INTO audit_logs (id, ticket_id, actor_id, action, old_values, new_values, ip_address, user_agent, created_at)
VALUES
    (
        1, 1, 5, 'ticket_created', 
        NULL, 
        '{"status": "open", "priority": "high", "title": "Dual monitor display flickers on dock connection"}'::jsonb, 
        '10.10.4.15', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '3 days'
    ),
    (
        2, 1, 1, 'ticket_assigned', 
        '{"assigned_to": null, "status": "open"}'::jsonb, 
        '{"assigned_to": 2, "status": "assigned"}'::jsonb, 
        '10.10.1.2', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '2 days 22 hours'
    ),
    (
        3, 1, 2, 'status_changed', 
        '{"status": "assigned"}'::jsonb, 
        '{"status": "in_progress"}'::jsonb, 
        '10.10.2.14', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '1 day'
    ),
    (
        4, 3, 2, 'status_changed', 
        '{"status": "in_progress"}'::jsonb, 
        '{"status": "resolved", "resolved_at": "2026-11-26T07:00:00Z"}'::jsonb, 
        '10.10.2.14', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '4 hours'
    ),
    (
        5, 4, 4, 'status_changed', 
        '{"status": "resolved"}'::jsonb, 
        '{"status": "closed", "closed_at": "2026-11-26T05:00:00Z"}'::jsonb, 
        '10.10.2.18', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '6 hours'
    );

SELECT setval('audit_logs_id_seq', (SELECT MAX(id) FROM audit_logs));


-- ----------------------------------------------------------------------------
-- 7. SEED REFRESH TOKENS
-- Stores SHA-256 hashed refresh tokens for authenticated sessions
-- ----------------------------------------------------------------------------
INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, is_revoked, created_at, ip_address, user_agent)
VALUES
    (
        1, 1, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        NOW() + INTERVAL '7 days', false, NOW() - INTERVAL '1 hour',
        '10.10.1.2', 'Mozilla/5.0 Admin Client'
    ),
    (
        2, 2, 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
        NOW() + INTERVAL '7 days', false, NOW() - INTERVAL '3 hours',
        '10.10.2.14', 'Mozilla/5.0 Tech Client'
    ),
    (
        3, 5, '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce',
        NOW() - INTERVAL '1 day', true, NOW() - INTERVAL '8 days',
        '10.10.4.15', 'Mozilla/5.0 Employee Client'
    );

SELECT setval('refresh_tokens_id_seq', (SELECT MAX(id) FROM refresh_tokens));


-- ----------------------------------------------------------------------------
-- 8. SEED PASSWORD RESET TOKENS
-- Stores security tokens for credential reset workflow
-- ----------------------------------------------------------------------------
INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at, is_used, created_at, ip_address)
VALUES
    (
        1, 7, 'a89f6424ff922e415cb04e03f1396dad62a95b859c484b383d823199f3fb2e04',
        NOW() + INTERVAL '30 minutes', false, NOW() - INTERVAL '5 minutes',
        '10.10.4.22'
    ),
    (
        2, 6, '5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5',
        NOW() - INTERVAL '2 hours', true, NOW() - INTERVAL '3 hours',
        '10.10.4.30'
    );

SELECT setval('password_reset_tokens_id_seq', (SELECT MAX(id) FROM password_reset_tokens));
