-- Migration script to add postes and other_competences columns to operators table
-- Run this script on existing databases to add the new fields

USE schedule_management;

-- Add postes column if it doesn't exist
ALTER TABLE operators ADD COLUMN postes TEXT;

-- Add other_competences column if it doesn't exist
ALTER TABLE operators ADD COLUMN other_competences TEXT;

-- Update existing records to have empty strings for the new columns
UPDATE operators SET postes = '' WHERE postes IS NULL;
UPDATE operators SET other_competences = '' WHERE other_competences IS NULL; 
