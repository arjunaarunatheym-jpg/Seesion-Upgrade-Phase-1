/**
 * ProgramsTab Component - Extracted from AdminDashboard
 * Manages training programs with tests, checklists, and feedback forms
 */
import { useState } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { BookOpen, Edit, Trash2, ClipboardList, ClipboardCheck, MessageSquare } from "lucide-react";
import { SearchBar } from "../SearchBar";
import TestManagement from "../../pages/TestManagement";
import FeedbackManagement from "../../pages/FeedbackManagement";
import ChecklistManagement from "../../pages/ChecklistManagement";

const ProgramsTab = ({ 
  programs, 
  filteredPrograms, 
  onSearch, 
  onRefresh,
  onDeleteClick 
}) => {
  const [programForm, setProgramForm] = useState({ name: "", description: "", pass_percentage: 70, certificate_title: "", certificate_subtitle: "" });
  const [programDialogOpen, setProgramDialogOpen] = useState(false);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [editingProgram, setEditingProgram] = useState(null);
  const [editProgramDialogOpen, setEditProgramDialogOpen] = useState(false);

  const handleCreateProgram = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/programs", programForm);
      toast.success("Program created successfully");
      setProgramForm({ name: "", description: "", pass_percentage: 70, certificate_title: "", certificate_subtitle: "" });
      setProgramDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create program");
    }
  };

  const handleEditProgram = (program) => {
    setEditingProgram({ ...program });
    setEditProgramDialogOpen(true);
  };

  const handleUpdateProgram = async () => {
    try {
      await axiosInstance.put(`/programs/${editingProgram.id}`, {
        name: editingProgram.name,
        description: editingProgram.description,
        pass_percentage: editingProgram.pass_percentage,
        certificate_title: editingProgram.certificate_title || null,
        certificate_subtitle: editingProgram.certificate_subtitle || null,
      });
      toast.success("Program updated successfully");
      setEditProgramDialogOpen(false);
      setEditingProgram(null);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update program");
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Training Programs</CardTitle>
              <CardDescription>Manage your training modules</CardDescription>
            </div>
            <Dialog open={programDialogOpen} onOpenChange={setProgramDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="create-program-button">
                  <BookOpen className="w-4 h-4 mr-2" />
                  Add Program
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create New Program</DialogTitle>
                  <DialogDescription>
                    Add a new training program/module
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateProgram} className="space-y-4">
                  <div>
                    <Label htmlFor="program-name">Program Name *</Label>
                    <Input
                      id="program-name"
                      data-testid="program-name-input"
                      placeholder="e.g., Defensive Riding"
                      value={programForm.name}
                      onChange={(e) => setProgramForm({ ...programForm, name: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="program-description">Description (Optional)</Label>
                    <Textarea
                      id="program-description"
                      data-testid="program-description-input"
                      placeholder="Brief description of the program"
                      value={programForm.description}
                      onChange={(e) => setProgramForm({ ...programForm, description: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="pass-percentage">Pass Percentage (%)</Label>
                    <Input
                      id="pass-percentage"
                      data-testid="pass-percentage-input"
                      type="number"
                      min="0"
                      max="100"
                      value={programForm.pass_percentage}
                      onChange={(e) => setProgramForm({ ...programForm, pass_percentage: parseFloat(e.target.value) })}
                      required
                    />
                  </div>
                  <div className="border-t pt-4 mt-2">
                    <p className="text-xs text-gray-500 mb-3">Certificate Display Settings (used on auto-generated certificates)</p>
                    <div>
                      <Label htmlFor="cert-title">Certificate Title</Label>
                      <Input
                        id="cert-title"
                        data-testid="cert-title-input"
                        placeholder="e.g., DEFENSIVE DRIVING COURSE"
                        value={programForm.certificate_title}
                        onChange={(e) => setProgramForm({ ...programForm, certificate_title: e.target.value })}
                      />
                      <p className="text-xs text-gray-400 mt-1">If blank, programme name will be used</p>
                    </div>
                    <div className="mt-2">
                      <Label htmlFor="cert-subtitle">Certificate Subtitle</Label>
                      <Input
                        id="cert-subtitle"
                        data-testid="cert-subtitle-input"
                        placeholder="e.g., > With Theory and Practical Training >"
                        value={programForm.certificate_subtitle}
                        onChange={(e) => setProgramForm({ ...programForm, certificate_subtitle: e.target.value })}
                      />
                    </div>
                  </div>
                  <Button data-testid="submit-program-button" type="submit" className="w-full">
                    Create Program
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <SearchBar
              placeholder="Search programs by name or description..."
              onSearch={onSearch}
              className="max-w-md"
            />
          </div>
          <div className="space-y-2">
            {filteredPrograms.length === 0 ? (
              <div className="text-center py-12">
                <BookOpen className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-500">
                  {programs.length === 0 ? "No programs yet. Create your first training program!" : "No programs match your search."}
                </p>
              </div>
            ) : (
              filteredPrograms.map((program) => (
                <div key={program.id} className="mb-4">
                  <Card>
                    <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 overflow-hidden">
                      <div className="flex flex-col sm:flex-row justify-between items-start gap-2">
                        <div className="flex-1 min-w-0 w-full">
                          <CardTitle className="text-sm sm:text-base break-words leading-snug">{program.name}</CardTitle>
                          {program.description && (
                            <CardDescription className="text-xs break-words">{program.description}</CardDescription>
                          )}
                          <div className="flex flex-wrap gap-2 mt-2">
                            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                              Pass: {program.pass_percentage}%
                            </span>
                            {program.certificate_title && (
                              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded truncate max-w-[150px]">
                                Cert: {program.certificate_title}
                              </span>
                            )}
                            <span className="text-xs text-gray-500">
                              {new Date(program.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleEditProgram(program)}
                          >
                            <Edit className="w-4 h-4 mr-1" />
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => onDeleteClick("program", program)}
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-3 px-3 sm:px-6">
                      <div className="flex gap-2 flex-wrap">
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs flex-1 sm:flex-none"
                          onClick={() => setSelectedProgram(selectedProgram?.id === program.id ? null : program)}
                        >
                          <ClipboardList className="w-3.5 h-3.5 mr-1" />
                          Tests & Checklists
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs flex-1 sm:flex-none"
                          onClick={() => {
                            if (selectedProgram?.id === program.id) {
                              setSelectedProgram(null);
                            } else {
                              setSelectedProgram(program);
                            }
                          }}
                        >
                          <MessageSquare className="w-3.5 h-3.5 mr-1" />
                          Feedback
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                  
                  {/* Expandable Management Section */}
                  {selectedProgram?.id === program.id && (
                    <Card className="mt-2 border-l-4 border-blue-500 overflow-hidden">
                      <CardContent className="pt-4 px-3 sm:px-6">
                        <Tabs defaultValue="tests" className="w-full" data-program-id={program.id}>
                          <TabsList className="grid w-full grid-cols-3 mb-4 h-auto">
                            <TabsTrigger value="tests" className="text-xs px-1 py-2">
                              <ClipboardList className="w-3.5 h-3.5 sm:mr-1.5" />
                              <span className="hidden sm:inline">Tests</span>
                              <span className="sm:hidden">Tests</span>
                            </TabsTrigger>
                            <TabsTrigger value="checklists" className="text-xs px-1 py-2">
                              <ClipboardCheck className="w-3.5 h-3.5 sm:mr-1.5" />
                              <span>Checklists</span>
                            </TabsTrigger>
                            <TabsTrigger value="feedback-form" className="text-xs px-1 py-2">
                              <MessageSquare className="w-3.5 h-3.5 sm:mr-1.5" />
                              <span>Feedback</span>
                            </TabsTrigger>
                          </TabsList>
                          
                          <TabsContent value="tests">
                            <div className="mb-4">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setSelectedProgram(null)}
                              >
                                ← Back to Programs
                              </Button>
                            </div>
                            <TestManagement program={program} />
                          </TabsContent>
                          
                          <TabsContent value="checklists">
                            <div className="mb-4">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setSelectedProgram(null)}
                              >
                                ← Back to Programs
                              </Button>
                            </div>
                            <ChecklistManagement program={program} />
                          </TabsContent>
                          
                          <TabsContent value="feedback-form">
                            <div className="mb-4">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setSelectedProgram(null)}
                              >
                                ← Back to Programs
                              </Button>
                            </div>
                            <FeedbackManagement program={program} />
                          </TabsContent>
                        </Tabs>
                      </CardContent>
                    </Card>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Edit Program Dialog */}
      <Dialog open={editProgramDialogOpen} onOpenChange={setEditProgramDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Program</DialogTitle>
            <DialogDescription>
              Update program details
            </DialogDescription>
          </DialogHeader>
          {editingProgram && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="edit-program-name">Program Name *</Label>
                <Input
                  id="edit-program-name"
                  value={editingProgram.name}
                  onChange={(e) => setEditingProgram({ ...editingProgram, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="edit-program-description">Description</Label>
                <Textarea
                  id="edit-program-description"
                  value={editingProgram.description || ""}
                  onChange={(e) => setEditingProgram({ ...editingProgram, description: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="edit-pass-percentage">Pass Percentage (%)</Label>
                <Input
                  id="edit-pass-percentage"
                  type="number"
                  min="0"
                  max="100"
                  value={editingProgram.pass_percentage}
                  onChange={(e) => setEditingProgram({ ...editingProgram, pass_percentage: parseFloat(e.target.value) })}
                  required
                />
              </div>
              <div className="border-t pt-4 mt-2">
                <p className="text-xs text-gray-500 mb-3">Certificate Display Settings</p>
                <div>
                  <Label htmlFor="edit-cert-title">Certificate Title</Label>
                  <Input
                    id="edit-cert-title"
                    data-testid="edit-cert-title-input"
                    placeholder="e.g., DEFENSIVE DRIVING COURSE"
                    value={editingProgram.certificate_title || ""}
                    onChange={(e) => setEditingProgram({ ...editingProgram, certificate_title: e.target.value })}
                  />
                  <p className="text-xs text-gray-400 mt-1">If blank, programme name will be used</p>
                </div>
                <div className="mt-2">
                  <Label htmlFor="edit-cert-subtitle">Certificate Subtitle</Label>
                  <Input
                    id="edit-cert-subtitle"
                    data-testid="edit-cert-subtitle-input"
                    placeholder="e.g., > With Theory and Practical Training >"
                    value={editingProgram.certificate_subtitle || ""}
                    onChange={(e) => setEditingProgram({ ...editingProgram, certificate_subtitle: e.target.value })}
                  />
                </div>
              </div>
              <Button onClick={handleUpdateProgram} className="w-full">
                Update Program
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ProgramsTab;
