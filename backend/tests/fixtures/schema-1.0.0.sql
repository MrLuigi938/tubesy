-- Database schema of Tubesy 1.0.0, for the migration test.
CREATE TABLE api_tokens (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	prefix VARCHAR(16) NOT NULL, 
	scope VARCHAR(8) NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_used_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE downloads (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	url TEXT NOT NULL, 
	video_id VARCHAR(128), 
	extractor VARCHAR(64), 
	title TEXT, 
	uploader VARCHAR(255), 
	thumbnail TEXT, 
	duration FLOAT, 
	preset_name VARCHAR(64), 
	options JSON NOT NULL, 
	subfolder VARCHAR(255), 
	playlist_title TEXT, 
	playlist_index INTEGER, 
	subscription_id INTEGER, 
	status VARCHAR(16) NOT NULL, 
	progress FLOAT NOT NULL, 
	error TEXT, 
	file_path TEXT, 
	file_size BIGINT, 
	created_at DATETIME NOT NULL, 
	started_at DATETIME, 
	finished_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE invites (
	id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	note VARCHAR(255), 
	role VARCHAR(16) NOT NULL, 
	max_uses INTEGER NOT NULL, 
	uses INTEGER NOT NULL, 
	expires_at DATETIME, 
	created_by INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE presets (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	name VARCHAR(64) NOT NULL, 
	options JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE sessions (
	id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	user_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_seen_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	ip VARCHAR(64), 
	user_agent VARCHAR(512), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE settings (
	"key" VARCHAR(64) NOT NULL, 
	value JSON NOT NULL, 
	PRIMARY KEY ("key")
);
CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(32) NOT NULL, 
	email VARCHAR(255), 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(16) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	quota_bytes BIGINT, 
	default_preset_id INTEGER, 
	created_at DATETIME NOT NULL, 
	last_login_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_api_tokens_token_hash ON api_tokens (token_hash);
CREATE INDEX ix_api_tokens_user_id ON api_tokens (user_id);
CREATE INDEX ix_downloads_created_at ON downloads (created_at);
CREATE INDEX ix_downloads_status ON downloads (status);
CREATE INDEX ix_downloads_subscription_id ON downloads (subscription_id);
CREATE INDEX ix_downloads_user_id ON downloads (user_id);
CREATE UNIQUE INDEX ix_invites_token_hash ON invites (token_hash);
CREATE INDEX ix_presets_user_id ON presets (user_id);
CREATE UNIQUE INDEX ix_sessions_token_hash ON sessions (token_hash);
CREATE INDEX ix_sessions_user_id ON sessions (user_id);
CREATE UNIQUE INDEX ix_users_username ON users (username);
