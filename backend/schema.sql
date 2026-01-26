-- Biotech Intelligence Platform - Database Schema
-- This schema is designed to enable the "join" that makes this valuable:
-- 13F ownership + clinical catalysts + competitive landscape + KOLs

-- ============================================
-- CORE ENTITIES
-- ============================================

-- Companies (the central node everything connects to)
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    market_cap_mm DECIMAL(15, 2),
    cash_mm DECIMAL(15, 2),
    burn_rate_mm DECIMAL(15, 2),  -- quarterly burn
    runway_months INTEGER,
    headquarters VARCHAR(255),
    website VARCHAR(255),
    ir_page VARCHAR(255),
    sec_cik VARCHAR(20),  -- SEC Central Index Key for EDGAR lookups
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pipeline assets (drugs/therapies in development)
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    name VARCHAR(255) NOT NULL,  -- e.g., "obefazimod"
    generic_name VARCHAR(255),
    mechanism TEXT,  -- e.g., "splicing modulator"
    modality VARCHAR(100),  -- e.g., "small molecule", "antibody", "cell therapy"
    route VARCHAR(100),  -- e.g., "oral", "IV", "subcutaneous"
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indications (diseases/conditions)
CREATE TABLE indications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,  -- e.g., "Ulcerative Colitis"
    therapeutic_area VARCHAR(100),  -- e.g., "Immunology", "Oncology"
    icd10_code VARCHAR(20),
    description TEXT,
    market_size_bn DECIMAL(10, 2),  -- estimated market size
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Asset-Indication mapping (an asset can target multiple indications)
CREATE TABLE asset_indications (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    indication_id INTEGER REFERENCES indications(id),
    phase VARCHAR(50),  -- "Preclinical", "Phase 1", "Phase 2", "Phase 3", "Filed", "Approved"
    status VARCHAR(50),  -- "Active", "Completed", "Suspended", "Terminated"
    nct_id VARCHAR(20),  -- ClinicalTrials.gov ID
    start_date DATE,
    estimated_completion DATE,
    primary_endpoint TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_id, indication_id)
);

-- ============================================
-- 13F OWNERSHIP DATA
-- ============================================

-- Investment funds we track
CREATE TABLE funds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cik VARCHAR(20) UNIQUE,  -- SEC CIK
    fund_type VARCHAR(50),  -- "Specialist", "Generalist", "Crossover"
    aum_mm DECIMAL(15, 2),
    website VARCHAR(255),
    is_biotech_specialist BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13F filings
