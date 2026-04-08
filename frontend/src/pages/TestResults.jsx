import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, XCircle, Award, TrendingUp } from "lucide-react";

const TestResults = () => {
  const { resultId } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadResult();
  }, [resultId]);

  const loadResult = async () => {
    try {
      const response = await axiosInstance.get(`/tests/results/${resultId}`);
      setResult(response.data);
      setLoading(false);
    } catch (error) {
      toast.error("Failed to load test results");
      navigate("/dashboard");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-lg">Loading results...</p>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="outline"
            onClick={() => navigate("/dashboard")}
            data-testid="back-to-dashboard"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
        </div>

        {/* Result Summary */}
        <Card className={`mb-6 ${result.passed ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200' : 'bg-gradient-to-r from-red-50 to-orange-50 border-red-200'}`}>
          <CardHeader>
            <div className="flex items-center gap-4">
              {result.passed ? (
                <CheckCircle2 className="w-16 h-16 text-green-600" />
              ) : (
                <XCircle className="w-16 h-16 text-red-600" />
              )}
              <div className="flex-1">
                <CardTitle className="text-3xl mb-2">
                  {result.passed ? "Congratulations! You Passed!" : "Test Not Passed"}
                </CardTitle>
                <CardDescription className="text-lg">
                  {result.test_type === "pre" ? "Pre-Test" : "Post-Test"} Results
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-white rounded-lg">
                <div className="flex items-center justify-center mb-2">
                  <TrendingUp className="w-5 h-5 text-blue-600 mr-2" />
                  <p className="text-sm text-gray-600">Score</p>
                </div>
                <p className="text-4xl font-bold text-blue-600">{result.score.toFixed(1)}%</p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg">
                <div className="flex items-center justify-center mb-2">
                  <CheckCircle2 className="w-5 h-5 text-green-600 mr-2" />
                  <p className="text-sm text-gray-600">Correct</p>
                </div>
                <p className="text-4xl font-bold text-green-600">
                  {result.correct_answers} / {result.total_questions}
                </p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg">
                <div className="flex items-center justify-center mb-2">
                  <Award className="w-5 h-5 text-purple-600 mr-2" />
                  <p className="text-sm text-gray-600">Status</p>
                </div>
                <p className={`text-2xl font-bold ${result.passed ? 'text-green-600' : 'text-red-600'}`}>
                  {result.passed ? "PASSED" : "FAILED"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Question Review */}
        <Card>
          <CardHeader>
            <CardTitle>Question Review</CardTitle>
            <CardDescription>Review your answers and the correct answers</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {result.test_questions && result.test_questions.map((question, qIndex) => {
                const userAnswer = Number(result.answers[qIndex]);
                const correctAnswer = Number(question.correct_answer);
                const isCorrect = userAnswer === correctAnswer;

                return (
                  <div
                    key={qIndex}
                    data-testid={`result-question-${qIndex}`}
                    className={`p-4 rounded-lg border-2 ${
                      isCorrect ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                    }`}
                  >
                    <div className="flex items-start gap-3 mb-3">
                      {isCorrect ? (
                        <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                      ) : (
                        <XCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-1" />
                      )}
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 mb-2">
                          Question {qIndex + 1}: {question.question}
                        </h3>
                        
                        {/* Options */}
                        <div className="space-y-2">
                          {question.options.map((option, optIndex) => {
                            const isUserAnswer = userAnswer === optIndex;
                            const isCorrectOption = correctAnswer === optIndex;
                            
                            let bgColor = "bg-white";
                            let textColor = "text-gray-900";
                            let badge = "";
                            
                            if (isCorrectOption) {
                              bgColor = "bg-green-100";
                              textColor = "text-green-900 font-medium";
                              badge = "✓ Correct Answer";
                            }
                            
                            if (isUserAnswer && !isCorrect) {
                              bgColor = "bg-red-100";
                              textColor = "text-red-900";
                              badge = "✗ Your Answer";
                            }

                            return (
                              <div
                                key={optIndex}
                                className={`p-3 rounded ${bgColor} ${textColor}`}
                              >
                                <div className="flex items-center justify-between">
                                  <span>
                                    <span className="font-semibold mr-2">
                                      {String.fromCharCode(65 + optIndex)}.
                                    </span>
                                    {typeof option === 'string' ? option : option.text}
                                  </span>
                                  {badge && (
                                    <span className="text-xs font-semibold">{badge}</span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Bottom Summary */}
        <Card className="mt-6">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-gray-600 mb-4">
                Submitted on {new Date(result.submitted_at).toLocaleString()}
              </p>
              <Button
                onClick={() => navigate("/dashboard")}
                size="lg"
                data-testid="return-dashboard-button"
              >
                Return to Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default TestResults;
