-- Phase 1: SQL Analytics Layer
-- Hospital Operations & Revenue Risk Intelligence Platform
-- Database engine: SQLite 3

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS v_department_kpis;
DROP VIEW IF EXISTS v_insurance_kpis;
DROP VIEW IF EXISTS v_city_patient_flow_kpis;
DROP VIEW IF EXISTS v_hospital_encounters;
DROP VIEW IF EXISTS v_quality_visits_without_billing;
DROP VIEW IF EXISTS v_quality_billing_without_visit;
DROP VIEW IF EXISTS v_quality_duplicate_patient_ids_raw;
DROP VIEW IF EXISTS v_quality_invalid_operational_values;
DROP VIEW IF EXISTS v_quality_missing_insurance_visits;
DROP VIEW IF EXISTS v_quality_temporal_anomalies;
DROP VIEW IF EXISTS v_quality_summary;

DROP TABLE IF EXISTS load_audit;
DROP TABLE IF EXISTS billing;
DROP TABLE IF EXISTS visits;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS raw_billing;
DROP TABLE IF EXISTS raw_visits;
DROP TABLE IF EXISTS raw_patients;

CREATE TABLE raw_patients (
    patient_id TEXT,
    age TEXT,
    gender TEXT,
    city TEXT,
    insurance_provider TEXT,
    chronic_flag TEXT,
    registration_date TEXT
);

CREATE TABLE raw_visits (
    visit_id TEXT,
    patient_id TEXT,
    visit_date TEXT,
    department TEXT,
    visit_type TEXT,
    length_of_stay_hours TEXT,
    risk_score TEXT,
    doctor_id TEXT
);

CREATE TABLE raw_billing (
    bill_id TEXT,
    visit_id TEXT,
    billed_amount TEXT,
    approved_amount TEXT,
    claim_status TEXT,
    payment_days TEXT,
    billing_date TEXT
);

CREATE TABLE patients (
    patient_id INTEGER PRIMARY KEY,
    age INTEGER NOT NULL CHECK (age BETWEEN 0 AND 120),
    gender TEXT NOT NULL CHECK (gender IN ('M', 'F')),
    city TEXT NOT NULL CHECK (TRIM(city) <> ''),
    insurance_provider TEXT,
    chronic_flag INTEGER NOT NULL CHECK (chronic_flag IN (0, 1)),
    registration_date TEXT NOT NULL CHECK (registration_date GLOB '????-??-??')
);

CREATE TABLE visits (
    visit_id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    visit_date TEXT NOT NULL CHECK (visit_date GLOB '????-??-??'),
    department TEXT NOT NULL CHECK (TRIM(department) <> ''),
    visit_type TEXT NOT NULL CHECK (visit_type IN ('OPD', 'ER', 'ICU')),
    length_of_stay_hours REAL NOT NULL CHECK (length_of_stay_hours >= 0),
    risk_score TEXT NOT NULL CHECK (risk_score IN ('Low', 'Medium', 'High')),
    doctor_id INTEGER NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE billing (
    bill_id INTEGER PRIMARY KEY,
    visit_id INTEGER NOT NULL UNIQUE,
    billed_amount REAL NOT NULL CHECK (billed_amount >= 0),
    approved_amount REAL CHECK (
        approved_amount IS NULL
        OR (approved_amount >= 0 AND approved_amount <= billed_amount)
    ),
    claim_status TEXT NOT NULL CHECK (claim_status IN ('Paid', 'Pending', 'Rejected')),
    payment_days INTEGER CHECK (payment_days IS NULL OR payment_days >= 0),
    billing_date TEXT NOT NULL CHECK (billing_date GLOB '????-??-??'),
    FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE load_audit (
    table_name TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    loaded_at_utc TEXT NOT NULL
);

CREATE INDEX idx_patients_city ON patients(city);
CREATE INDEX idx_patients_insurance_provider ON patients(insurance_provider);
CREATE INDEX idx_patients_registration_date ON patients(registration_date);

CREATE INDEX idx_visits_patient_id ON visits(patient_id);
CREATE INDEX idx_visits_visit_date ON visits(visit_date);
CREATE INDEX idx_visits_department ON visits(department);
CREATE INDEX idx_visits_visit_type ON visits(visit_type);
CREATE INDEX idx_visits_risk_score ON visits(risk_score);
CREATE INDEX idx_visits_doctor_id ON visits(doctor_id);
CREATE INDEX idx_visits_department_risk ON visits(department, risk_score);
CREATE INDEX idx_visits_doctor_risk ON visits(doctor_id, risk_score);

CREATE INDEX idx_billing_visit_id ON billing(visit_id);
CREATE INDEX idx_billing_claim_status ON billing(claim_status);
CREATE INDEX idx_billing_billing_date ON billing(billing_date);
CREATE INDEX idx_billing_payment_days ON billing(payment_days);
CREATE INDEX idx_billing_billed_amount ON billing(billed_amount);
CREATE INDEX idx_billing_claim_payment ON billing(claim_status, payment_days);