CREATE TABLE filings_13f (
    id SERIAL PRIMARY KEY,
    fund_id INTEGER REFERENCES funds(id),
    filing_date DATE NOT NULL,
    report_date DATE NOT NULL,  -- quarter end date
    accession_number VARCHAR(50) UNIQUE,
    total_value_mm DECIMAL(15, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Individual holdings from 13F filings
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    filing_id INTEGER REFERENCES filings_13f(id),
    company_id INTEGER REFERENCES companies(id),
    shares BIGINT,
    value_mm DECIMAL(15, 2),
    percent_of_portfolio DECIMAL(5, 2),
    -- Calculated fields for QoQ changes
    shares_change BIGINT,
    shares_change_pct DECIMAL(10, 2),
    is_new_position BOOLEAN DEFAULT FALSE,
    is_sold_out BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13D filings (activist positions > 5%)
CREATE TABLE filings_13d (
    id SERIAL PRIMARY KEY,
    fund_id INTEGER REFERENCES funds(id),
    company_id INTEGER REFERENCES companies(id),
    filing_date DATE NOT NULL,
    accession_number VARCHAR(50) UNIQUE,
    percent_owned DECIMAL(5, 2),
    purpose TEXT,  -- often contains thesis
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- CLINICAL TRIALS DATA
-- ============================================

CREATE TABLE clinical_trials (
    id SERIAL PRIMARY KEY,
    nct_id VARCHAR(20) UNIQUE NOT NULL,
    asset_id INTEGER REFERENCES assets(id),
    indication_id INTEGER REFERENCES indications(id),
    title TEXT,
    phase VARCHAR(50),
    status VARCHAR(100),
    enrollment INTEGER,
    start_date DATE,
    primary_completion_date DATE,
    study_completion_date DATE,
    primary_endpoint TEXT,
    secondary_endpoints TEXT,
    sponsor VARCHAR(255),
    locations TEXT,  -- JSON array of sites
    results_posted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trial results (when available)
CREATE TABLE trial_results (
    id SERIAL PRIMARY KEY,
    trial_id INTEGER REFERENCES clinical_trials(id),
    endpoint_name VARCHAR(255),
    endpoint_type VARCHAR(50),  -- "primary", "secondary", "exploratory"
    result_value VARCHAR(255),
    comparator_value VARCHAR(255),
    p_value DECIMAL(10, 6),
    met_endpoint BOOLEAN,
    notes TEXT,
    source_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- CATALYSTS & EVENTS
-- ============================================

CREATE TABLE catalysts (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    asset_id INTEGER REFERENCES assets(id),
    catalyst_type VARCHAR(100),  -- "PDUFA", "Phase 3 Readout", "Conference Presentation", "AdCom"
    expected_date DATE,
    date_precision VARCHAR(20),  -- "exact", "month", "quarter", "half", "year"
    description TEXT,
    source_url VARCHAR(500),
    is_confirmed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- KOL (KEY OPINION LEADERS)
-- ============================================

CREATE TABLE kols (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    institution VARCHAR(255),
    department VARCHAR(255),
    title VARCHAR(255),
    city VARCHAR(100),
    country VARCHAR(100),
    h_index INTEGER,
    publication_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- KOL expertise areas (links to indications/therapeutic areas)
CREATE TABLE kol_expertise (
    id SERIAL PRIMARY KEY,
    kol_id INTEGER REFERENCES kols(id),
    indication_id INTEGER REFERENCES indications(id),
    expertise_level VARCHAR(50),  -- "Primary", "Secondary"
    publication_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Publications
CREATE TABLE publications (
    id SERIAL PRIMARY KEY,
    pmid VARCHAR(20) UNIQUE,  -- PubMed ID
    title TEXT,
    abstract TEXT,
    journal VARCHAR(255),
    publication_date DATE,
    doi VARCHAR(255),
    citation_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Publication authors (many-to-many)
CREATE TABLE publication_authors (
    id SERIAL PRIMARY KEY,
    publication_id INTEGER REFERENCES publications(id),
    kol_id INTEGER REFERENCES kols(id),
    author_position INTEGER,  -- 1 = first author, -1 = last/senior author
    is_corresponding BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link publications to assets/indications
CREATE TABLE publication_topics (
    id SERIAL PRIMARY KEY,
    publication_id INTEGER REFERENCES publications(id),
    asset_id INTEGER REFERENCES assets(id),
    indication_id INTEGER REFERENCES indications(id),
    relevance_score DECIMAL(3, 2),  -- 0-1 score
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- COMPETITIVE LANDSCAPE
-- ============================================

-- Competitors for each asset/indication combo
CREATE TABLE competitive_landscape (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    indication_id INTEGER REFERENCES indications(id),
    competitor_asset_id INTEGER REFERENCES assets(id),
    relationship VARCHAR(50),  -- "direct", "indirect", "SOC"
    differentiation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Standard of care / approved drugs
CREATE TABLE approved_drugs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    brand_name VARCHAR(255),
    company VARCHAR(255),
    indication_id INTEGER REFERENCES indications(id),
    mechanism TEXT,
    approval_date DATE,
    annual_sales_mm DECIMAL(15, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- NEWS & UPDATES
-- ============================================

CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    url VARCHAR(500) UNIQUE,
    source VARCHAR(255),
    published_date TIMESTAMP,
    summary TEXT,
    full_text TEXT,
    sentiment VARCHAR(20),  -- "positive", "negative", "neutral"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link news to companies
CREATE TABLE news_company_mentions (
    id SERIAL PRIMARY KEY,
    news_id INTEGER REFERENCES news_articles(id),
    company_id INTEGER REFERENCES companies(id),
    is_primary_subject BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES FOR COMMON QUERIES
-- ============================================

CREATE INDEX idx_holdings_company ON holdings(company_id);
CREATE INDEX idx_holdings_filing ON holdings(filing_id);
CREATE INDEX idx_assets_company ON assets(company_id);
CREATE INDEX idx_asset_indications_asset ON asset_indications(asset_id);
CREATE INDEX idx_asset_indications_phase ON asset_indications(phase);
CREATE INDEX idx_trials_nct ON clinical_trials(nct_id);
CREATE INDEX idx_trials_asset ON clinical_trials(asset_id);
CREATE INDEX idx_catalysts_date ON catalysts(expected_date);
CREATE INDEX idx_catalysts_company ON catalysts(company_id);
CREATE INDEX idx_publications_pmid ON publications(pmid);
CREATE INDEX idx_kols_name ON kols(last_name, first_name);
CREATE INDEX idx_filings_13f_fund ON filings_13f(fund_id);
CREATE INDEX idx_filings_13f_date ON filings_13f(report_date);

-- ============================================
-- USEFUL VIEWS
-- ============================================

-- View: Latest holdings per fund per company (for QoQ comparison)
CREATE VIEW latest_holdings AS
SELECT DISTINCT ON (h.company_id, f.fund_id)
    h.*,
    f.fund_id,
    f.report_date,
    fu.name as fund_name,
    c.ticker,
    c.name as company_name
FROM holdings h
JOIN filings_13f f ON h.filing_id = f.id
JOIN funds fu ON f.fund_id = fu.id
JOIN companies c ON h.company_id = c.id
ORDER BY h.company_id, f.fund_id, f.report_date DESC;

-- View: Specialist fund consensus (companies held by multiple specialists)
CREATE VIEW specialist_consensus AS
SELECT 
    c.id as company_id,
    c.ticker,
    c.name,
    COUNT(DISTINCT f.fund_id) as specialist_fund_count,
    SUM(h.value_mm) as total_specialist_value_mm,
    AVG(h.percent_of_portfolio) as avg_portfolio_weight
FROM holdings h
JOIN filings_13f f ON h.filing_id = f.id
JOIN funds fu ON f.fund_id = fu.id
JOIN companies c ON h.company_id = c.id
WHERE fu.is_biotech_specialist = TRUE
AND f.report_date = (SELECT MAX(report_date) FROM filings_13f)
GROUP BY c.id, c.ticker, c.name
ORDER BY specialist_fund_count DESC, total_specialist_value_mm DESC;

-- View: Upcoming catalysts with ownership context
CREATE VIEW catalysts_with_ownership AS
SELECT 
    cat.*,
    c.ticker,
    c.name as company_name,
    a.name as asset_name,
    sc.specialist_fund_count,
    sc.total_specialist_value_mm
FROM catalysts cat
JOIN companies c ON cat.company_id = c.id
LEFT JOIN assets a ON cat.asset_id = a.id
LEFT JOIN specialist_consensus sc ON c.id = sc.company_id
WHERE cat.expected_date >= CURRENT_DATE
ORDER BY cat.expected_date;
