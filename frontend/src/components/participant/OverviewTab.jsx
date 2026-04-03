import { CheckCircle2, Circle, ArrowRight, Clock, FileText, ClipboardCheck, Award, MessageSquare } from "lucide-react";

const OverviewTab = ({ sessions, participantAccess, availableTests, attendanceToday, vehicleDetails, user }) => {
  // Compute progress steps per session
  const getProgress = (session) => {
    const access = participantAccess[session.id] || {};
    const attendance = attendanceToday[session.id];
    const hasVehicle = vehicleDetails[session.id];
    const tests = availableTests[session.id] || [];
    const preTest = tests.find(t => t.type === "pre_test" || t.type === "pre-test");
    const postTest = tests.find(t => t.type === "post_test" || t.type === "post-test");

    return [
      { key: "verified", label: "Profile Verified", done: !!user?.profile_verified, hint: "Verify your name, IC, and contact details" },
      { key: "indemnity", label: "Indemnity Signed", done: !!user?.indemnity_accepted, hint: "Read and sign the indemnity form" },
      { key: "pretest", label: "Pre-Test", done: !!access.pre_test_completed, hint: access.pre_test_enabled ? "Your pre-test is available now" : "Pre-test will be released by your trainer" },
      { key: "attendance", label: "Training Day", done: !!attendance?.clock_in, hint: attendance?.clock_in ? `Clocked in at ${attendance.clock_in}` : "Clock in when training begins" },
      { key: "posttest", label: "Post-Test", done: !!access.post_test_completed, hint: access.post_test_enabled ? "Your post-test is available now" : "Post-test will be released after training" },
      { key: "feedback", label: "Feedback", done: !!access.feedback_completed, hint: access.feedback_enabled ? "Please submit your course feedback" : "Feedback form will be available after training" },
      { key: "certificate", label: "Certificate", done: !!access.certificate_issued, hint: access.certificate_issued ? "Your certificate is ready to download" : "Certificate will be issued after completion" },
    ];
  };

  const icons = {
    verified: <FileText className="w-4 h-4" />,
    indemnity: <ClipboardCheck className="w-4 h-4" />,
    pretest: <FileText className="w-4 h-4" />,
    attendance: <Clock className="w-4 h-4" />,
    posttest: <FileText className="w-4 h-4" />,
    feedback: <MessageSquare className="w-4 h-4" />,
    certificate: <Award className="w-4 h-4" />,
  };

  if (!sessions || sessions.length === 0) {
    return <div className="text-center py-12 text-gray-500">No active sessions found</div>;
  }

  return (
    <div className="space-y-6">
      {sessions.map((session) => {
        const steps = getProgress(session);
        const completedCount = steps.filter(s => s.done).length;
        const currentStepIdx = steps.findIndex(s => !s.done);
        const pct = Math.round((completedCount / steps.length) * 100);

        return (
          <div key={session.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {/* Session Header */}
            <div className="px-4 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 text-white">
              <h3 className="font-semibold text-sm">{session.program_name || session.name}</h3>
              <p className="text-xs opacity-90">{session.company_name} | {session.start_date ? new Date(session.start_date).toLocaleDateString("en-MY", { day: "numeric", month: "long", year: "numeric" }) : ""}</p>
            </div>

            {/* Progress Bar */}
            <div className="px-4 pt-3 pb-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-600">Your Progress</span>
                <span className="text-xs font-bold text-emerald-700">{pct}%</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
              </div>
            </div>

            {/* Steps */}
            <div className="px-4 py-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {steps.map((step, idx) => {
                  const isCurrent = idx === currentStepIdx;
                  return (
                    <div
                      key={step.key}
                      data-testid={`progress-step-${step.key}`}
                      className={`flex items-start gap-2.5 p-2.5 rounded-lg text-sm transition-all ${
                        step.done
                          ? "bg-emerald-50 text-emerald-800"
                          : isCurrent
                          ? "bg-blue-50 text-blue-800 ring-1 ring-blue-200"
                          : "bg-gray-50 text-gray-400"
                      }`}
                    >
                      <div className="mt-0.5 flex-shrink-0">
                        {step.done ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        ) : isCurrent ? (
                          <ArrowRight className="w-4 h-4 text-blue-600 animate-pulse" />
                        ) : (
                          <Circle className="w-4 h-4 text-gray-300" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className={`font-medium text-xs ${step.done ? "line-through opacity-70" : ""}`}>
                          {step.label}
                        </div>
                        {(isCurrent || !step.done) && (
                          <p className="text-[10px] mt-0.5 leading-tight opacity-75">{step.hint}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Training Schedule (if available) */}
            {session.schedule && session.schedule.length > 0 && (
              <div className="px-4 pb-3 border-t border-gray-100 pt-3">
                <h4 className="text-xs font-semibold text-gray-600 mb-2">Today's Schedule</h4>
                <div className="space-y-1">
                  {session.schedule.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-3 text-xs">
                      <span className="font-mono text-gray-500 w-12 flex-shrink-0">{item.time}</span>
                      <span className="text-gray-700">{item.activity}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export { OverviewTab };
