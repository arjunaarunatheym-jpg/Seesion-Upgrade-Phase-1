/**
 * TestsTab Component - Extracted from ParticipantDashboard
 * Displays available tests and test results
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Play } from "lucide-react";

const TestsTab = ({
  availableTests,
  testResults,
  onTakeTest,
  onViewResult,
}) => {
  return (
    <>
      {/* Available Tests */}
      {availableTests.length > 0 && (
        <Card className="mb-6 bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-200">
          <CardHeader>
            <CardTitle>Available Tests</CardTitle>
            <CardDescription>Tests you need to complete</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {availableTests.map((test) => (
                <div
                  key={`${test.id}-${test.session_id}`}
                  data-testid={`available-test-${test.id}`}
                  className="p-4 bg-white rounded-lg border-2 border-emerald-300"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {test.test_type === "pre" ? "Pre-Test" : "Post-Test"}
                      </h3>
                      <p className="text-sm text-gray-600">{test.session_name}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {test.questions.length} questions
                      </p>
                    </div>
                    <Button
                      onClick={() => onTakeTest(test.id, test.session_id)}
                      data-testid={`take-test-${test.id}`}
                      className="bg-emerald-600 hover:bg-emerald-700"
                    >
                      <Play className="w-4 h-4 mr-2" />
                      Start Test
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Completed Tests */}
      <Card>
        <CardHeader>
          <CardTitle>Test Results</CardTitle>
          <CardDescription>View your completed test scores</CardDescription>
        </CardHeader>
        <CardContent>
          {testResults.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No test results yet</p>
          ) : (
            <div className="space-y-3">
              {testResults.map((result) => (
                <div
                  key={result.id}
                  data-testid={`test-result-${result.id}`}
                  className={`p-4 rounded-lg cursor-pointer hover:shadow-md transition-shadow ${
                    result.passed
                      ? 'bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200'
                      : 'bg-gradient-to-r from-red-50 to-orange-50 border border-red-200'
                  }`}
                  onClick={() => onViewResult(result.id)}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {result.test_type === "pre" ? "Pre-Test" : "Post-Test"}
                      </h3>
                      <p className="text-sm text-gray-600">
                        Submitted: {new Date(result.submitted_at).toLocaleDateString()}
                      </p>
                      <p className={`text-xs font-semibold mt-1 ${result.passed ? 'text-green-600' : 'text-red-600'}`}>
                        {result.passed ? "PASSED" : "FAILED"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`text-3xl font-bold ${result.passed ? 'text-green-600' : 'text-red-600'}`}>
                        {result.score.toFixed(1)}%
                      </p>
                      <p className="text-sm text-gray-600">
                        {result.correct_answers} / {result.total_questions} correct
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
};

export { TestsTab };
