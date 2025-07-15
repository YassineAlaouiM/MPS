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
