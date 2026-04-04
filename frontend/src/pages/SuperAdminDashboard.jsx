import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { LogOut, Search, Edit, Trash2, Eye, CheckCircle, XCircle, Clock, AlertCircle, FileText, ClipboardList, MessageSquare, Pen } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import SuperAdminPanel from "../components/SuperAdminPanel";
import { DigitalSignatureManager } from "../components/shared/DigitalSignatureManager";

const SuperAdminDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { primaryColor, secondaryColor, companyName, logoUrl } = useTheme();
  
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState("session");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Edit dialogs
  const [editParticipantOpen, setEditParticipantOpen] = useState(false);
  const [editingParticipant, setEditingParticipant] = useState(null);
  const [editForm, setEditForm] = useState({
    full_name: "",
    id_number: "",
    email: ""
  });

  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Test/Checklist/Feedback editing
  const [editTestOpen, setEditTestOpen] = useState(false);
  const [editingTest, setEditingTest] = useState(null);
  const [testForm, setTestForm] = useState({ score: 0, passed: false });

  const [editChecklistOpen, setEditChecklistOpen] = useState(false);
  const [checklistForm, setChecklistForm] = useState({ items: [] });

  const [editFeedbackOpen, setEditFeedbackOpen] = useState(false);
  const [feedbackForm, setFeedbackForm] = useState({ responses: [] });

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error("Please enter a search query");
      return;
    }

    setLoading(true);
    try {
      let response;
      if (searchType === "session") {
        response = await axiosInstance.get("/sessions", {
          params: { search: searchQuery }
        });
        setSearchResults(response.data);
      } else if (searchType === "company") {
        const companiesRes = await axiosInstance.get("/companies");
        const filtered = companiesRes.data.filter(c => 
          c.name.toLowerCase().includes(searchQuery.toLowerCase())
        );
        
        if (filtered.length > 0) {
          const sessionsRes = await axiosInstance.get("/sessions", {
            params: { company_id: filtered[0].id }
          });
          setSearchResults(sessionsRes.data);
        } else {
          setSearchResults([]);
          toast.info("No companies found");
        }
      } else if (searchType === "participant") {
        const usersRes = await axiosInstance.get("/users");
        const filtered = usersRes.data.filter(u => 
          u.role === "participant" && 
          (u.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
           u.id_number?.toLowerCase().includes(searchQuery.toLowerCase()))
        );
        
        if (filtered.length > 0) {
          const allSessions = await axiosInstance.get("/sessions");
          const participantSessions = allSessions.data.filter(s => 
            filtered.some(p => s.participant_ids?.includes(p.id))
          );
          setSearchResults(participantSessions);
        } else {
          setSearchResults([]);
          toast.info("No participants found");
        }
      }
      
      toast.success(`Found ${searchResults.length} result(s)`);
    } catch (error) {
      toast.error("Search failed");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSession = async (session) => {
    setSelectedSession(session);
    setLoading(true);
    
    try {
      const response = await axiosInstance.get(`/sessions/${session.id}/participants`);
      
      // Enrich with test results and checklist status
      const enriched = await Promise.all(response.data.map(async (p) => {
        const participantUser = p.user || p;
        
        try {
          // Get test results
          const testsRes = await axiosInstance.get(`/tests/results/participant/${participantUser.id}`);
          const sessionTests = testsRes.data.filter(t => t.session_id === session.id);
          const preTest = sessionTests.find(t => t.test_type === "pre");
          const postTest = sessionTests.find(t => t.test_type === "post");
          
          // Get checklist status
          const checklistRes = await axiosInstance.get(`/vehicle-checklists/${session.id}/${participantUser.id}`);
          
          // Get feedback
          const feedbackRes = await axiosInstance.get(`/feedback/session/${session.id}/participant/${participantUser.id}`).catch(() => ({ data: [] }));
          
          return {
            ...participantUser,
            sessionId: session.id,
            preTest: preTest ? { ...preTest, completed: true } : { completed: false },
            postTest: postTest ? { ...postTest, completed: true } : { completed: false },
            checklistStatus: checklistRes.data?.length > 0 ? "completed" : "pending",
            checklistData: checklistRes.data || [],
            feedbackData: feedbackRes.data || null
          };
        } catch (error) {
          return {
            ...participantUser,
            sessionId: session.id,
            preTest: { completed: false },
            postTest: { completed: false },
            checklistStatus: "pending",
            checklistData: [],
            feedbackData: null
          };
        }
      }));
      
      setParticipants(enriched);
    } catch (error) {
      toast.error("Failed to load participants");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleEditParticipant = (participant) => {
    setEditingParticipant(participant);
    setEditForm({
      full_name: participant.full_name,
      id_number: participant.id_number,
      email: participant.email || ""
    });
    setEditParticipantOpen(true);
  };

  const handleSaveParticipant = async () => {
    try {
      await axiosInstance.put(`/users/${editingParticipant.id}`, editForm);
      toast.success("Participant updated successfully");
      setEditParticipantOpen(false);
      
      if (selectedSession) {
        handleSelectSession(selectedSession);
      }
    } catch (error) {
      toast.error("Failed to update participant");
      console.error(error);
    }
  };

  const handleDeleteParticipant = async () => {
    try {
      await axiosInstance.delete(`/users/${deleteTarget.id}`);
      toast.success("Participant deleted successfully");
      setDeleteConfirmOpen(false);
      setDeleteTarget(null);
      
      if (selectedSession) {
        handleSelectSession(selectedSession);
      }
    } catch (error) {
      toast.error("Failed to delete participant");
      console.error(error);
    }
  };

  const handleEditTest = (participant, testType) => {
    setEditingTest({ participant, testType });
    const testData = testType === "pre" ? participant.preTest : participant.postTest;
    setTestForm({
      score: testData.score || 0,
      passed: testData.passed || false
    });
    setEditTestOpen(true);
  };

  const handleSaveTest = async () => {
    try {
      const { participant, testType } = editingTest;
      const testData = testType === "pre" ? participant.preTest : participant.postTest;
      
      if (testData.completed && testData.id) {
        // Update existing test result
        await axiosInstance.put(`/tests/results/${testData.id}`, {
          score: parseFloat(testForm.score),
          passed: testForm.passed
        });
      } else {
        // Create new test result
        const program = await axiosInstance.get(`/sessions/${participant.sessionId}`);
        const tests = await axiosInstance.get(`/tests/program/${program.data.program_id}`);
        const test = tests.data.find(t => t.test_type === testType);
        
        if (!test) {
          toast.error(`No ${testType}-test found for this program`);
          return;
        }
        
        await axiosInstance.post("/tests/submit", {
          test_id: test.id,
          session_id: participant.sessionId,
          participant_id: participant.id,
          answers: Array(test.questions?.length || 0).fill(0),
          score: parseFloat(testForm.score),
          passed: testForm.passed
        });
      }
      
      toast.success(`${testType === 'pre' ? 'Pre' : 'Post'}-test updated successfully`);
      setEditTestOpen(false);
      handleSelectSession(selectedSession);
    } catch (error) {
      toast.error("Failed to update test");
      console.error(error);
    }
  };

  const getStatusBadge = (status) => {
    if (status.completed) {
      return status.passed ? (
        <Badge className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" /> Passed ({status.score}%)</Badge>
      ) : (
        <Badge className="bg-red-500"><XCircle className="w-3 h-3 mr-1" /> Failed ({status.score}%)</Badge>
      );
    }
    return <Badge variant="outline"><Clock className="w-3 h-3 mr-1" /> Pending</Badge>;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            {logoUrl && (
              <img 
                src={logoUrl} 
                alt={companyName}
                className="h-10 w-auto object-contain bg-white rounded p-1"
              />
            )}
            <div>
              <h1 className="text-2xl font-bold">🔐 Super Admin Dashboard</h1>
              <p className="text-sm text-purple-100">Welcome, {user.full_name}</p>
            </div>
          </div>
          <Button
            onClick={onLogout}
            variant="outline"
            className="bg-white text-purple-600 hover:bg-purple-50"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs defaultValue="search" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="search" data-testid="search-tab">Search & Manage</TabsTrigger>
            <TabsTrigger value="sessions" data-testid="sessions-tab">Sessions</TabsTrigger>
            <TabsTrigger value="signature" data-testid="signature-tab">
              <Pen className="w-4 h-4 mr-2" />Signature
            </TabsTrigger>
          </TabsList>

          <TabsContent value="search" className="mt-6">
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Search className="w-5 h-5 mr-2" />
                  Advanced Search
                </CardTitle>
                <CardDescription>
                  Search by session, company, or participant to manage training data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <Select value={searchType} onValueChange={setSearchType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="session">Session</SelectItem>
                      <SelectItem value="company">Company</SelectItem>
                      <SelectItem value="participant">Participant</SelectItem>
                    </SelectContent>
                  </Select>

                  <div className="md:col-span-2">
                    <Input
                      placeholder={`Search by ${searchType} name...`}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                    />
                  </div>

                  <Button 
                    onClick={handleSearch} 
                    disabled={loading}
                    className="bg-gradient-to-r from-purple-600 to-pink-600"
                  >
                    <Search className="w-4 h-4 mr-2" />
                    Search
                  </Button>
                </div>
              </CardContent>
            </Card>

            {searchResults.length > 0 && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Search Results ({searchResults.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {searchResults.map((session) => (
                      <Card
                        key={session.id}
                        className={`cursor-pointer transition-all ${
                          selectedSession?.id === session.id ? "ring-2 ring-purple-500" : "hover:shadow-md"
                        }`}
                        onClick={() => handleSelectSession(session)}
                      >
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start">
                            <div>
                              <h3 className="font-semibold text-lg">{session.company_name || "Unknown Company"}</h3>
                              <p className="text-sm text-gray-600">{session.program_name || "Unknown Program"}</p>
                              <p className="text-xs text-gray-500 mt-1">
                                {session.start_date} to {session.end_date} • {session.location}
                              </p>
                            </div>
                            <Badge variant={selectedSession?.id === session.id ? "default" : "outline"}>
                              {session.participant_ids?.length || 0} Participants
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {selectedSession && (
              <Card>
                <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50">
                  <CardTitle>
                    Participants in {selectedSession.company_name} - {selectedSession.program_name}
                  </CardTitle>
                  <CardDescription>
                    View and manage participant progress, tests, and checklists
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-6">
                  {loading ? (
                    <div className="text-center py-8">Loading participants...</div>
                  ) : participants.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">No participants found</div>
                  ) : (
                    <div className="space-y-4">
                      {participants.map((participant) => (
                        <Card key={participant.id} className="bg-gray-50">
                          <CardContent className="p-4">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <h4 className="font-semibold text-lg">{participant.full_name}</h4>
                                <p className="text-sm text-gray-600">IC: {participant.id_number}</p>
                                {participant.email && (
                                  <p className="text-sm text-gray-600">Email: {participant.email}</p>
                                )}
                                
                                <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
                                  <div>
                                    <Label className="text-xs">Pre-Test:</Label>
                                    <div className="mt-1 flex gap-2 items-center">
                                      {getStatusBadge(participant.preTest)}
                                      <Button size="sm" variant="ghost" onClick={() => handleEditTest(participant, "pre")}>
                                        <Edit className="w-3 h-3" />
                                      </Button>
                                    </div>
                                  </div>
                                  <div>
                                    <Label className="text-xs">Post-Test:</Label>
                                    <div className="mt-1 flex gap-2 items-center">
                                      {getStatusBadge(participant.postTest)}
                                      <Button size="sm" variant="ghost" onClick={() => handleEditTest(participant, "post")}>
                                        <Edit className="w-3 h-3" />
                                      </Button>
                                    </div>
                                  </div>
                                  <div>
                                    <Label className="text-xs">Checklist:</Label>
                                    <div className="mt-1">
                                      {participant.checklistStatus === "completed" ? (
                                        <Badge className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" /> Completed</Badge>
                                      ) : (
                                        <Badge variant="outline"><Clock className="w-3 h-3 mr-1" /> Pending</Badge>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditParticipant(participant)}
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => {
                                    setDeleteTarget(participant);
                                    setDeleteConfirmOpen(true);
                                  }}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="sessions" className="mt-6">
            <SuperAdminPanel />
          </TabsContent>

          <TabsContent value="signature" className="mt-6">
            <DigitalSignatureManager user={user} />
          </TabsContent>
        </Tabs>
      </main>

      {/* Edit Participant Dialog */}
      <Dialog open={editParticipantOpen} onOpenChange={setEditParticipantOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Participant</DialogTitle>
            <DialogDescription>
              Update participant information
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Full Name</Label>
              <Input
                value={editForm.full_name}
                onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
              />
            </div>
            <div>
              <Label>IC Number</Label>
              <Input
                value={editForm.id_number}
                onChange={(e) => setEditForm({ ...editForm, id_number: e.target.value })}
              />
            </div>
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              />
            </div>
            <Button onClick={handleSaveParticipant} className="w-full">
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Test Dialog */}
      <Dialog open={editTestOpen} onOpenChange={setEditTestOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit {editingTest?.testType === 'pre' ? 'Pre' : 'Post'}-Test Result</DialogTitle>
            <DialogDescription>
              Update test score and pass/fail status
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Score (%)</Label>
              <Input
                type="number"
                min="0"
                max="100"
                value={testForm.score}
                onChange={(e) => setTestForm({ ...testForm, score: e.target.value })}
              />
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="passed"
                checked={testForm.passed}
                onChange={(e) => setTestForm({ ...testForm, passed: e.target.checked })}
                className="w-4 h-4"
              />
              <Label htmlFor="passed">Passed</Label>
            </div>
            <Button onClick={handleSaveTest} className="w-full">
              Save Test Result
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center text-red-600">
              <AlertCircle className="w-5 h-5 mr-2" />
              Confirm Delete
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteTarget?.full_name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteParticipant}>
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SuperAdminDashboard;