-- Team Table
CREATE TABLE IF NOT EXISTS teams (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    owner_email VARCHAR(255) NOT NULL,
    created_at DOUBLE PRECISION NOT NULL
);

-- User Table
CREATE TABLE IF NOT EXISTS users (
    email VARCHAR(255) PRIMARY KEY,
    team_id VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    joined_at DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- Risk Audit Table
CREATE TABLE IF NOT EXISTS risk_audit (
    id SERIAL PRIMARY KEY,
    merchant_id VARCHAR(255) NOT NULL,
    order_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    ip_address VARCHAR(50) NOT NULL,
    risk_score FLOAT NOT NULL,
    risk_status VARCHAR(50) NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    metadata JSONB
);

-- Risk Profile Audit Table
CREATE TABLE IF NOT EXISTS risk_profile_audit (
    id SERIAL PRIMARY KEY,
    team_id VARCHAR(50) NOT NULL,
    admin_email VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    timestamp DOUBLE PRECISION NOT NULL
);
