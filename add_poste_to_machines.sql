-- Migration script to add poste_id to machines table
-- This allows each machine to be assigned a specific poste type

USE schedule_management;

-- Add poste_id column to machines table
ALTER TABLE machines ADD COLUMN poste_id INT;

-- Add foreign key constraint
ALTER TABLE machines 
ADD CONSTRAINT fk_machine_poste 
FOREIGN KEY (poste_id) REFERENCES postes(id) ON DELETE SET NULL;

-- Update existing machines with appropriate poste types
-- You can run these manually or update them through your application

-- Example updates (adjust based on your actual machine names):
-- UPDATE machines SET poste_id = (SELECT id FROM postes WHERE name = 'machine') WHERE name LIKE '%BL%';
-- UPDATE machines SET poste_id = (SELECT id FROM postes WHERE name = 'laveuse') WHERE name LIKE '%Laveuse%';
-- UPDATE machines SET poste_id = (SELECT id FROM postes WHERE name = 'emballage') WHERE name LIKE '%emballage%';

-- Make poste_id NOT NULL after populating data (optional)
-- ALTER TABLE machines MODIFY COLUMN poste_id INT NOT NULL; 