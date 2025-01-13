-- Ensure foreign key checks are enabled
PRAGMA foreign_keys = ON;

-- Create a temporary table with the correct schema
CREATE TABLE image_metadata_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    size TEXT NOT NULL,
    format TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- Copy the data from the old table to the new one (assuming default user_id = 1)
INSERT INTO image_metadata_new (id, filename, size, format, user_id)
SELECT id, filename, size, format, 1 FROM image_metadata;

-- Drop the old table
DROP TABLE image_metadata;

-- Rename the new table to the original table name
ALTER TABLE image_metadata_new RENAME TO image_metadata;

PRAGMA table_info(image_metadata);