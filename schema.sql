-- ============================================================
-- TrustButVerify — Research Data Store Schema
-- Created: 2026-02-17
-- Engine: MySQL 8+ / MariaDB 10.5+ (InnoDB, utf8mb4)
-- ============================================================

-- ------------------------------------------------------------
-- 1. Participants
-- ------------------------------------------------------------
CREATE TABLE participants (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  participant_uuid VARCHAR(36)  NOT NULL,          -- UUID issued during explicit registration
  registered_at    DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_participant_uuid (participant_uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 2. Conversations
-- ------------------------------------------------------------
CREATE TABLE conversations (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  participant_id  BIGINT UNSIGNED NOT NULL,
  thread_id       VARCHAR(255) NOT NULL,           -- deterministic threadId from plugin
  platform        VARCHAR(50)  NULL,               -- ChatGPT / Gemini / Grok / Claude / DeepSeek
  domain          VARCHAR(255) NULL,
  url             TEXT         NULL,               -- last seen URL for thread
  title           VARCHAR(512) NULL,
  first_seen_at   DATETIME(3)  NOT NULL,
  last_seen_at    DATETIME(3)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_conversations_thread (participant_id, thread_id),
  KEY idx_conversations_platform (platform),
  KEY idx_conversations_last_seen (last_seen_at),
  CONSTRAINT fk_conversations_participant
    FOREIGN KEY (participant_id) REFERENCES participants(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 3. Conversation turns
-- ------------------------------------------------------------
CREATE TABLE conversation_turns (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  conversation_id    BIGINT UNSIGNED NOT NULL,

  turn_id            VARCHAR(255) NOT NULL,        -- e.g. "threadId::1771311561179"
  previous_turn_id   VARCHAR(255) NULL,

  prompt_ts          DATETIME(3)  NOT NULL,
  response_ts        DATETIME(3)  NOT NULL,
  response_time_ms   INT UNSIGNED NULL,

  prompt_text_len    INT UNSIGNED NULL,
  response_text_len  INT UNSIGNED NULL,

  category           VARCHAR(512) NULL,            -- pipe-separated labels or "pending"
  summary            TEXT         NULL,

  -- Readability metrics (individual columns)
  resp_readability_version     TINYINT UNSIGNED NULL DEFAULT 1,
  resp_sample_text_length      INT UNSIGNED NULL,
  resp_sentence_count          INT UNSIGNED NULL,
  resp_word_count              INT UNSIGNED NULL,
  resp_flesch_reading_ease     DECIMAL(8,2) NULL,
  resp_flesch_kincaid_grade    DECIMAL(8,2) NULL,
  resp_smog_index              DECIMAL(8,2) NULL,
  resp_coleman_liau_index      DECIMAL(8,2) NULL,
  resp_automated_readability   DECIMAL(8,2) NULL,
  resp_gunning_fog             DECIMAL(8,2) NULL,
  resp_dale_chall_score        DECIMAL(8,2) NULL,
  resp_lix                     DECIMAL(8,2) NULL,
  resp_rix                     DECIMAL(8,2) NULL,
  resp_text_standard           VARCHAR(100) NULL,
  resp_text_median             DECIMAL(8,2) NULL,

  -- Complexity metrics (individual columns)
  resp_grade_consensus         DECIMAL(8,2) NULL,
  resp_complexity_band         VARCHAR(20) NULL,     -- very-easy/easy/moderate/hard/very-hard
  resp_reason_codes            VARCHAR(512) NULL,     -- comma-separated

  created_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                                    ON UPDATE CURRENT_TIMESTAMP(3),

  PRIMARY KEY (id),
  UNIQUE KEY uq_turn_id (turn_id),
  KEY idx_turns_conversation_time (conversation_id, response_ts),
  KEY idx_turns_category (category),
  CONSTRAINT fk_turns_conversation
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 4. Copy activities
-- ------------------------------------------------------------
CREATE TABLE copy_activities (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  participant_id     BIGINT UNSIGNED NOT NULL,
  activity_id        VARCHAR(255) NOT NULL,         -- client-generated ID (e.g. "1771311845746-n7vvctn")
  occurred_at        DATETIME(3)  NOT NULL,
  domain             VARCHAR(255) NULL,
  url                TEXT         NULL,

  thread_id          VARCHAR(255) NULL,             -- conversationId if associated
  turn_id            VARCHAR(255) NULL,             -- matched turn if associated
  turn_side          VARCHAR(10)  NULL,             -- 'prompt' or 'response'

  selection_len      INT UNSIGNED NULL,             -- length of copied text
  container_text_len INT UNSIGNED NULL,             -- length of full container text
  is_full_text       TINYINT(1)   NULL DEFAULT 0,   -- 1 = copied entire text, 0 = partial

  copy_category        VARCHAR(512) NULL,           -- e.g. "Language Translation|Education"
  copy_category_source VARCHAR(20)  NULL,           -- 'llm' or 'turn'

  -- Readability metrics (individual columns)
  readability_version          TINYINT UNSIGNED NULL DEFAULT 1,
  sample_text_length           INT UNSIGNED NULL,
  sentence_count               INT UNSIGNED NULL,
  word_count                   INT UNSIGNED NULL,
  flesch_reading_ease          DECIMAL(8,2) NULL,
  flesch_kincaid_grade         DECIMAL(8,2) NULL,
  smog_index                   DECIMAL(8,2) NULL,
  coleman_liau_index           DECIMAL(8,2) NULL,
  automated_readability        DECIMAL(8,2) NULL,
  gunning_fog                  DECIMAL(8,2) NULL,
  dale_chall_score             DECIMAL(8,2) NULL,
  lix                          DECIMAL(8,2) NULL,
  rix                          DECIMAL(8,2) NULL,
  text_standard                VARCHAR(100) NULL,
  text_median                  DECIMAL(8,2) NULL,

  -- Complexity metrics (individual columns)
  grade_consensus              DECIMAL(8,2) NULL,
  complexity_band              VARCHAR(20) NULL,     -- very-easy/easy/moderate/hard/very-hard
  reason_codes                 VARCHAR(512) NULL,     -- comma-separated

  created_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

  PRIMARY KEY (id),
  UNIQUE KEY uq_activity_id (participant_id, activity_id),
  KEY idx_copy_time (occurred_at),
  KEY idx_copy_domain (domain),
  KEY idx_copy_thread (thread_id),
  KEY idx_copy_turn (turn_id),
  KEY idx_copy_side (turn_side),
  CONSTRAINT fk_copy_participant
    FOREIGN KEY (participant_id) REFERENCES participants(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------
-- 5. Nudge events (ESM / questionnaire responses)
-- ------------------------------------------------------------
CREATE TABLE nudge_events (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  participant_id     BIGINT UNSIGNED NOT NULL,
  event_id           VARCHAR(255) NOT NULL,         -- client-generated (e.g. "nudge-1771311698722-867856")
  occurred_at        DATETIME(3)  NOT NULL,
  domain             VARCHAR(255) NULL,

  thread_id          VARCHAR(255) NULL,             -- conversationId from browser
  turn_id            VARCHAR(255) NULL,
  copy_activity_id   VARCHAR(255) NULL,             -- only for copy-triggered nudges

  trigger_type       VARCHAR(20)  NOT NULL,         -- 'copy' or 'response'
  question_id        VARCHAR(100) NOT NULL,         -- e.g. "response-clarity-1"
  question_text      TEXT         NOT NULL,

  response           VARCHAR(50)  NULL,             -- 'yes'/'no'/'partly'/'skip' or '1'-'10'
  response_time_ms   INT UNSIGNED NULL,
  dismissed_by       VARCHAR(20)  NULL,             -- 'answer'/'skip'/'close'/'timeout'/'replaced'

  created_at         DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

  PRIMARY KEY (id),
  UNIQUE KEY uq_event_id (participant_id, event_id),
  KEY idx_nudge_time (occurred_at),
  KEY idx_nudge_trigger (trigger_type),
  KEY idx_nudge_question (question_id),
  KEY idx_nudge_dismissed (dismissed_by),
  CONSTRAINT fk_nudge_participant
    FOREIGN KEY (participant_id) REFERENCES participants(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
