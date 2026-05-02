-- MedMind AI — Full Database Schema
-- PostgreSQL 15 + pgvector
-- Run via: docker-entrypoint-initdb.d or alembic migration

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- ============================================================
-- SPECIALTIES
-- ============================================================
CREATE TABLE IF NOT EXISTS specialties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,       -- e.g. "CARDIO", "NEURO"
    name VARCHAR(200) NOT NULL,             -- "Кардиология"
    name_en VARCHAR(200),
    icon VARCHAR(10),                       -- emoji
    description TEXT,
    is_veterinary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    module_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- MODULES
-- ============================================================
CREATE TABLE IF NOT EXISTS modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,       -- "CARDIO-001", "BASE-ECG-006"
    specialty_id UUID REFERENCES specialties(id),
    title VARCHAR(300) NOT NULL,
    title_en VARCHAR(300),
    description TEXT,
    level INTEGER CHECK (level BETWEEN 1 AND 5) DEFAULT 1,
    level_label VARCHAR(50),               -- "intermediate", "advanced"
    module_order INTEGER DEFAULT 0,
    duration_hours NUMERIC(4,1) DEFAULT 0,
    is_fundamental BOOLEAN DEFAULT FALSE,  -- TRUE for BASE-* modules
    prerequisite_codes TEXT[],             -- codes of prerequisite modules
    prerequisites UUID[],                  -- UUIDs of prerequisite modules
    used_in UUID[],                        -- specialty IDs that use this module
    embedding vector(1536),               -- pgvector for semantic search
    content JSONB,                         -- full original JSON
    is_published BOOLEAN DEFAULT FALSE,
    is_veterinary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_modules_specialty ON modules(specialty_id);
CREATE INDEX IF NOT EXISTS idx_modules_code ON modules(code);
CREATE INDEX IF NOT EXISTS idx_modules_published ON modules(is_published);
CREATE INDEX IF NOT EXISTS idx_modules_fundamental ON modules(is_fundamental);
CREATE INDEX IF NOT EXISTS idx_modules_embedding ON modules USING hnsw (embedding vector_cosine_ops);

-- ============================================================
-- LESSONS
-- ============================================================
CREATE TABLE IF NOT EXISTS lessons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    lesson_code VARCHAR(50),               -- "L001", "L002"
    title VARCHAR(300) NOT NULL,
    lesson_order INTEGER DEFAULT 0,
    content JSONB NOT NULL,               -- full lesson content
    embedding vector(1536),               -- for semantic search
    estimated_minutes INTEGER DEFAULT 20,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lessons_module ON lessons(module_id);

-- ============================================================
-- FLASHCARDS
-- ============================================================
CREATE TABLE IF NOT EXISTS flashcards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'medium', -- easy/medium/hard
    category VARCHAR(100),
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_flashcards_module ON flashcards(module_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_difficulty ON flashcards(difficulty);

-- ============================================================
-- MCQ QUESTIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS mcq_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    options JSONB NOT NULL,               -- {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}
    correct VARCHAR(5) NOT NULL,          -- "A", "B", etc.
    explanation TEXT,
    difficulty VARCHAR(20) DEFAULT 'medium',
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcq_module ON mcq_questions(module_id);

-- ============================================================
-- CLINICAL CASES
-- ============================================================
CREATE TABLE IF NOT EXISTS clinical_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    specialty VARCHAR(100),
    presentation TEXT NOT NULL,
    vitals JSONB,
    diagnosis VARCHAR(300),
    differential_diagnosis TEXT[],
    management TEXT[],
    teaching_points TEXT[],
    content JSONB,                        -- full original JSON
    difficulty VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cases_module ON clinical_cases(module_id);

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,   -- store as-is (encrypt at app layer for GDPR)
    email_hash VARCHAR(64),               -- SHA-256 for lookup without decryption
    password_hash VARCHAR(255),           -- bcrypt, NULL for OAuth users
    role VARCHAR(50) DEFAULT 'student',   -- student|resident|doctor|professor|admin
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    subscription_tier VARCHAR(50) DEFAULT 'free',  -- free|student|pro|clinic|lifetime
    subscription_expires TIMESTAMP,       -- NULL for lifetime/free
    stripe_customer_id VARCHAR(100),
    profile_data JSONB DEFAULT '{}',      -- {years_of_experience, institution, country, interests}
    preferences JSONB DEFAULT '{}',       -- {daily_goal_minutes, dark_mode, language, vet_mode}
    ai_requests_today INTEGER DEFAULT 0,
    ai_requests_reset_at TIMESTAMP DEFAULT NOW(),
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    streak_days INTEGER DEFAULT 0,
    last_active_date DATE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    oauth_provider VARCHAR(50),           -- "google", "apple", NULL for email
    oauth_id VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_email_hash ON users(email_hash);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(subscription_tier);

-- ============================================================
-- USER PROGRESS
-- ============================================================
CREATE TABLE IF NOT EXISTS user_progress (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    lessons_completed UUID[] DEFAULT '{}',
    flashcards_mastered UUID[] DEFAULT '{}',
    mcq_score NUMERIC(5,2) DEFAULT 0,
    mcq_attempts INTEGER DEFAULT 0,
    completion_percent NUMERIC(5,2) DEFAULT 0,
    next_review_at TIMESTAMP,
    ease_factor NUMERIC(4,2) DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    started_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, module_id)
);

