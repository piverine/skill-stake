-- Initialize the database with extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE stake_status AS ENUM ('PENDING', 'ACTIVE', 'SETTLED');
CREATE TYPE settlement_type AS ENUM ('RETURNED', 'DONATED');
CREATE TYPE processing_status AS ENUM ('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED');