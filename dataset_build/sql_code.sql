-- MySQL 8.0+
-- SET NAMES utf8mb4;
-- SET FOREIGN_KEY_CHECKS = 0;


-- 如果数据库已经存在，则先删除
DROP DATABASE IF EXISTS clearread;

-- 创建新的数据库
CREATE DATABASE clearread;

-- 可选：使用该数据库
USE clearread;


CREATE TABLE IF NOT EXISTS `USER` (
    user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    preferences JSON NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    last_active_at DATETIME(3) NULL,
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `DOCUMENT` (
    document_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    parsed_text LONGTEXT NULL,
    uploaded_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (document_id),
    KEY idx_document_user_id (user_id),
    CONSTRAINT fk_document_user
        FOREIGN KEY (user_id) REFERENCES `USER`(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `PROCESSED_CONTENT` (
    content_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    document_id BIGINT UNSIGNED NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content LONGTEXT NOT NULL,
    generated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (content_id),
    KEY idx_processed_content_document_id (document_id),
    KEY idx_processed_content_document_type (document_id, content_type),
    CONSTRAINT fk_processed_content_document
        FOREIGN KEY (document_id) REFERENCES `DOCUMENT`(document_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `GLOSSARY` (
    term_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    document_id BIGINT UNSIGNED NOT NULL,
    term VARCHAR(255) NOT NULL,
    simple_definition TEXT NULL,
    context_example TEXT NULL,
    PRIMARY KEY (term_id),
    UNIQUE KEY uk_glossary_document_term (document_id, term),
    KEY idx_glossary_document_id (document_id),
    CONSTRAINT fk_glossary_document
        FOREIGN KEY (document_id) REFERENCES `DOCUMENT`(document_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `TASK_STEP` (
    step_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    document_id BIGINT UNSIGNED NOT NULL,
    step_order INT UNSIGNED NOT NULL,
    instruction_text TEXT NOT NULL,
    is_completed TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (step_id),
    UNIQUE KEY uk_task_step_document_order (document_id, step_order),
    KEY idx_task_step_document_id (document_id),
    CONSTRAINT fk_task_step_document
        FOREIGN KEY (document_id) REFERENCES `DOCUMENT`(document_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `AUDIO_SESSION` (
    session_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    document_id BIGINT UNSIGNED NOT NULL,
    playback_speed DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    last_position_seconds INT UNSIGNED NOT NULL DEFAULT 0,
    started_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    ended_at DATETIME(3) NULL,
    PRIMARY KEY (session_id),
    KEY idx_audio_session_user_id (user_id),
    KEY idx_audio_session_document_id (document_id),
    CONSTRAINT fk_audio_session_user
        FOREIGN KEY (user_id) REFERENCES `USER`(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_audio_session_document
        FOREIGN KEY (document_id) REFERENCES `DOCUMENT`(document_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `READING_PROCESS` (
    process_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    document_id BIGINT UNSIGNED NOT NULL,
    last_position INT UNSIGNED NOT NULL DEFAULT 0,
    last_accessed_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (process_id),
    UNIQUE KEY uk_reading_process_user_document (user_id, document_id),
    KEY idx_reading_process_document_id (document_id),
    CONSTRAINT fk_reading_process_user
        FOREIGN KEY (user_id) REFERENCES `USER`(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_reading_process_document
        FOREIGN KEY (document_id) REFERENCES `DOCUMENT`(document_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `FOCUS_MODE_SETTING` (
    setting_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    is_enabled TINYINT(1) NOT NULL DEFAULT 0,
    ruler_width INT UNSIGNED NOT NULL DEFAULT 80,
    PRIMARY KEY (setting_id),
    UNIQUE KEY uk_focus_mode_setting_user_id (user_id),
    CONSTRAINT fk_focus_mode_setting_user
        FOREIGN KEY (user_id) REFERENCES `USER`(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `VOICE_RECORDING` (
    recording_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    audio_file_path VARCHAR(500) NOT NULL,
    transcribed_text LONGTEXT NULL,
    structured_notes LONGTEXT NULL,
    recorded_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (recording_id),
    KEY idx_voice_recording_user_id (user_id),
    CONSTRAINT fk_voice_recording_user
        FOREIGN KEY (user_id) REFERENCES `USER`(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `COMMUNITY_RESOURCE` (
    resource_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255) NULL,
    state VARCHAR(100) NULL,
    url VARCHAR(2048) NULL,
    description TEXT NULL,
    PRIMARY KEY (resource_id),
    KEY idx_community_resource_type (type),
    KEY idx_community_resource_state (state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `USER_COMMUNITY` (
    user_id BIGINT UNSIGNED NOT NULL,
    resource_id BIGINT UNSIGNED NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (user_id, resource_id),
    KEY idx_user_community_resource_id (resource_id),
    CONSTRAINT fk_user_community_user
        FOREIGN KEY (user_id) REFERENCES `USER`(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_user_community_resource
        FOREIGN KEY (resource_id) REFERENCES `COMMUNITY_RESOURCE`(resource_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- SET FOREIGN_KEY_CHECKS = 1;