CREATE INDEX IF NOT EXISTS idx_progress_user ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_review ON user_progress(next_review_at);

-- ============================================================
-- FLASHCARD REVIEWS (per-card SM-2 state)
-- ============================================================
CREATE TABLE IF NOT EXISTS flashcard_reviews (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    flashcard_id UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    ease_factor NUMERIC(4,2) DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    next_review_at TIMESTAMP DEFAULT NOW(),
    last_reviewed_at TIMESTAMP,
    last_quality INTEGER,                 -- 0-5 (SM-2 quality of last response)
    PRIMARY KEY (user_id, flashcard_id)
);

CREATE INDEX IF NOT EXISTS idx_flashcard_reviews_due ON flashcard_reviews(user_id, next_review_at);

-- ============================================================
-- AI CONVERSATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),
    specialty VARCHAR(100),
    mode VARCHAR(50) DEFAULT 'tutor',     -- tutor|socratic|case|exam
    model_used VARCHAR(100),              -- claude-haiku/sonnet
    cached_responses INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON ai_conversations(user_id);

-- ============================================================
-- AI CONVERSATION MESSAGES
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,            -- "user" | "assistant"
    content TEXT NOT NULL,
    pubmed_refs JSONB,                    -- array of PubMed articles
    model_used VARCHAR(100),
    tokens_used INTEGER DEFAULT 0,
    from_cache BOOLEAN DEFAULT FALSE,
    feedback INTEGER,                     -- 1=thumbs_up, -1=thumbs_down, NULL
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON ai_conversation_messages(conversation_id);

-- ============================================================
-- USER NOTES
-- ============================================================
CREATE TABLE IF NOT EXISTS user_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id UUID REFERENCES lessons(id),
    module_id UUID REFERENCES modules(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- USER BOOKMARKS
-- ============================================================
CREATE TABLE IF NOT EXISTS user_bookmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL,    -- module|lesson|flashcard|case
    content_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, content_type, content_id)
);

-- ============================================================
-- USER ACHIEVEMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_code VARCHAR(100) NOT NULL,  -- "streak_7", "module_master" etc.
    unlocked_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, achievement_code)
);

-- ============================================================
-- DRUGS
-- ============================================================
CREATE TABLE IF NOT EXISTS drugs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200),
    drug_class VARCHAR(100),
    mechanism TEXT,
    indications TEXT[],
    contraindications TEXT[],
    dosing JSONB,
    adverse_effects JSONB,
    interactions TEXT[],
    monitoring TEXT[],
    black_box_warning TEXT,
    is_high_yield BOOLEAN DEFAULT FALSE,
    is_nti BOOLEAN DEFAULT FALSE,         -- Narrow Therapeutic Index
    is_veterinary BOOLEAN DEFAULT FALSE,
    content JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drugs_name_trgm ON drugs USING gin(name gin_trgm_ops);

-- ============================================================
-- ANIMAL SPECIES (veterinary)
-- ============================================================
CREATE TABLE IF NOT EXISTS animal_species (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,    -- "CANINE", "FELINE", "EQUINE"
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    category VARCHAR(50),               -- "small_animal", "large_animal", "exotic"
    physiological_ranges JSONB          -- normal HR, RR, temp, etc.
);

-- ============================================================
-- VETERINARY DOSING
-- ============================================================
CREATE TABLE IF NOT EXISTS veterinary_dosing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_id UUID REFERENCES drugs(id),
    drug_name VARCHAR(200) NOT NULL,     -- denormalized for faster lookup
    species_id UUID NOT NULL REFERENCES animal_species(id),
    dose_mg_kg VARCHAR(100),
    route VARCHAR(50),
    frequency VARCHAR(100),
    notes TEXT,
    contraindicated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- STRIPE / PAYMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS stripe_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stripe_event_id VARCHAR(200) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES users(id),
    data JSONB,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- GDPR: USER CONSENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS user_consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(100) NOT NULL,   -- "terms", "privacy", "marketing"
    version VARCHAR(50),
    given_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    UNIQUE(user_id, consent_type)
);

