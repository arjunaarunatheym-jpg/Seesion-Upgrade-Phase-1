import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { ArrowLeft, Send, CheckCircle } from "lucide-react";

const FeedbackForm = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [responses, setResponses] = useState({});
  const [alreadySubmitted, setAlreadySubmitted] = useState(false);

  useEffect(() => {
    loadData();
  }, [sessionId]);

  const loadData = async () => {
    try {
      // Load session details
      const sessionResponse = await axiosInstance.get(`/sessions/${sessionId}`);
      setSession(sessionResponse.data);
      
      // Check if participant has already submitted feedback
      try {
        const accessResponse = await axiosInstance.get(`/participant-access/${sessionId}`);
        if (accessResponse.data && accessResponse.data.feedback_completed) {
          setAlreadySubmitted(true);
          toast.info("Anda telah menghantar maklum balas untuk sesi ini.");
        }
      } catch (accessError) {
        console.log("Could not check feedback status");
      }
      
      // Load feedback questions from admin settings
      const questionsResponse = await axiosInstance.get("/settings/feedback-questions");
      const feedbackQuestions = questionsResponse.data || [];
      setQuestions(feedbackQuestions);
      
      // Initialize responses
      const initialResponses = {};
      feedbackQuestions.forEach((q) => {
        initialResponses[q.id] = q.type === "rating" ? 0 : "";
      });
      setResponses(initialResponses);
      
      setLoading(false);
    } catch (error) {
      console.error("Feedback form error:", error);
      toast.error("Gagal memuatkan borang maklum balas");
      navigate("/participant");
    }
  };

  const handleResponseChange = (questionId, value) => {
    setResponses({ ...responses, [questionId]: value });
  };

  const handleSubmit = async () => {
    // Validate required fields
    const invalidQuestion = questions.find((q) => {
      if (!q.required) return false;
      if (q.type === "rating") return responses[q.id] === 0;
      return !responses[q.id] || responses[q.id].toString().trim() === "";
    });

    if (invalidQuestion) {
      toast.error(`Sila lengkapkan soalan: ${invalidQuestion.question.substring(0, 50)}...`);
      return;
    }

    setSubmitting(true);
    try {
      const formattedResponses = questions.map((q) => ({
        question_id: q.id,
        question: q.question,
        category: q.category,
        type: q.type,
        answer: responses[q.id]
      }));

      await axiosInstance.post("/feedback/submit", {
        session_id: sessionId,
        program_id: session.program_id,
        responses: formattedResponses
      });
      
      // Set flag to trigger data reload on participant dashboard
      sessionStorage.setItem('feedbackSubmitted', 'true');
      
      toast.success("Maklum balas berjaya dihantar! Terima kasih.", { duration: 2000 });
      
      // Navigate back after short delay
      setTimeout(() => {
        navigate("/participant", { replace: true });
        window.location.reload();
      }, 1500);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Gagal menghantar maklum balas");
      setSubmitting(false);
    }
  };

  // Group questions by category
  const groupedQuestions = questions.reduce((acc, q) => {
    const category = q.category || "UMUM";
    if (!acc[category]) acc[category] = [];
    acc[category].push(q);
    return acc;
  }, {});

  const categoryOrder = ["KUALITI KURSUS", "PENYEDIA LATIHAN", "TRAINER", "UMUM"];
  const categoryLabels = {
    "KUALITI KURSUS": "A. KUALITI KURSUS",
    "PENYEDIA LATIHAN": "B. PENYEDIA LATIHAN",
    "TRAINER": "C. TRAINER",
    "UMUM": "D. UMUM"
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Memuatkan...</p>
        </div>
      </div>
    );
  }

  if (alreadySubmitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 py-8">
        <div className="max-w-2xl mx-auto px-4">
          <Card className="text-center">
            <CardContent className="py-12">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Maklum Balas Telah Dihantar</h2>
              <p className="text-gray-600 mb-6">Terima kasih kerana menghantar maklum balas anda.</p>
              <Button onClick={() => navigate("/participant")} data-testid="back-to-dashboard">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Kembali ke Dashboard
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 py-8">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="outline"
            onClick={() => navigate("/participant")}
            data-testid="back-to-dashboard"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Kembali ke Dashboard
          </Button>
          <h1 className="text-3xl font-bold text-gray-900 mt-4">Borang Maklum Balas Latihan</h1>
          <p className="text-gray-600">{session?.name}</p>
          <p className="text-sm text-gray-500 mt-1">{session?.company_name}</p>
        </div>

        {/* Instructions */}
        <Card className="mb-6 bg-blue-50 border-blue-200">
          <CardContent className="py-4">
            <p className="text-blue-800 text-sm">
              <strong>Arahan:</strong> Sila berikan penilaian anda untuk setiap soalan. 
              Skala: <strong>1</strong> (Sangat Tidak Setuju) hingga <strong>5</strong> (Sangat Setuju).
              Soalan bertanda <span className="text-red-500">*</span> adalah wajib.
            </p>
          </CardContent>
        </Card>

        {/* Questions by Category */}
        {categoryOrder.map((category) => {
          const categoryQuestions = groupedQuestions[category];
          if (!categoryQuestions || categoryQuestions.length === 0) return null;

          return (
            <Card key={category} className="mb-6" data-testid={`category-${category}`}>
              <CardHeader className="bg-gray-50 border-b">
                <CardTitle className="text-lg">{categoryLabels[category] || category}</CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-6">
                {categoryQuestions.map((question) => (
                  <div key={question.id} className="space-y-3" data-testid={`question-${question.id}`}>
                    <Label className="text-base font-medium text-gray-800 leading-relaxed">
                      <span className="text-gray-500 mr-2">{question.id}.</span>
                      {question.question}
                      {question.required && <span className="text-red-500 ml-1">*</span>}
                    </Label>
                    
                    {question.type === "rating" ? (
                      <div className="flex gap-2 flex-wrap">
                        {[1, 2, 3, 4, 5].map((num) => (
                          <button
                            key={num}
                            onClick={() => handleResponseChange(question.id, num)}
                            className={`w-12 h-12 rounded-lg font-bold text-lg transition-all border-2 ${
                              responses[question.id] === num
                                ? "bg-blue-600 text-white border-blue-600 shadow-lg scale-105"
                                : "bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:bg-blue-50"
                            }`}
                            type="button"
                            data-testid={`rating-${question.id}-${num}`}
                          >
                            {num}
                          </button>
                        ))}
                        <span className="ml-3 text-sm text-gray-500 self-center">
                          {responses[question.id] > 0 ? (
                            <span className="text-blue-600 font-medium">{responses[question.id]}/5</span>
                          ) : (
                            "Belum dipilih"
                          )}
                        </span>
                      </div>
                    ) : (
                      <Textarea
                        value={responses[question.id] || ""}
                        onChange={(e) => handleResponseChange(question.id, e.target.value)}
                        placeholder="Sila masukkan pandangan anda..."
                        rows={3}
                        className="w-full"
                        data-testid={`text-${question.id}`}
                      />
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}

        {/* Submit Button */}
        <div className="flex justify-end gap-4 mb-8">
          <Button
            variant="outline"
            onClick={() => navigate("/participant")}
          >
            Batal
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting}
            className="bg-blue-600 hover:bg-blue-700 px-8"
            data-testid="submit-feedback-btn"
          >
            {submitting ? (
              <>
                <span className="animate-spin mr-2">⏳</span>
                Menghantar...
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                Hantar Maklum Balas
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackForm;
