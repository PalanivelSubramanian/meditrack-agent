import type { ChatUI, PatientHistoryUIData } from "@/types/chat";

type Props = {
  ui: ChatUI;
  onSendMessage?: (message: string) => void;
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


function PatientHistoryCard({ data }: { data: PatientHistoryUIData }) {
  return (
    <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
      <div className="mb-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
          Patient history
        </div>

        <div className="mt-1 text-lg font-semibold">
          {data.patient.full_name}
        </div>

        <div className="text-xs text-blue-800">
          {data.patient.patient_number}
          {data.patient.date_of_birth
            ? ` · DOB ${data.patient.date_of_birth}`
            : ""}
          {data.patient.phone_ending
            ? ` · Phone ending ${data.patient.phone_ending}`
            : ""}
        </div>
      </div>

      <div className="space-y-4">
        <section>
          <div className="mb-2 font-semibold">Recent visits</div>

          {data.recent_visits.length === 0 ? (
            <div className="text-blue-800">No recent visits found.</div>
          ) : (
            <div className="space-y-2">
              {data.recent_visits.map((visit) => (
                <div
                  key={visit.id}
                  className="rounded-xl border border-blue-100 bg-white p-3"
                >
                  <div className="font-medium">
                    {visit.visit_date} · {visit.visit_type}
                  </div>

                  {visit.doctor_name && (
                    <div className="text-xs text-blue-700">
                      Doctor: {visit.doctor_name}
                    </div>
                  )}

                  {visit.reason_for_visit && (
                    <div className="mt-1 text-blue-900">
                      Reason: {visit.reason_for_visit}
                    </div>
                  )}

                  {visit.summary && (
                    <div className="mt-1 text-blue-800">
                      {visit.summary}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-2 font-semibold">Active diagnoses</div>

          {data.active_diagnoses.length === 0 ? (
            <div className="text-blue-800">No active diagnoses found.</div>
          ) : (
            <div className="space-y-2">
              {data.active_diagnoses.map((diagnosis) => (
                <div
                  key={diagnosis.id}
                  className="rounded-xl border border-blue-100 bg-white p-3"
                >
                  <div className="font-medium">
                    {diagnosis.diagnosis_name}
                  </div>

                  <div className="text-xs text-blue-700">
                    Status: {diagnosis.status}
                    {diagnosis.diagnosis_code
                      ? ` · Code: ${diagnosis.diagnosis_code}`
                      : ""}
                    {diagnosis.diagnosed_on
                      ? ` · Since: ${diagnosis.diagnosed_on}`
                      : ""}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-2 font-semibold">Current medications</div>

          {data.current_medications.length === 0 ? (
            <div className="text-blue-800">No current medications found.</div>
          ) : (
            <div className="space-y-2">
              {data.current_medications.map((medication) => (
                <div
                  key={medication.id}
                  className="rounded-xl border border-blue-100 bg-white p-3"
                >
                  <div className="font-medium">
                    {medication.medication_name}
                  </div>

                  <div className="text-xs text-blue-700">
                    {[medication.dosage, medication.frequency, medication.route]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-2 font-semibold">Clinical notes</div>

          {data.clinical_notes.length === 0 ? (
            <div className="text-blue-800">No clinical notes found.</div>
          ) : (
            <div className="space-y-2">
              {data.clinical_notes.map((note) => (
                <div
                  key={note.id}
                  className="rounded-xl border border-blue-100 bg-white p-3"
                >
                  <div className="text-xs font-medium uppercase text-blue-700">
                    {note.note_type}
                    {note.doctor_name ? ` · ${note.doctor_name}` : ""}
                  </div>

                  <div className="mt-1 text-blue-900">
                    {note.note_preview}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function HistoryPatientMatchesCard({
  data,
  onSendMessage,
}: {
  data: any;
  onSendMessage?: (message: string) => void;
}) {
  const matches = data?.matches ?? [];

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
      <div className="mb-3 font-semibold">
        Multiple patients matched. Select the correct patient before viewing history.
      </div>

      <div className="space-y-2">
        {matches.map((patient: any) => (
          <div
            key={patient.patient_id}
            className="rounded-xl border border-amber-100 bg-white p-3"
          >
            <div className="font-medium">{patient.full_name}</div>

            <div className="text-xs text-amber-800">
              {patient.patient_number}
              {patient.date_of_birth ? ` · DOB ${patient.date_of_birth}` : ""}
              {patient.phone_ending
                ? ` · Phone ending ${patient.phone_ending}`
                : ""}
            </div>

            {onSendMessage && (
              <button
                type="button"
                onClick={() => onSendMessage(`Select ${patient.patient_number}`)}
                className="mt-3 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700"
              >
                View history
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function PatientMedicationsCard({ data }: { data: any }) {
  const patient = data.patient;
  const medications = data.current_medications ?? [];

  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
      <div className="mb-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
          Current medications
        </div>
        <div className="mt-1 text-lg font-semibold">{patient.full_name}</div>
        <div className="text-xs text-emerald-800">
          {patient.patient_number}
          {patient.date_of_birth ? ` · DOB ${patient.date_of_birth}` : ""}
        </div>
      </div>

      {medications.length === 0 ? (
        <div className="text-emerald-800">No current medications found.</div>
      ) : (
        <div className="space-y-2">
          {medications.map((medication: any) => (
            <div
              key={medication.id}
              className="rounded-xl border border-emerald-100 bg-white p-3"
            >
              <div className="font-medium">{medication.medication_name}</div>
              <div className="text-xs text-emerald-700">
                {[medication.dosage, medication.frequency, medication.route]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
              {medication.start_date && (
                <div className="mt-1 text-xs text-emerald-700">
                  Started: {medication.start_date}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PatientVisitsCard({ data }: { data: any }) {
  const patient = data.patient;
  const visits = data.recent_visits ?? [];

  return (
    <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-950">
      <div className="mb-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
          Recent visits
        </div>
        <div className="mt-1 text-lg font-semibold">{patient.full_name}</div>
        <div className="text-xs text-indigo-800">
          {patient.patient_number}
          {patient.date_of_birth ? ` · DOB ${patient.date_of_birth}` : ""}
        </div>
      </div>

      {visits.length === 0 ? (
        <div className="text-indigo-800">No recent visits found.</div>
      ) : (
        <div className="space-y-2">
          {visits.map((visit: any) => (
            <div
              key={visit.id}
              className="rounded-xl border border-indigo-100 bg-white p-3"
            >
              <div className="font-medium">
                {visit.visit_date} · {visit.visit_type}
              </div>
              {visit.doctor_name && (
                <div className="text-xs text-indigo-700">
                  Doctor: {visit.doctor_name}
                </div>
              )}
              {visit.reason_for_visit && (
                <div className="mt-1 text-indigo-900">
                  Reason: {visit.reason_for_visit}
                </div>
              )}
              {visit.summary && (
                <div className="mt-1 text-indigo-800">{visit.summary}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PatientDiagnosesCard({ data }: { data: any }) {
  const patient = data.patient;
  const diagnoses = data.active_diagnoses ?? [];

  return (
    <div className="rounded-2xl border border-purple-200 bg-purple-50 p-4 text-sm text-purple-950">
      <div className="mb-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-purple-700">
          Active diagnoses
        </div>
        <div className="mt-1 text-lg font-semibold">{patient.full_name}</div>
        <div className="text-xs text-purple-800">
          {patient.patient_number}
          {patient.date_of_birth ? ` · DOB ${patient.date_of_birth}` : ""}
        </div>
      </div>

      {diagnoses.length === 0 ? (
        <div className="text-purple-800">No active diagnoses found.</div>
      ) : (
        <div className="space-y-2">
          {diagnoses.map((diagnosis: any) => (
            <div
              key={diagnosis.id}
              className="rounded-xl border border-purple-100 bg-white p-3"
            >
              <div className="font-medium">{diagnosis.diagnosis_name}</div>
              <div className="text-xs text-purple-700">
                Status: {diagnosis.status}
                {diagnosis.diagnosis_code
                  ? ` · Code: ${diagnosis.diagnosis_code}`
                  : ""}
                {diagnosis.diagnosed_on
                  ? ` · Since: ${diagnosis.diagnosed_on}`
                  : ""}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AgentTracePanel({ trace }: { trace: any }) {
  if (!trace) {
    return null;
  }

  return (
    <details className="mt-3 rounded-xl border border-slate-200 bg-white p-3 text-xs text-slate-700">
      <summary className="cursor-pointer font-semibold text-slate-800">
        Agent trace
      </summary>

      <div className="mt-3 grid gap-2">
        {trace.intent && (
          <div>
            <span className="font-semibold">Intent:</span> {trace.intent}
          </div>
        )}

        {trace.access_status && (
          <div>
            <span className="font-semibold">Access:</span>{" "}
            {trace.access_status}
          </div>
        )}

        {trace.required_permission && (
          <div>
            <span className="font-semibold">Permission:</span>{" "}
            {trace.required_permission}
          </div>
        )}

        {trace.tool_used && (
          <div>
            <span className="font-semibold">Tool:</span> {trace.tool_used}
          </div>
        )}

        {trace.selected_patient_id && (
          <div>
            <span className="font-semibold">Selected patient ID:</span>{" "}
            {trace.selected_patient_id}
          </div>
        )}

        {trace.audit_event && (
          <div>
            <span className="font-semibold">Audit event:</span>{" "}
            {trace.audit_event}
          </div>
        )}

        {trace.workflow_result && (
          <div>
            <span className="font-semibold">Workflow result:</span>{" "}
            {trace.workflow_result}
          </div>
        )}
      </div>
    </details>
  );
}

export function DynamicAgentCard({ ui, onSendMessage }: Props) {
  switch (ui.type) {
    case "auth_required":
      return <AuthRequiredCard data={ui.data} />;

    case "patient_matches":
    case "booking_patient_matches":
      return <PatientMatchesCard data={ui.data} />;

    case "history_patient_matches":
      return (
        <HistoryPatientMatchesCard
          data={ui.data}
          onSendMessage={onSendMessage}
        />
      );

    case "patient_single_match":
      return <PatientSingleMatchCard data={ui.data} />;

    case "availability_slots":
      return <AvailabilitySlotsCard data={ui.data} />;

    case "booking_confirmed":
      return <BookingConfirmedCard data={ui.data} />;

    case "patient_history":
      return (
        <>
          <PatientHistoryCard data={ui.data as PatientHistoryUIData} />
          <AgentTracePanel trace={ui.data?.agent_trace} />
        </>
      );

    case "patient_no_match":
    case "booking_patient_no_match":
      return <SimpleStatusCard title="No patient found" data={ui.data} />;

    case "history_patient_no_match":
      return (
        <SimpleStatusCard
          title="No patient history found"
          data={ui.data}
        />
      );

    case "booking_slot_unavailable":
      return <SimpleStatusCard title="Slot unavailable" data={ui.data} />;

    case "access_denied":
      return <SimpleStatusCard title="Access denied" data={ui.data} />;

    case "patient_medications":
      return (
        <>
          <PatientMedicationsCard data={ui.data} />
          <AgentTracePanel trace={ui.data?.agent_trace} />
        </>
      );

    case "patient_visits":
      return (
        <>
          <PatientVisitsCard data={ui.data} />
          <AgentTracePanel trace={ui.data?.agent_trace} />
        </>
      );

    case "patient_diagnoses":
      return (
        <>
          <PatientDiagnosesCard data={ui.data} />
          <AgentTracePanel trace={ui.data?.agent_trace} />
        </>
      ); 

    default:
      return null;
  }
}
