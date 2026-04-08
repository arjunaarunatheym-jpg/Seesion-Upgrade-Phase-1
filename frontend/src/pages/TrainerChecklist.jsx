import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { toast } from "sonner";
import { CheckCircle2, ArrowLeft, Upload, Camera, ChevronLeft, ChevronRight, Users } from "lucide-react";

const TrainerChecklist = ({ user }) => {
  const { sessionId, participantId } = useParams();
  const navigate = useNavigate();
  
  const [participant, setParticipant] = useState(null);
  const [vehicle, setVehicle] = useState(null);
  const [template, setTemplate] = useState(null);
  const [checklistItems, setChecklistItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [existingChecklist, setExistingChecklist] = useState(null);
  const [isCompleted, setIsCompleted] = useState(false);
  
  // Swipe-through navigation state
  const [allParticipants, setAllParticipants] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(-1);

  useEffect(() => {
    loadData();
    loadAllParticipants();
  }, [participantId]);

  const loadAllParticipants = async () => {
    try {
      const res = await axiosInstance.get(`/trainer-checklist/${sessionId}/assigned-participants`);
      const list = res.data.participants || [];
      // Show participants claimed by me or with my completed checklists
      const myList = list.filter(p =>
        p.claimed_by_trainer_id === user?.id || p.submitted_by_trainer_id === user?.id
      );
      setAllParticipants(myList);
      const idx = myList.findIndex(p => p.id === participantId);
      setCurrentIndex(idx);
    } catch {
      setAllParticipants([]);
    }
  };

  const goToParticipant = (idx) => {
    if (idx >= 0 && idx < allParticipants.length) {
      navigate(`/trainer-checklist/${sessionId}/${allParticipants[idx].id}`, { replace: true });
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load participant details
      console.log('Loading participant:', participantId);
      const participantRes = await axiosInstance.get(`/users/${participantId}`);
      console.log('Participant loaded:', participantRes.data);
      setParticipant(participantRes.data);
      
      // Load vehicle details
      console.log('Loading vehicle details for session:', sessionId, 'participant:', participantId);
      try {
        const vehicleRes = await axiosInstance.get(`/vehicle-details/${sessionId}/${participantId}`);
        console.log('Vehicle loaded:', vehicleRes.data);
        setVehicle(vehicleRes.data);
      } catch (vehicleError) {
        console.error('Vehicle details not found:', vehicleError);
        toast.error("Participant hasn't entered vehicle details yet");
        setVehicle({ 
          registration_number: 'Not provided', 
          vehicle_model: 'Not provided', 
          roadtax_expiry: 'Not provided' 
        });
      }
      
      // Load session to get program_id
      console.log('Loading session:', sessionId);
      const sessionRes = await axiosInstance.get(`/sessions/${sessionId}`);
      const programId = sessionRes.data.program_id;
      console.log('Program ID:', programId);
      
      // Load checklist template
      console.log('Loading checklist template for program:', programId);
      const templateRes = await axiosInstance.get(`/checklists/templates/program/${programId}`);
      console.log('Template loaded:', templateRes.data);
      
      // API returns a single template object (not an array)
      const template = templateRes.data;
      if (!template || !template.program_id) {
        toast.error("No checklist template found for this program");
        setChecklistItems([]); // Ensure checklistItems is initialized
        setLoading(false);
        return;
      }
      
      setTemplate(template);
      
      // Ensure template has items
      if (!template.items || template.items.length === 0) {
        toast.error("Checklist template has no items. Please contact administrator.");
        setChecklistItems([]);
        setLoading(false);
        return;
      }
      
      // Check for existing checklist
      console.log('Checking for existing checklist...');
      try {
        const existingRes = await axiosInstance.get(`/vehicle-checklists/${sessionId}/${participantId}`);
        console.log('Existing checklist found:', existingRes.data);
        setExistingChecklist(existingRes.data);
        setIsCompleted(existingRes.data.verification_status === 'completed');
        
        // Load existing items
        if (existingRes.data.checklist_items) {
          setChecklistItems(existingRes.data.checklist_items);
        }
      } catch (existingError) {
        console.log('No existing checklist found, creating new one');
        
        // Initialize checklist items from template
        if (template && template.items && template.items.length > 0) {
          const items = template.items.map(item => ({
            item: typeof item === 'string' ? item : item.item || item.name || 'Item',
            status: "good",
            comments: "",
            photo_url: null
          }));
          console.log('Initialized checklist items:', items);
          setChecklistItems(items);
        } else {
          console.error('Template or items missing:', template);
          toast.error("No checklist items in template");
          setChecklistItems([]); // Set empty array to prevent undefined error
        }
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Load error:', error);
      console.error('Error response:', error.response?.data);
      const errorMessage = typeof error.response?.data?.detail === 'string' 
        ? error.response.data.detail 
        : error.response?.data?.message || error.message || "Failed to load checklist data";
      toast.error(errorMessage);
      setChecklistItems([]); // Ensure checklistItems is initialized even on error
      setLoading(false);
    }
  };

  const handleStatusChange = (index, status) => {
    if (isCompleted) {
      toast.error("Cannot modify a completed checklist");
      return;
    }
    const updated = [...checklistItems];
    updated[index].status = status;
    setChecklistItems(updated);
  };

  const handleCommentsChange = (index, comments) => {
    if (isCompleted) {
      toast.error("Cannot modify a completed checklist");
      return;
    }
    const updated = [...checklistItems];
    updated[index].comments = comments;
    setChecklistItems(updated);
  };

  const handlePhotoUpload = async (index, file) => {
    if (!file) return;
    
    // If already completed, don't allow photo upload
    if (isCompleted) {
      toast.error("Cannot modify a completed checklist");
      return;
    }
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axiosInstance.post('/checklist-photos/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      const updated = [...checklistItems];
      updated[index].photo_url = response.data.photo_url;
      setChecklistItems(updated);
      
      toast.success("Photo uploaded successfully");
    } catch (error) {
      console.error("Photo upload error:", error);
      const errorDetail = typeof error.response?.data?.detail === 'string' 
        ? error.response.data.detail 
        : error.message || "Unknown error";
      toast.error("Failed to upload photo: " + errorDetail);
    }
  };

  const handleSubmit = async () => {
    // Prevent resubmission if already completed
    if (isCompleted) {
      toast.error("This checklist has already been submitted and cannot be resubmitted");
      return;
    }
    
    try {
      // Validate all items are filled
      for (let i = 0; i < checklistItems.length; i++) {
        if (checklistItems[i].status === "needs_repair" && !checklistItems[i].comments.trim()) {
          toast.error(`Please add repair details for: ${checklistItems[i].item}`);
          return;
        }
      }
      
      setSubmitting(true);
      
      const response = await axiosInstance.post('/trainer-checklist/submit', {
        participant_id: participantId,
        session_id: sessionId,
        items: checklistItems.map(item => ({
          item: item.item,
          status: item.status,
          comments: item.comments || "",
          photo_url: item.photo_url
        }))
      });
      
      // Mark as completed
      setIsCompleted(true);
      // Refresh participant list to update progress
      loadAllParticipants();
      
      if (currentIndex < allParticipants.length - 1) {
        toast.success("Checklist submitted! Moving to next participant...", { duration: 2000 });
        setTimeout(() => {
          goToParticipant(currentIndex + 1);
        }, 1500);
      } else {
        toast.success("All checklists completed! Returning to dashboard...", { duration: 2000 });
        setTimeout(() => {
          navigate('/trainer-dashboard');
        }, 2000);
      }
      
      setSubmitting(false);
    } catch (error) {
      console.error("Submit error:", error);
      const errorMessage = typeof error.response?.data?.detail === 'string' 
        ? error.response.data.detail 
        : error.response?.data?.message || error.message || "Failed to submit checklist";
      toast.error(errorMessage);
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-cyan-50 p-6">
        <div className="flex items-center justify-center h-64">
          <p className="text-lg text-gray-600">Loading checklist...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-cyan-50 p-4 sm:p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header with Back + Navigation */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <Button 
              onClick={() => navigate('/trainer-dashboard')} 
              variant="outline"
              size="sm"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Back
            </Button>
            
            {/* Participant Navigation */}
            {allParticipants.length > 1 && (
              <div className="flex items-center gap-2" data-testid="participant-nav">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={currentIndex <= 0}
                  onClick={() => goToParticipant(currentIndex - 1)}
                  data-testid="prev-participant"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm font-medium text-gray-600 min-w-[80px] text-center">
                  {currentIndex + 1} / {allParticipants.length}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={currentIndex >= allParticipants.length - 1}
                  onClick={() => goToParticipant(currentIndex + 1)}
                  data-testid="next-participant"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Progress Bar (all claimed participants) */}
          {allParticipants.length > 1 && (
            <div className="mb-3">
              <div className="flex gap-1">
                {allParticipants.map((p, i) => (
                  <button
                    key={p.id}
                    onClick={() => goToParticipant(i)}
                    className={`h-2 flex-1 rounded-full transition-all ${
                      p.checklist_submitted
                        ? "bg-green-500"
                        : i === currentIndex
                        ? "bg-blue-500"
                        : "bg-gray-300"
                    }`}
                    title={p.full_name}
                  />
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1 text-center">
                {allParticipants.filter(p => p.checklist_submitted).length}/{allParticipants.length} completed
              </p>
            </div>
          )}
          
          {isCompleted && (
            <div className="mb-4 p-3 bg-green-100 border-2 border-green-500 rounded-lg">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="text-green-600 w-6 h-6 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-bold text-green-800">Checklist Submitted</p>
                  <p className="text-sm text-green-700">Proceed to the next participant.</p>
                </div>
                {currentIndex < allParticipants.length - 1 && (
                  <Button
                    size="sm"
                    className="bg-green-600 hover:bg-green-700"
                    onClick={() => goToParticipant(currentIndex + 1)}
                  >
                    Next <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                )}
              </div>
            </div>
          )}
          
          <Card>
            <CardHeader>
              <CardTitle>Vehicle Inspection Checklist</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Participant</p>
                  <p className="font-semibold">{participant?.full_name || 'Loading...'}</p>
                  <p className="text-xs text-gray-500">{participant?.email || ''}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Vehicle Registration</p>
                  <p className="font-semibold">{vehicle?.registration_number || 'Not provided'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Vehicle Model</p>
                  <p className="font-semibold">{vehicle?.vehicle_model || 'Not provided'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Roadtax Expiry</p>
                  <p className="font-semibold">{vehicle?.roadtax_expiry || 'Not provided'}</p>
                </div>
              </div>
              
              {(!vehicle?.registration_number || vehicle?.registration_number === 'Not provided') && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    ⚠️ Participant has not entered vehicle details yet. You can still complete the checklist.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Checklist Items */}
        <div className="space-y-4">
          {checklistItems && checklistItems.length > 0 ? (
            checklistItems.map((item, index) => (
              <Card key={index}>
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    <div>
                      <Label className="text-lg font-semibold">{item?.item || 'Checklist Item'}</Label>
                    </div>
                  
                  <div>
                    <Label>Status</Label>
                    <RadioGroup 
                      value={item.status} 
                      onValueChange={(value) => handleStatusChange(index, value)}
                      className="flex gap-4 mt-2"
                      disabled={isCompleted}
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="good" id={`good-${index}`} disabled={isCompleted} />
                        <Label htmlFor={`good-${index}`} className={isCompleted ? "cursor-not-allowed opacity-50" : "cursor-pointer"}>Good</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="satisfactory" id={`satisfactory-${index}`} disabled={isCompleted} />
                        <Label htmlFor={`satisfactory-${index}`} className={isCompleted ? "cursor-not-allowed opacity-50" : "cursor-pointer"}>Satisfactory</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="needs_repair" id={`repair-${index}`} disabled={isCompleted} />
                        <Label htmlFor={`repair-${index}`} className={isCompleted ? "cursor-not-allowed opacity-50" : "cursor-pointer"}>Needs Repair</Label>
                      </div>
                    </RadioGroup>
                  </div>
                  
                  {item.status === "needs_repair" && (
                    <div>
                      <Label>Repair Details (Required)</Label>
                      <Textarea
                        value={item.comments}
                        onChange={(e) => handleCommentsChange(index, e.target.value)}
                        placeholder="Describe what needs to be repaired..."
                        className="mt-2"
                        rows={3}
                        disabled={isCompleted}
                      />
                    </div>
                  )}
                  
                  {item.status === "needs_repair" && (
                    <div>
                      <Label>Attach Photo (Optional)</Label>
                      <div className="mt-2 space-y-3">
                        <div className="flex items-center gap-4">
                          <input
                            type="file"
                            accept="image/*"
                            capture="environment"
                            onChange={(e) => handlePhotoUpload(index, e.target.files[0])}
                            className="hidden"
                            id={`photo-${index}`}
                            disabled={isCompleted}
                          />
                          <label htmlFor={`photo-${index}`}>
                            <Button 
                              type="button" 
                              variant="outline" 
                              asChild
                              disabled={isCompleted}
                            >
                              <span>
                                <Camera className="w-4 h-4 mr-2" />
                                {item.photo_url ? 'Change Photo' : 'Take Photo'}
                              </span>
                            </Button>
                          </label>
                          {item.photo_url && (
                            <span className="text-sm text-green-600 font-medium">✓ Photo attached</span>
                          )}
                        </div>
                        
                        {/* Photo Preview */}
                        {item.photo_url && (
                          <div className="mt-3 border-2 border-green-200 rounded-lg p-3 bg-green-50">
                            <p className="text-sm font-medium text-gray-700 mb-2">Photo Preview:</p>
                            <img 
                              src={item.photo_url} 
                              alt={`${item.item} inspection`}
                              className="w-48 h-48 object-cover rounded-lg border-2 border-gray-300"
                              onError={(e) => {
                                console.error('Image load error:', item.photo_url);
                                e.target.style.display = 'none';
                              }}
                            />
                          </div>
                        )}
                        
                        <p className="text-xs text-gray-500">
                          Camera will open on mobile devices
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
            ))
          ) : (
            <Card>
              <CardContent className="pt-6">
                <p className="text-center text-gray-500">No checklist items available. Please contact administrator.</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Submit Button or Completed Message */}
        <div className="mt-6">
          {isCompleted ? (
            <Card className="bg-gradient-to-r from-green-100 to-emerald-100 border-2 border-green-500">
              <CardContent className="pt-6">
                <div className="flex items-center justify-center gap-3">
                  <CheckCircle2 className="w-8 h-8 text-green-600" />
                  <div>
                    <p className="font-bold text-green-800 text-lg">Checklist Successfully Submitted</p>
                    <p className="text-sm text-green-700">You may now proceed to the next participant or return to dashboard.</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-gradient-to-r from-green-50 to-teal-50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">Ready to submit?</p>
                    <p className="text-sm text-gray-600">Your name will be automatically signed upon submission</p>
                  </div>
                  <Button 
                    onClick={handleSubmit}
                    disabled={submitting || checklistItems.length === 0}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {submitting ? "Submitting..." : "Submit Checklist"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
        
        {isCompleted && (
          <div className="mt-6">
            <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-300">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-blue-900">This checklist has been completed</p>
                    <p className="text-sm text-blue-700">Verified by: {existingChecklist?.verified_by || 'System'}</p>
                  </div>
                  <Button 
                    onClick={() => navigate('/trainer-dashboard')}
                    variant="outline"
                    className="border-blue-500 text-blue-700 hover:bg-blue-50"
                  >
                    Back to Dashboard
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrainerChecklist;
