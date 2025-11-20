CREATE DATABASE Images;

-- GRANT ALL PRIVILEGES ON Images.* TO images_user@localhost IDENTIFIED BY '666';

-- FLUSH PRIVILEGES;

CREATE TABLE IF NOT EXISTS image (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  filename        VARCHAR(255)     NOT NULL,
  mime_type       VARCHAR(100)     NOT NULL,
  size_bytes      BIGINT UNSIGNED  NOT NULL,
  uploaded_at     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  storage_url      TEXT             NOT NULL,
  PRIMARY KEY (id),
  KEY idx_uploaded_at (uploaded_at),
  KEY idx_filename (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
