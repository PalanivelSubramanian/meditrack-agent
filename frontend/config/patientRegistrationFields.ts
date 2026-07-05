export type PatientRegistrationField = {
  name: string;
  label: string;
  type: "text" | "date" | "tel" | "select";
  required: boolean;
  placeholder?: string;
  options?: string[];
};

export const patientRegistrationFields: PatientRegistrationField[] = [
  {
    name: "first_name",
    label: "First name",
    type: "text",
    required: true,
    placeholder: "Example: Palanivel",
  },
  {
    name: "last_name",
    label: "Last name",
    type: "text",
    required: true,
    placeholder: "Example: Subramanian",
  },
  {
    name: "date_of_birth",
    label: "Date of birth",
    type: "date",
    required: true,
  },
  {
    name: "gender",
    label: "Gender",
    type: "select",
    required: true,
    options: ["male", "female", "other", "unknown"],
  },
  {
    name: "phone",
    label: "Phone number",
    type: "tel",
    required: true,
    placeholder: "Example: 9876543210",
  },
];