-- =============================================
-- IVF Tâm Anh HN - Quality Audit System
-- Supabase Schema
-- =============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- MODULE 5: Users
-- =============================================
CREATE TABLE IF NOT EXISTS audit_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(50) DEFAULT 'auditor', -- 'admin', 'auditor', 'viewer'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- MODULE 6: Options / Configuration
-- =============================================
CREATE TABLE IF NOT EXISTS departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default departments
INSERT INTO departments (name, code, sort_order) VALUES
    ('Lab IVF', 'LAB_IVF', 1),
    ('Khu thủ thuật - Điều dưỡng', 'PROCEDURE', 2),
    ('Khu phòng khám tư vấn', 'CLINIC', 3),
    ('Khu Phòng tiêm thuốc - lấy máu', 'INJECTION', 4),
    ('Khu sảnh chờ của Bệnh nhân', 'WAITING', 5),
    ('Lab xét nghiệm Nam Khoa', 'ANDROLOGY', 6)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS audit_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- MODULE 1: Audit Planning
-- =============================================
CREATE TABLE IF NOT EXISTS audit_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    year INT NOT NULL,                          -- 2026, 2027, 2028
    sequence_no INT NOT NULL,                   -- 1-12
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    issue_type VARCHAR(50) NOT NULL,            -- 'new_objective', 'additional_monitoring'
    audit_level VARCHAR(50) NOT NULL,           -- 'urgent', 'moderate', 'intensive', 'rtac'
    audit_nature VARCHAR(50) NOT NULL,          -- 'supplementary', 'mandatory_periodic', 'on_request'
    status VARCHAR(50) DEFAULT 'planned',       -- 'planned', 'in_progress', 'completed'
    notes TEXT,
    created_by UUID REFERENCES audit_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(year, sequence_no)
);

CREATE TABLE IF NOT EXISTS audit_objectives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id UUID NOT NULL REFERENCES audit_plans(id) ON DELETE CASCADE,
    objective_no INT NOT NULL,
    objective_text TEXT NOT NULL,
    department_ids UUID[],                      -- array of department IDs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_kpis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    objective_id UUID NOT NULL REFERENCES audit_objectives(id) ON DELETE CASCADE,
    kpi_text TEXT NOT NULL,
    expected_outcome TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- MODULE 2: Audit Findings / Results
-- =============================================
CREATE TABLE IF NOT EXISTS audit_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id UUID NOT NULL REFERENCES audit_plans(id) ON DELETE CASCADE,
    objective_id UUID NOT NULL REFERENCES audit_objectives(id),
    kpi_id UUID REFERENCES audit_kpis(id),
    finding_name TEXT NOT NULL,
    impact_consequence TEXT,
    qualitative_assessment TEXT,               -- kết quả, hiệu suất, cấu trúc
    evidence_link TEXT,                        -- Google Drive link
    
    -- Quantitative score (0 to 5, step 0.5)
    quantitative_score NUMERIC(3,1) DEFAULT 0 CHECK (quantitative_score >= 0 AND quantitative_score <= 5),
    
    -- FMEA components (1-10)
    severity_score INT CHECK (severity_score BETWEEN 1 AND 10),
    occurrence_score INT CHECK (occurrence_score BETWEEN 1 AND 10),
    detection_score INT CHECK (detection_score BETWEEN 1 AND 10),
    rpn_score INT GENERATED ALWAYS AS (
        CASE WHEN severity_score IS NOT NULL AND occurrence_score IS NOT NULL AND detection_score IS NOT NULL
        THEN severity_score * occurrence_score * detection_score
        ELSE NULL END
    ) STORED,
    
    -- Process indicator
    process_indicator_score INT CHECK (process_indicator_score BETWEEN 1 AND 10),
    
    corrective_action TEXT,
    follow_up_option VARCHAR(50) DEFAULT 'no_action', -- 'no_action', 'improvement_project', 'additional_monitoring'
    
    -- Reference to previous finding for comparison
    previous_finding_id UUID REFERENCES audit_findings(id),
    
    auditor_id UUID REFERENCES audit_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- VIEWS
-- =============================================
CREATE OR REPLACE VIEW v_audit_plans_summary AS
SELECT 
    ap.*,
    COUNT(DISTINCT ao.id) as objective_count,
    COUNT(DISTINCT af.id) as finding_count
FROM audit_plans ap
LEFT JOIN audit_objectives ao ON ao.plan_id = ap.id
LEFT JOIN audit_findings af ON af.plan_id = ap.id
GROUP BY ap.id;

CREATE OR REPLACE VIEW v_findings_with_context AS
SELECT
    af.*,
    ap.year,
    ap.sequence_no,
    ap.date_from,
    ap.date_to,
    ao.objective_text,
    ao.objective_no,
    ak.kpi_text,
    ak.expected_outcome,
    -- Quantitative classification
    CASE 
        WHEN af.quantitative_score < 3 THEN 'Dưới kỳ vọng'
        WHEN af.quantitative_score <= 4 THEN 'Tạm chấp nhận'
        ELSE 'Kết quả ổn'
    END as quantitative_classification,
    -- Previous RPN for comparison
    pf.rpn_score as previous_rpn_score
FROM audit_findings af
JOIN audit_plans ap ON ap.id = af.plan_id
JOIN audit_objectives ao ON ao.id = af.objective_id
LEFT JOIN audit_kpis ak ON ak.id = af.kpi_id
LEFT JOIN audit_findings pf ON pf.id = af.previous_finding_id;

-- =============================================
-- ROW LEVEL SECURITY (Optional - enable if needed)
-- =============================================
-- ALTER TABLE audit_plans ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE audit_findings ENABLE ROW LEVEL SECURITY;

-- =============================================
-- INDEXES for performance
-- =============================================
CREATE INDEX IF NOT EXISTS idx_audit_plans_year ON audit_plans(year);
CREATE INDEX IF NOT EXISTS idx_audit_plans_year_seq ON audit_plans(year, sequence_no);
CREATE INDEX IF NOT EXISTS idx_audit_objectives_plan ON audit_objectives(plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_kpis_objective ON audit_kpis(objective_id);
CREATE INDEX IF NOT EXISTS idx_audit_findings_plan ON audit_findings(plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_findings_objective ON audit_findings(objective_id);
