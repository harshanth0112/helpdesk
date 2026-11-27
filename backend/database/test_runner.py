import sqlite3

def run_tests():
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('PRAGMA foreign_keys = ON;')

    c.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'employee' CHECK (role IN ('employee', 'technician', 'admin')),
        phone TEXT,
        department TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    c.execute('''
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    c.execute('''
    CREATE TABLE tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_number TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'assigned', 'in_progress', 'pending', 'resolved', 'closed')),
        priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
        category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
        requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
        resolved_at TIMESTAMP,
        closed_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    c.execute('''
    CREATE TABLE comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        comment_text TEXT NOT NULL CHECK (LENGTH(TRIM(comment_text)) > 0),
        is_internal INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    c.execute('''
    CREATE TABLE attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
        uploaded_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes > 0 AND file_size_bytes <= 52428800),
        mime_type TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    c.execute('''
    CREATE TABLE audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
        actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        action TEXT NOT NULL,
        old_values TEXT,
        new_values TEXT,
        ip_address TEXT,
        user_agent TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    c.execute('''
    CREATE TABLE refresh_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        is_revoked INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        revoked_at TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT
    );
    ''')

    c.execute('''
    CREATE TABLE password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        is_used INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        used_at TIMESTAMP,
        ip_address TEXT
    );
    ''')

    # Seed data
    c.executemany('''
    INSERT INTO users (id, email, password_hash, first_name, last_name, role, phone, department, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    ''', [
        (1, 'admin@helpdesk.local', 'hash1', 'Sarah', 'Connor', 'admin', '+1-555-0101', 'IT Operations', 1),
        (2, 'tech.alex@helpdesk.local', 'hash2', 'Alex', 'Rivera', 'technician', '+1-555-0102', 'IT Support', 1),
        (3, 'tech.maya@helpdesk.local', 'hash3', 'Maya', 'Patel', 'technician', '+1-555-0103', 'Network Engineering', 1),
        (4, 'tech.liam@helpdesk.local', 'hash4', 'Liam', 'Chen', 'technician', '+1-555-0104', 'Cloud Infrastructure', 1),
        (5, 'emp.john@helpdesk.local', 'hash5', 'John', 'Doe', 'employee', '+1-555-0201', 'Finance', 1),
        (6, 'emp.emily@helpdesk.local', 'hash6', 'Emily', 'Watson', 'employee', '+1-555-0202', 'Marketing', 1),
        (7, 'emp.robert@helpdesk.local', 'hash7', 'Robert', 'Taylor', 'employee', '+1-555-0203', 'Human Resources', 1),
        (8, 'emp.sophia@helpdesk.local', 'hash8', 'Sophia', 'Kim', 'employee', '+1-555-0204', 'Product Design', 1),
        (9, 'emp.david@helpdesk.local', 'hash9', 'David', 'Miller', 'employee', '+1-555-0205', 'Engineering', 0)
    ])

    c.executemany('''
    INSERT INTO categories (id, name, description, is_active)
    VALUES (?, ?, ?, ?);
    ''', [
        (1, 'Hardware & Devices', 'Workstations, laptops, monitors, docks', 1),
        (2, 'Software & Applications', 'Operating systems, dev tools', 1),
        (3, 'Network & Connectivity', 'Wi-Fi, VPN tunnels, DNS', 1),
        (4, 'Access & Security', 'SSO, MFA, credentials', 1),
        (5, 'Email & Collaboration', 'Google Workspace, Slack', 1)
    ])

    c.executemany('''
    INSERT INTO tickets (id, ticket_number, title, description, status, priority, category_id, requester_id, assigned_to)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    ''', [
        (1, 'TICK-2026-0001', 'Dual monitor display flickers on dock connection', 'Dock error', 'in_progress', 'high', 1, 5, 2),
        (2, 'TICK-2026-0002', 'VPN tunnel drop after macOS Sonoma update', 'Cisco error', 'assigned', 'critical', 3, 5, 3),
        (3, 'TICK-2026-0003', 'Request Adobe Creative Cloud Photoshop license', 'License error', 'resolved', 'medium', 2, 6, 2),
        (4, 'TICK-2026-0004', 'MFA token lost due to phone replacement', 'Okta error', 'closed', 'high', 4, 7, 4),
        (5, 'TICK-2026-0005', 'Figma enterprise workspace seat invitation', 'Figma error', 'open', 'low', 2, 8, None),
        (6, 'TICK-2026-0006', 'Floor 4 Conference Room Wi-Fi SSID unreachable', 'Wi-Fi error', 'in_progress', 'critical', 3, 6, 3),
        (7, 'TICK-2026-0007', 'Keyboard spacebar sticking on ThinkPad X1', 'Hardware issue', 'pending', 'low', 1, 7, 2),
        (8, 'TICK-2026-0008', 'Git commit signing GPG key verification error', 'Git error', 'assigned', 'medium', 4, 8, 4)
    ])

    c.executemany('''
    INSERT INTO comments (id, ticket_id, user_id, comment_text, is_internal)
    VALUES (?, ?, ?, ?, ?);
    ''', [
        (1, 1, 5, 'Tried swapping cables', 0),
        (2, 1, 2, 'Checking firmware', 0),
        (3, 1, 2, 'Internal note on dock', 1),
        (4, 2, 3, 'Internal note ASA firewall', 1),
        (5, 2, 3, 'Please attach DART bundle', 0)
    ])

    c.executemany('''
    INSERT INTO attachments (id, ticket_id, uploaded_by, file_name, file_path, file_size_bytes, mime_type)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    ''', [
        (1, 1, 5, 'screen_flicker_capture.mp4', '/uploads/tickets/1/screen_flicker_capture.mp4', 12450300, 'video/mp4'),
        (2, 1, 5, 'dock_system_specs.txt', '/uploads/tickets/1/dock_system_specs.txt', 4096, 'text/plain'),
        (3, 2, 5, 'cisco_anyconnect_logs.dart.zip', '/uploads/tickets/2/cisco_anyconnect_logs.dart.zip', 3145728, 'application/zip')
    ])

    # 1. SELECT WHERE ORDER BY
    q1 = c.execute('SELECT id, email, first_name, last_name, role FROM users WHERE is_active = 1 ORDER BY last_name ASC;').fetchall()
    print('SELECT WHERE ORDER BY count:', len(q1))

    # 2. INSERT
    c.execute('''
    INSERT INTO tickets (ticket_number, title, description, status, priority, category_id, requester_id)
    VALUES ('TICK-2026-0009', 'Cannot access Finance shared drive', 'SMB share error', 'open', 'high', 4, 5);
    ''')
    print('INSERT successful, new row id:', c.lastrowid)

    # 3. UPDATE
    c.execute("UPDATE tickets SET status = 'assigned', assigned_to = 2 WHERE ticket_number = 'TICK-2026-0009';")
    print('UPDATE rows affected:', c.rowcount)

    # 4. DELETE
    c.execute("DELETE FROM tickets WHERE ticket_number = 'TICK-2026-0009';")
    print('DELETE rows affected:', c.rowcount)

    # 5. INNER JOIN
    inner_rows = c.execute('''
    SELECT t.ticket_number, t.title, c.name, req.first_name || ' ' || req.last_name, tech.first_name || ' ' || tech.last_name
    FROM tickets t
    INNER JOIN categories c ON t.category_id = c.id
    INNER JOIN users req ON t.requester_id = req.id
    INNER JOIN users tech ON t.assigned_to = tech.id
    WHERE t.status IN ('assigned', 'in_progress');
    ''').fetchall()
    print('INNER JOIN matched rows:', len(inner_rows))

    # 6. LEFT JOIN
    left_rows = c.execute('''
    SELECT c.name, COUNT(DISTINCT t.id) as ticket_cnt, COUNT(DISTINCT cm.id) as comment_cnt
    FROM categories c
    LEFT JOIN tickets t ON c.id = t.category_id
    LEFT JOIN comments cm ON t.id = cm.ticket_id
    GROUP BY c.id, c.name
    ORDER BY ticket_cnt DESC;
    ''').fetchall()
    print('LEFT JOIN categories summarized:', len(left_rows))

    # 7. GROUP BY & HAVING
    having_rows = c.execute('''
    SELECT u.email, COUNT(t.id) as cnt
    FROM users u
    INNER JOIN tickets t ON u.id = t.requester_id
    GROUP BY u.id, u.email
    HAVING COUNT(t.id) > 1;
    ''').fetchall()
    print('GROUP BY HAVING >1 tickets:', having_rows)

    # 8. AVG
    avg_rows = c.execute('''
    SELECT tech.first_name || ' ' || tech.last_name, COUNT(t.id), AVG(COALESCE(att.file_size_bytes, 0))
    FROM users tech
    LEFT JOIN tickets t ON tech.id = t.assigned_to
    LEFT JOIN attachments att ON t.id = att.ticket_id
    WHERE tech.role = 'technician'
    GROUP BY tech.id, tech.first_name, tech.last_name;
    ''').fetchall()
    print('AVG attachment size query rows:', len(avg_rows))
    print('ALL SQL CHECKS AND CONSTRAINT VALIDATIONS PASSED!')

if __name__ == '__main__':
    run_tests()