-- ============================================================
-- AUDIT LOG (GDPR)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,        -- "login", "view_module", "export_data"
    resource_type VARCHAR(100),
    resource_id UUID,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id, created_at);

-- ============================================================
-- REFRESH TOKENS
-- ============================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);

-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================

-- SM-2 next review calculation
CREATE OR REPLACE FUNCTION calculate_next_review(
    p_ease_factor NUMERIC,
    p_interval INTEGER,
    p_quality INTEGER  -- 0-5
) RETURNS TIMESTAMP AS $$
DECLARE
    new_interval INTEGER;
    new_ef NUMERIC;
BEGIN
    -- SM-2 algorithm
    new_ef := p_ease_factor + (0.1 - (5 - p_quality) * (0.08 + (5 - p_quality) * 0.02));
    IF new_ef < 1.3 THEN new_ef := 1.3; END IF;

    IF p_quality < 3 THEN
        new_interval := 1;
    ELSIF p_interval <= 1 THEN
        new_interval := 1;
    ELSIF p_interval = 1 THEN
        new_interval := 6;
    ELSE
        new_interval := ROUND(p_interval * new_ef);
    END IF;

    RETURN NOW() + (new_interval || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER modules_updated_at BEFORE UPDATE ON modules FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER lessons_updated_at BEFORE UPDATE ON lessons FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER drugs_updated_at BEFORE UPDATE ON drugs FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER conversations_updated_at BEFORE UPDATE ON ai_conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- SEED: SPECIALTIES
-- ============================================================
INSERT INTO specialties (code, name, name_en, icon, is_veterinary) VALUES
('BASE',       'Базовые дисциплины',          'Foundations',          '📚', FALSE),
('CARDIO',     'Кардиология',                  'Cardiology',           '❤️', FALSE),
('THERAPY',    'Терапия / Internal Medicine',  'Internal Medicine',    '🩺', FALSE),
('NEURO',      'Неврология',                   'Neurology',            '🧠', FALSE),
('SURG',       'Хирургия',                     'Surgery',              '🔪', FALSE),
('PEDS',       'Педиатрия',                    'Pediatrics',           '👶', FALSE),
('OB',         'Акушерство и гинекология',     'OB/GYN',               '🤰', FALSE),
('PSYCH',      'Психиатрия',                   'Psychiatry',           '🧩', FALSE),
('ANES',       'Анестезиология',               'Anesthesiology',       '💉', FALSE),
('ONC',        'Онкология',                    'Oncology',             '🎗️', FALSE),
('DERM',       'Дерматология',                 'Dermatology',          '🔬', FALSE),
('VET_SMALL',  'Мелкие животные',              'Small Animal',         '🐕', TRUE),
('VET_LARGE',  'Крупные животные / Лошади',    'Large Animal / Equine','🐴', TRUE),
('VET_EXOTIC', 'Экзотические животные',        'Exotic Animals',       '🦜', TRUE),
('VET_BIRDS',  'Птицы',                        'Avian Medicine',       '🐦', TRUE),
('VET_ZOO',    'Зоопарковая медицина',         'Zoo Medicine',         '🦁', TRUE)
ON CONFLICT (code) DO NOTHING;

-- SEED: ANIMAL SPECIES
INSERT INTO animal_species (code, name, name_en, category, physiological_ranges) VALUES
('CANINE',  'Собака',    'Canine',   'small_animal', '{"HR": "60-140", "RR": "15-30", "temp": "38-39.2"}'),
('FELINE',  'Кошка',     'Feline',   'small_animal', '{"HR": "160-240", "RR": "20-40", "temp": "38-39.2"}'),
('EQUINE',  'Лошадь',    'Equine',   'large_animal', '{"HR": "28-44", "RR": "8-16", "temp": "37.5-38.5"}'),
('BOVINE',  'КРС',       'Bovine',   'large_animal', '{"HR": "48-84", "RR": "12-36", "temp": "38-39.5"}'),
('AVIAN',   'Птицы',     'Avian',    'avian',        '{"HR": "200-400", "RR": "25-60", "temp": "40-42"}'),
('RABBIT',  'Кролик',    'Rabbit',   'exotic',       '{"HR": "130-325", "RR": "30-60", "temp": "38.5-40"}')
ON CONFLICT (code) DO NOTHING;
