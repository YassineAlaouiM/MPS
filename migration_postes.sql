-- Migration script to populate postes table and migrate existing operator postes data
-- Run this script after creating the new tables

USE schedule_management;

-- First, populate the postes table with standard postes
INSERT INTO postes (name, type) VALUES
  ('machine', 'machine'),
  ('laveuse', 'machine'),
  ('extrudeuse', 'machine'),
  ('broyeur', 'machine'),
  ('melange', 'service'),
  ('services', 'service'),
  ('chargement', 'service'),
  ('emballage', 'service')
ON DUPLICATE KEY UPDATE name=name;

-- Create a temporary function to migrate existing postes data
-- This will parse the old comma-separated postes string and create entries in operator_postes

-- For each operator with postes data, parse the string and create operator_postes entries
-- Note: This is a simplified migration. You may need to adjust the poste names to match exactly.

-- Example migration for common poste names:
-- This will need to be run for each operator that has postes data

-- You can run this manually for each operator, or create a more sophisticated script
-- that automatically parses the postes string and creates the appropriate entries.

-- Example of how to migrate one operator (replace with actual operator_id and postes):
-- INSERT INTO operator_postes (op_id, poste_id) 
-- SELECT 1, p.id FROM postes p WHERE p.name IN ('machine', 'laveuse');

-- To see which operators have postes data:
SELECT id, name, postes FROM operators WHERE postes IS NOT NULL AND postes != '';

-- To see the available postes:
SELECT * FROM postes ORDER BY name; 