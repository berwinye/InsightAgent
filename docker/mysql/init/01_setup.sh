#!/bin/bash
set -e

echo "==> Creating application users and custom tables..."

mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<SQL
-- Create read-write user
CREATE USER IF NOT EXISTS '${MYSQL_APP_RW_USER}'@'%' IDENTIFIED BY '${MYSQL_APP_RW_PASSWORD}';
GRANT SELECT, INSERT, UPDATE, DELETE ON enterprise_api.* TO '${MYSQL_APP_RW_USER}'@'%';

-- Create read-only user
CREATE USER IF NOT EXISTS '${MYSQL_APP_RO_USER}'@'%' IDENTIFIED BY '${MYSQL_APP_RO_PASSWORD}';
GRANT SELECT ON enterprise_api.* TO '${MYSQL_APP_RO_USER}'@'%';

FLUSH PRIVILEGES;
SQL

mysql -u root -p"${MYSQL_ROOT_PASSWORD}" enterprise_api <<SQL
CREATE TABLE IF NOT EXISTS saved_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    natural_language_query TEXT NOT NULL,
    generated_code TEXT,
    result_summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS analysis_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    query_text TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    error_type VARCHAR(100),
    error_message TEXT,
    iterations INT DEFAULT 0,
    final_answer TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_turns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    log_id INT NOT NULL,
    iteration INT NOT NULL,
    tool_name VARCHAR(50) NOT NULL,
    llm_content TEXT,
    tool_input TEXT,
    tool_output TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (log_id) REFERENCES analysis_logs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
SQL

echo "==> Users and custom tables created successfully."
