-- Migration: 007_create_usage_ledger
-- Description: One row per billable OpenAI operation, so the public demo can be
--              held to a hard USD ceiling per day and per month (ADR-0019 §3).
-- Requirements: public demo cost containment.
--
-- Why a table and not an in-memory counter: a counter resets on every restart
-- (and every deploy), which would silently hand the demo a fresh budget several
-- times a week. A budget that forgets is not a budget.
--
-- Why NUMERIC and not DOUBLE PRECISION for the cost: this column gets SUMmed
-- thousands of times, and binary floating point accumulates representation error
-- on exactly that operation. NUMERIC is exact decimal arithmetic — the standard
-- choice for money, at the cost of being slower (irrelevant here).

CREATE TABLE IF NOT EXISTS usage_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 'transcription' | 'extraction' | 'enrichment'
    operation VARCHAR(32) NOT NULL,
    -- Estimated, not billed: priced from configured unit costs (ADR-0019 §3).
    -- 6 decimal places because a single operation costs ~$0.0004.
    estimated_cost_usd NUMERIC(12, 6) NOT NULL,
    -- Template session this operation belonged to, when there is one. Nullable
    -- and intentionally NOT a foreign key: the ledger is an accounting record and
    -- must survive the deletion of the session it refers to.
    session_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Every read is "sum the cost since <instant>", so the index is on the column
-- that filters it.
CREATE INDEX idx_usage_ledger_created ON usage_ledger(created_at);
