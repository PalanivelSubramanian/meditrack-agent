import type { ChatUI } from "@/types/chat";

type Props = {
  ui: ChatUI;
};

function CardShell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-3 rounded-xl border bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-semibold text-slate-800">{title}</div>
      {children}
    </div>
  );
}

function AuthRequiredCard({ data }: { data: Record<string, any> }) {
  return (
    <CardShell title="Staff verification required">
      <p className="text-sm text-slate-600">
        This action requires authorized clinic access.
      </p>
      <div className="mt-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
        Required permission:{" "}
        <span className="font-medium">{data.required_permission}</span>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Use the Staff Login panel to verify with Employee ID and Authenticator
        code.
      </p>
    </CardShell>
  );
}

function PatientMatchesCard({ data }: { data: Record<string, any> }) {
  const patients = data.patients || [];

  return (
    <CardShell title="Patient matches">
      <p className="mb-3 text-sm text-slate-600">
        Query: <span className="font-medium">{data.query}</span>
      </p>

      <div className="space-y-2">
        {patients.map((patient: any) => (
          <div
            key={patient.patient_id}
            className="rounded-lg border bg-slate-50 p-3"
          >
            <div className="font-medium text-slate-900">
              {patient.full_name}
            </div>
            <div className="text-sm text-slate-600">
              Patient No: {patient.patient_number}
            </div>
            <div className="text-sm text-slate-600">
              DOB: {patient.date_of_birth}
            </div>
            <div className="text-sm text-slate-600">
              Gender: {patient.gender || "Not specified"}
            </div>
            <div className="text-sm text-slate-600">
              Phone ending: {patient.phone_ending || "N/A"}
            </div>
          </div>
        ))}
      </div>
    </CardShell>
  );
}

function PatientSingleMatchCard({ data }: { data: Record<string, any> }) {
  const patient = data.selected_patient;

  if (!patient) return null;

  return (
    <CardShell title="Patient found">
      <div className="rounded-lg border bg-slate-50 p-3">
        <div className="font-medium text-slate-900">{patient.full_name}</div>
        <div className="text-sm text-slate-600">
          Patient No: {patient.patient_number}
        </div>
        <div className="text-sm text-slate-600">
          DOB: {patient.date_of_birth}
        </div>
        <div className="text-sm text-slate-600">
          Phone ending: {patient.phone_ending || "N/A"}
        </div>
      </div>
    </CardShell>
  );
}

function AvailabilitySlotsCard({ data }: { data: Record<string, any> }) {
  const slots = data.slots || [];

  return (
    <CardShell title="Available appointment slots">
      <p className="mb-3 text-sm text-slate-600">
        {data.specialization} — {data.target_date}
      </p>

      <div className="grid gap-2">
        {slots.map((slot: any, index: number) => (
          <div
            key={`${slot.doctor_id}-${slot.appointment_date}-${slot.start_time}-${index}`}
            className="rounded-lg border bg-slate-50 p-3"
          >
            <div className="font-medium text-slate-900">
              {slot.doctor_name}
            </div>
            <div className="text-sm text-slate-600">
              {slot.appointment_date}, {slot.start_time}–{slot.end_time}
            </div>
            <div className="text-sm text-slate-600">
              {slot.department} / {slot.specialization}
            </div>
          </div>
        ))}
      </div>
    </CardShell>
  );
}

function BookingConfirmedCard({ data }: { data: Record<string, any> }) {
  const patient = data.patient;
  const slot = data.slot;

  return (
    <CardShell title="Appointment booked">
      <div className="rounded-lg border bg-slate-50 p-3">
        <div className="text-sm text-slate-600">
          Appointment ID:{" "}
          <span className="font-medium">{data.appointment_id}</span>
        </div>
        {patient && (
          <div className="mt-2">
            <div className="font-medium text-slate-900">
              {patient.full_name}
            </div>
            <div className="text-sm text-slate-600">
              Patient No: {patient.patient_number}
            </div>
          </div>
        )}
        {slot && (
          <div className="mt-2 text-sm text-slate-600">
            {slot.doctor_name} — {slot.appointment_date}, {slot.start_time}–
            {slot.end_time}
          </div>
        )}
      </div>
    </CardShell>
  );
}

function SimpleStatusCard({
  title,
  data,
}: {
  title: string;
  data: Record<string, any>;
}) {
  return (
    <CardShell title={title}>
      <pre className="overflow-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
        {JSON.stringify(data, null, 2)}
      </pre>
    </CardShell>
  );
}

export function DynamicAgentCard({ ui }: Props) {
  switch (ui.type) {
    case "auth_required":
      return <AuthRequiredCard data={ui.data} />;

    case "patient_matches":
    case "booking_patient_matches":
      return <PatientMatchesCard data={ui.data} />;

    case "patient_single_match":
      return <PatientSingleMatchCard data={ui.data} />;

    case "availability_slots":
      return <AvailabilitySlotsCard data={ui.data} />;

    case "booking_confirmed":
      return <BookingConfirmedCard data={ui.data} />;

    case "patient_no_match":
    case "booking_patient_no_match":
      return <SimpleStatusCard title="No patient found" data={ui.data} />;

    case "booking_slot_unavailable":
      return <SimpleStatusCard title="Slot unavailable" data={ui.data} />;

    case "access_denied":
      return <SimpleStatusCard title="Access denied" data={ui.data} />;

    default:
      return null;
  }
}