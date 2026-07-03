export type PatientHistoryPatient = {
  patient_id: number;
  patient_number: string;
  full_name: string;
  date_of_birth: string | null;
  gender: string | null;
  phone_ending: string | null;
};

export type PatientHistoryVisit = {
  id: number;
  visit_date: string;
  visit_type: string;
  reason_for_visit: string | null;
  summary: string | null;
  doctor_name: string | null;
};

export type PatientHistoryDiagnosis = {
  id: number;
  diagnosis_name: string;
  diagnosis_code: string | null;
  status: string;
  diagnosed_on: string | null;
};

export type PatientHistoryMedication = {
  id: number;
  medication_name: string;
  dosage: string | null;
  frequency: string | null;
  route: string | null;
  start_date: string | null;
  end_date: string | null;
  status: string;
};

export type PatientHistoryNote = {
  id: number;
  note_type: string;
  note_preview: string;
  created_at: string;
  doctor_name: string | null;
};

export type PatientHistoryUIData = {
  patient: PatientHistoryPatient;
  recent_visits: PatientHistoryVisit[];
  active_diagnoses: PatientHistoryDiagnosis[];
  current_medications: PatientHistoryMedication[];
  clinical_notes: PatientHistoryNote[];
};