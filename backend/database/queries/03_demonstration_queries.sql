-- ============================================================================
-- SMART IT HELPDESK MANAGEMENT SYSTEM - DEMONSTRATION SQL QUERIES (PHASE 2)
-- Script: 03_demonstration_queries.sql
-- Description: Comprehensive SQL operations illustrating SELECT, INSERT, UPDATE,
--              DELETE, WHERE, ORDER BY, GROUP BY, HAVING, INNER JOIN, LEFT JOIN,
--              COUNT, and AVG aggregations.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. BASIC SELECT with WHERE, ORDER BY
-- Lists all active users ordered alphabetically by last name and first name.
-- ----------------------------------------------------------------------------
SELECT 
    id,
    email,
    first_name,
    last_name,
    role,
    department,
    is_active,
    created_at
FROM users
WHERE is_active = TRUE
ORDER BY last_name ASC, first_name ASC;


-- ----------------------------------------------------------------------------
-- 2. INSERT DEMONSTRATION
-- Creates a new ticket submitted by an employee with priority 'high'.
-- ----------------------------------------------------------------------------
INSERT INTO tickets (
    ticket_number,
    title,
    description,
    status,
    priority,
    category_id,
    requester_id
)
VALUES (
    'TICK-2026-0009',
    'Cannot access Finance shared drive after password change',
    'SMB share \\\\corp-fs01\\finance returns Access Denied error 0x80070005.',
    'open',
    'high',
    4,
    5
)
RETURNING id, ticket_number, title, status, priority, created_at;


-- ----------------------------------------------------------------------------
-- 3. UPDATE DEMONSTRATION with WHERE
-- Assigns the newly created ticket to technician Alex (user_id = 2) and updates status.
-- ----------------------------------------------------------------------------
UPDATE tickets
SET 
    status = 'assigned',
    assigned_to = 2,
    updated_at = CURRENT_TIMESTAMP
WHERE ticket_number = 'TICK-2026-0009'
RETURNING id, ticket_number, status, assigned_to, updated_at;


-- ----------------------------------------------------------------------------
-- 4. DELETE DEMONSTRATION with WHERE
-- Cleans up expired, already revoked refresh tokens.
-- ----------------------------------------------------------------------------
DELETE FROM refresh_tokens
WHERE is_revoked = TRUE AND expires_at < CURRENT_TIMESTAMP
RETURNING id, user_id, token_hash, expires_at;


-- ----------------------------------------------------------------------------
-- 5. INNER JOIN DEMONSTRATION
-- Retrieves active tickets with their Category, Requester name, and Assigned Technician.
-- ----------------------------------------------------------------------------
SELECT 
    t.ticket_number,
    t.title,
    t.status,
    t.priority,
    c.name AS category_name,
    CONCAT(req.first_name, ' ', req.last_name) AS requester_name,
    req.email AS requester_email,
    CONCAT(tech.first_name, ' ', tech.last_name) AS technician_name,
    tech.email AS technician_email,
    t.created_at
FROM tickets t
INNER JOIN categories c ON t.category_id = c.id
INNER JOIN users req ON t.requester_id = req.id
INNER JOIN users tech ON t.assigned_to = tech.id
WHERE t.status IN ('assigned', 'in_progress')
ORDER BY 
    CASE t.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
        ELSE 5
    END,
    t.created_at ASC;


-- ----------------------------------------------------------------------------
-- 6. LEFT JOIN DEMONSTRATION
-- Lists ALL categories (even those without tickets) and shows tickets or NULL.
-- ----------------------------------------------------------------------------
SELECT 
    c.id AS category_id,
    c.name AS category_name,
    t.ticket_number,
    t.title AS ticket_title,
    t.status AS ticket_status
FROM categories c
LEFT JOIN tickets t ON c.id = t.category_id
ORDER BY c.id ASC, t.id ASC;


-- ----------------------------------------------------------------------------
-- 7. LEFT JOIN with COUNT & GROUP BY
-- Summarizes ticket volume, comments count, and attachments count per category.
-- ----------------------------------------------------------------------------
SELECT 
    c.id AS category_id,
    c.name AS category_name,
    COUNT(DISTINCT t.id) AS total_tickets,
    COUNT(DISTINCT cm.id) AS total_comments,
    COUNT(DISTINCT a.id) AS total_attachments
FROM categories c
LEFT JOIN tickets t ON c.id = t.category_id
LEFT JOIN comments cm ON t.id = cm.ticket_id
LEFT JOIN attachments a ON t.id = a.ticket_id
GROUP BY c.id, c.name
ORDER BY total_tickets DESC, c.name ASC;


-- ----------------------------------------------------------------------------
-- 8. GROUP BY, HAVING & COUNT DEMONSTRATION
-- Identifies users who have submitted MORE THAN 1 ticket.
-- ----------------------------------------------------------------------------
SELECT 
    u.id AS user_id,
    u.email,
    CONCAT(u.first_name, ' ', u.last_name) AS full_name,
    u.department,
    COUNT(t.id) AS tickets_submitted
FROM users u
INNER JOIN tickets t ON u.id = t.requester_id
GROUP BY u.id, u.email, u.first_name, u.last_name, u.department
HAVING COUNT(t.id) > 1
ORDER BY tickets_submitted DESC;


-- ----------------------------------------------------------------------------
-- 9. AVG & AGGREGATE METRICS DEMONSTRATION
-- Computes technician workload, total assigned tickets, and average resolution time in hours.
-- ----------------------------------------------------------------------------
SELECT 
    tech.id AS technician_id,
    CONCAT(tech.first_name, ' ', tech.last_name) AS technician_name,
    tech.department,
    COUNT(t.id) AS total_assigned_tickets,
    COUNT(CASE WHEN t.status IN ('resolved', 'closed') THEN 1 END) AS resolved_count,
    ROUND(
        AVG(
            CASE 
                WHEN t.resolved_at IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 3600.0 
                ELSE NULL 
            END
        )::NUMERIC, 
        2
    ) AS avg_resolution_hours,
    ROUND(
        AVG(COALESCE(att_summary.attachment_bytes, 0)) / 1024.0, 
        2
    ) AS avg_ticket_attachment_kb
FROM users tech
LEFT JOIN tickets t ON tech.id = t.assigned_to
LEFT JOIN (
    SELECT ticket_id, SUM(file_size_bytes) AS attachment_bytes
    FROM attachments
    GROUP BY ticket_id
) att_summary ON t.id = att_summary.ticket_id
WHERE tech.role = 'technician'
GROUP BY tech.id, tech.first_name, tech.last_name, tech.department
ORDER BY total_assigned_tickets DESC;


-- ----------------------------------------------------------------------------
-- 10. TICKET AUDIT TIMELINE with INNER JOIN & ORDER BY
-- Retrieves chronological audit history for a specific ticket with actor details.
-- ----------------------------------------------------------------------------
SELECT 
    al.id AS audit_id,
    t.ticket_number,
    al.action,
    CONCAT(u.first_name, ' ', u.last_name) AS performed_by,
    u.role AS actor_role,
    al.old_values,
    al.new_values,
    al.ip_address,
    al.created_at AS timestamp
FROM audit_logs al
INNER JOIN tickets t ON al.ticket_id = t.id
LEFT JOIN users u ON al.actor_id = u.id
WHERE t.ticket_number = 'TICK-2026-0001'
ORDER BY al.created_at ASC;
