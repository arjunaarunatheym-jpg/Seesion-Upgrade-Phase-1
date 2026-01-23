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
  const [programForm, setProgramForm] = useState({ name: "", description: "", pass_percentage: 70 });
  const [programDialogOpen, setProgramDialogOpen] = useState(false);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [editingProgram, setEditingProgram] = useState(null);
  const [editProgramDialogOpen, setEditProgramDialogOpen] = useState(false);

  const handleCreateProgram = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/programs", programForm);
      toast.success("Program created successfully");
      setProgramForm({ name: "", description: "", pass_percentage: 70 });
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
                    <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <CardTitle>{program.name}</CardTitle>
                          {program.description && (
                            <CardDescription>{program.description}</CardDescription>
                          )}
                          <div className="flex gap-3 mt-2">
                            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                              Pass Mark: {program.pass_percentage}%
                            </span>
                            <span className="text-xs text-gray-500">
                              Created: {new Date(program.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2 flex-wrap">
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
                    <CardContent className="pt-4">
                      <div className="flex gap-2 flex-wrap">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setSelectedProgram(selectedProgram?.id === program.id ? null : program)}
                        >
                          <ClipboardList className="w-4 h-4 mr-2" />
                          Manage Tests & Checklists
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            if (selectedProgram?.id === program.id) {
                              setSelectedProgram(null);
                            } else {
                              setSelectedProgram(program);
                            }
                          }}
                        >
                          <MessageSquare className="w-4 h-4 mr-2" />
                          Manage Feedback Form
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                  
                  {/* Expandable Management Section */}
                  {selectedProgram?.id === program.id && (
                    <Card className="mt-2 border-l-4 border-blue-500">
                      <CardContent className="pt-6">
                        <Tabs defaultValue="tests" className="w-full" data-program-id={program.id}>
                          <TabsList className="grid w-full grid-cols-3 mb-4">
                            <TabsTrigger value="tests">
                              <ClipboardList className="w-4 h-4 mr-2" />
                              Tests
                            </TabsTrigger>
                            <TabsTrigger value="checklists">
                              <ClipboardCheck className="w-4 h-4 mr-2" />
                              Checklists
                            </TabsTrigger>
                            <TabsTrigger value="feedback-form">
                              <MessageSquare className="w-4 h-4 mr-2" />
                              Feedback
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
