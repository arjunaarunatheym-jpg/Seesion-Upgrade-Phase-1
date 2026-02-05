import { useState, useEffect } from "react";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Upload, Save, Image as ImageIcon, Palette, FileText, FileSignature, Plus, Trash2, GripVertical, ChevronUp, ChevronDown, MessageSquare } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const Settings = () => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [logoFile, setLogoFile] = useState(null);
  const [templateFile, setTemplateFile] = useState(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingTemplate, setUploadingTemplate] = useState(false);
  
  // Indemnity form sections state
  const [indemnitySections, setIndemnitySections] = useState([]);
  const [savingIndemnity, setSavingIndemnity] = useState(false);
  
  // Feedback questions state
  const [feedbackQuestions, setFeedbackQuestions] = useState([]);
  const [savingFeedback, setSavingFeedback] = useState(false);

  const [formData, setFormData] = useState({
    company_name: "",
    primary_color: "#3b82f6",
    secondary_color: "#6366f1",
    footer_text: "",
    max_certificate_file_size_mb: 5
  });

  useEffect(() => {
    loadSettings();
    loadIndemnitySections();
    loadFeedbackQuestions();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await axiosInstance.get("/settings");
      setSettings(response.data);
      setFormData({
        company_name: response.data.company_name || "",
        primary_color: response.data.primary_color || "#3b82f6",
        secondary_color: response.data.secondary_color || "#6366f1",
        footer_text: response.data.footer_text || "",
        max_certificate_file_size_mb: response.data.max_certificate_file_size_mb || 5
      });
      setLoading(false);
    } catch (error) {
      toast.error("Failed to load settings");
      setLoading(false);
    }
  };

  const loadIndemnitySections = async () => {
    try {
      const response = await axiosInstance.get("/settings/indemnity-sections");
      setIndemnitySections(response.data || []);
    } catch (error) {
      console.error("Failed to load indemnity sections:", error);
    }
  };

  const handleAddSection = () => {
    const newOrder = indemnitySections.length + 1;
    setIndemnitySections([...indemnitySections, {
      id: `temp_${Date.now()}`,
      order: newOrder,
      title: "",
      content: ""
    }]);
  };

  const handleRemoveSection = (index) => {
    const updated = indemnitySections.filter((_, i) => i !== index);
    // Reorder remaining sections
    updated.forEach((section, i) => { section.order = i + 1; });
    setIndemnitySections(updated);
  };

  const handleMoveSection = (index, direction) => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= indemnitySections.length) return;
    
    const updated = [...indemnitySections];
    [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
    // Update order values
    updated.forEach((section, i) => { section.order = i + 1; });
    setIndemnitySections(updated);
  };

  const handleSectionChange = (index, field, value) => {
    const updated = [...indemnitySections];
    updated[index] = { ...updated[index], [field]: value };
    setIndemnitySections(updated);
  };

  const handleSaveIndemnitySections = async () => {
    // Validate
    if (indemnitySections.some(s => !s.title.trim())) {
      toast.error("All sections must have a title");
      return;
    }
    
    setSavingIndemnity(true);
    try {
      await axiosInstance.post("/settings/indemnity-sections", indemnitySections);
      toast.success("Indemnity form sections saved successfully!");
      loadIndemnitySections();
    } catch (error) {
      toast.error("Failed to save indemnity sections");
    } finally {
      setSavingIndemnity(false);
    }
  };

  // Feedback Questions Functions
  const loadFeedbackQuestions = async () => {
    try {
      const response = await axiosInstance.get("/settings/feedback-questions");
      setFeedbackQuestions(response.data || []);
    } catch (error) {
      console.error("Failed to load feedback questions:", error);
    }
  };

  const handleAddFeedbackQuestion = () => {
    const newOrder = feedbackQuestions.length + 1;
    setFeedbackQuestions([...feedbackQuestions, {
      id: `Q${newOrder}`,
      order: newOrder,
      category: "UMUM",
      question: "",
      type: "rating",
      required: true
    }]);
  };

  const handleRemoveFeedbackQuestion = (index) => {
    const updated = feedbackQuestions.filter((_, i) => i !== index);
    updated.forEach((q, i) => { q.order = i + 1; });
    setFeedbackQuestions(updated);
  };

  const handleMoveFeedbackQuestion = (index, direction) => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= feedbackQuestions.length) return;
    
    const updated = [...feedbackQuestions];
    [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
    updated.forEach((q, i) => { q.order = i + 1; });
    setFeedbackQuestions(updated);
  };

  const handleFeedbackQuestionChange = (index, field, value) => {
    const updated = [...feedbackQuestions];
    updated[index] = { ...updated[index], [field]: value };
    setFeedbackQuestions(updated);
  };

  const handleSaveFeedbackQuestions = async () => {
    if (feedbackQuestions.some(q => !q.question.trim())) {
      toast.error("All questions must have text");
      return;
    }
    
    setSavingFeedback(true);
    try {
      await axiosInstance.post("/settings/feedback-questions", feedbackQuestions);
      toast.success("Feedback questions saved successfully!");
      loadFeedbackQuestions();
    } catch (error) {
      toast.error("Failed to save feedback questions");
    } finally {
      setSavingFeedback(false);
    }
  };

  const handleLogoUpload = async () => {
    if (!logoFile) {
      toast.error("Please select a logo file");
      return;
    }

    // Check file size (max 5MB)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (logoFile.size > maxSize) {
      toast.error("Logo file size must be less than 5MB");
      return;
    }

    // Check file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(logoFile.type)) {
      toast.error("Please upload a valid image file (JPEG, PNG, GIF, or WebP)");
      return;
    }

    setUploadingLogo(true);
    try {
      const formData = new FormData();
      formData.append("file", logoFile);

      const response = await axiosInstance.post("/settings/upload-logo", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 30000 // 30 second timeout for upload
      });

      toast.success("Logo uploaded successfully!");
      setLogoFile(null);
      loadSettings();
    } catch (error) {
      console.error("Logo upload error:", error);
      toast.error(error.response?.data?.detail || "Failed to upload logo. Please try a smaller file.");
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleTemplateUpload = async () => {
    if (!templateFile) {
      toast.error("Please select a certificate template file");
      return;
    }

    if (!templateFile.name.endsWith('.docx')) {
      toast.error("Only .docx files are supported");
      return;
    }

    // Check file size (max 10MB for Word documents)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (templateFile.size > maxSize) {
      toast.error("Template file size must be less than 10MB");
      return;
    }

    setUploadingTemplate(true);
    try {
      const formData = new FormData();
      formData.append("file", templateFile);

      const response = await axiosInstance.post("/settings/upload-certificate-template", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 30000 // 30 second timeout for upload
      });

      toast.success("Certificate template uploaded successfully!");
      setTemplateFile(null);
      loadSettings();
    } catch (error) {
      console.error("Template upload error:", error);
      toast.error(error.response?.data?.detail || "Failed to upload template. Please try again.");
    } finally {
      setUploadingTemplate(false);
    }
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await axiosInstance.put("/settings", formData);
      toast.success("Settings saved successfully!");
      loadSettings();
    } catch (error) {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Logo Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImageIcon className="w-5 h-5" />
            Company Logo
          </CardTitle>
          <CardDescription>Upload your company logo (appears on login page before sign in)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {settings?.logo_url && (
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">Current Logo:</p>
              <img
                src={`${process.env.REACT_APP_BACKEND_URL}${settings.logo_url}`}
                alt="Company Logo"
                className="h-20 object-contain border rounded p-2"
              />
            </div>
          )}
          <div className="space-y-2">
            <div className="flex gap-3">
              <Input
                type="file"
                accept="image/*"
                onChange={(e) => setLogoFile(e.target.files[0])}
                data-testid="logo-upload-input"
              />
              <Button
                onClick={handleLogoUpload}
                disabled={!logoFile || uploadingLogo}
                data-testid="upload-logo-button"
              >
                <Upload className="w-4 h-4 mr-2" />
                {uploadingLogo ? "Uploading..." : "Upload Logo"}
              </Button>
            </div>
            <p className="text-xs text-gray-500">
              Supported formats: JPEG, PNG, GIF, WebP | Max size: 5MB
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Certificate Template Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Certificate Template
          </CardTitle>
          <CardDescription>
            Upload your certificate template (.docx file). Use placeholders: «PARTICIPANT_NAME», «IC_NUMBER», «COMPANY_NAME», «PROGRAMME NAME», «VENUE», «DATE»
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {settings?.certificate_template_url && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded">
              <p className="text-sm text-green-800">✓ Certificate template uploaded</p>
            </div>
          )}
          <div className="space-y-2">
            <div className="flex gap-3">
              <Input
                type="file"
                accept=".docx"
                onChange={(e) => setTemplateFile(e.target.files[0])}
                data-testid="template-upload-input"
              />
              <Button
                onClick={handleTemplateUpload}
                disabled={!templateFile || uploadingTemplate}
                data-testid="upload-template-button"
              >
                <Upload className="w-4 h-4 mr-2" />
                {uploadingTemplate ? "Uploading..." : "Upload Template"}
              </Button>
            </div>
            <p className="text-xs text-gray-500">
              Only .docx files | Max size: 10MB
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Theme Colors */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="w-5 h-5" />
            Dashboard Theme Colors
          </CardTitle>
          <CardDescription>Set your corporate colors for the dashboard and login page</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="primary-color">Primary Color</Label>
              <div className="flex gap-2 items-center">
                <Input
                  id="primary-color"
                  type="color"
                  value={formData.primary_color}
                  onChange={(e) => setFormData({ ...formData, primary_color: e.target.value })}
                  className="h-10 w-20"
                  data-testid="primary-color-input"
                />
                <Input
                  type="text"
                  value={formData.primary_color}
                  onChange={(e) => setFormData({ ...formData, primary_color: e.target.value })}
                  placeholder="#3b82f6"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="secondary-color">Secondary Color</Label>
              <div className="flex gap-2 items-center">
                <Input
                  id="secondary-color"
                  type="color"
                  value={formData.secondary_color}
                  onChange={(e) => setFormData({ ...formData, secondary_color: e.target.value })}
                  className="h-10 w-20"
                  data-testid="secondary-color-input"
                />
                <Input
                  type="text"
                  value={formData.secondary_color}
                  onChange={(e) => setFormData({ ...formData, secondary_color: e.target.value })}
                  placeholder="#6366f1"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Company Details */}
      <Card>
        <CardHeader>
          <CardTitle>Company Details</CardTitle>
          <CardDescription>Company name appears on login page and in certificates</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="company-name">Company Name</Label>
            <Input
              id="company-name"
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              placeholder="Your Company Name"
              data-testid="company-name-input"
            />
            <p className="text-xs text-gray-500 mt-1">Appears on login page and in certificate placeholders</p>
          </div>
          <div>
            <Label htmlFor="footer-text">Footer Text (Optional)</Label>
            <Textarea
              id="footer-text"
              value={formData.footer_text}
              onChange={(e) => setFormData({ ...formData, footer_text: e.target.value })}
              placeholder="Footer text for emails and documents"
              rows={3}
              data-testid="footer-text-input"
            />
          </div>
          <div>
            <Label htmlFor="max-cert-size">Max Certificate File Size (MB)</Label>
            <Input
              id="max-cert-size"
              type="number"
              min="1"
              max="50"
              value={formData.max_certificate_file_size_mb}
              onChange={(e) => setFormData({ ...formData, max_certificate_file_size_mb: parseInt(e.target.value) || 5 })}
              data-testid="max-cert-size-input"
            />
            <p className="text-xs text-gray-500 mt-1">Maximum file size for coordinator certificate uploads (1-50 MB)</p>
          </div>
        </CardContent>
      </Card>

      {/* Indemnity Form Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileSignature className="w-5 h-5" />
            Indemnity Form Sections
          </CardTitle>
          <CardDescription>
            Manage the text sections shown in the participant indemnity form wizard. 
            Participants must accept each section before signing.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {indemnitySections.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileSignature className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No sections defined yet.</p>
              <p className="text-sm">Add sections to customize the indemnity form.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {indemnitySections.map((section, index) => (
                <div 
                  key={section.id || index} 
                  className="border rounded-lg p-4 bg-gray-50"
                  data-testid={`indemnity-section-${index}`}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className="flex flex-col gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMoveSection(index, 'up')}
                        disabled={index === 0}
                        className="h-6 w-6 p-0"
                        title="Move up"
                      >
                        <ChevronUp className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMoveSection(index, 'down')}
                        disabled={index === indemnitySections.length - 1}
                        className="h-6 w-6 p-0"
                        title="Move down"
                      >
                        <ChevronDown className="w-4 h-4" />
                      </Button>
                    </div>
                    <span className="text-sm font-medium text-gray-500 w-8">#{section.order}</span>
                    <Input
                      value={section.title}
                      onChange={(e) => handleSectionChange(index, 'title', e.target.value)}
                      placeholder="Section Title (e.g., Terms & Conditions)"
                      className="flex-1"
                      data-testid={`indemnity-title-${index}`}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveSection(index)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      title="Remove section"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                  <Textarea
                    value={section.content}
                    onChange={(e) => handleSectionChange(index, 'content', e.target.value)}
                    placeholder="Section content... (This text will be shown to participants)"
                    rows={4}
                    className="w-full"
                    data-testid={`indemnity-content-${index}`}
                  />
                </div>
              ))}
            </div>
          )}
          
          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              onClick={handleAddSection}
              data-testid="add-indemnity-section-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Section
            </Button>
            {indemnitySections.length > 0 && (
              <Button
                onClick={handleSaveIndemnitySections}
                disabled={savingIndemnity}
                data-testid="save-indemnity-sections-btn"
              >
                <Save className="w-4 h-4 mr-2" />
                {savingIndemnity ? "Saving..." : "Save Indemnity Sections"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Feedback Questions Management */}
      <Card data-testid="feedback-questions-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Soalan Maklum Balas Peserta
          </CardTitle>
          <CardDescription>
            Urus soalan maklum balas untuk peserta. Skala 1-5 untuk penilaian.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {feedbackQuestions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No questions defined yet.</p>
              <p className="text-sm">Add questions to customize the feedback form.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {feedbackQuestions.map((question, index) => (
                <div 
                  key={question.id || index} 
                  className="border rounded-lg p-3 bg-gray-50"
                  data-testid={`feedback-question-${index}`}
                >
                  <div className="flex items-start gap-2">
                    <div className="flex flex-col gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMoveFeedbackQuestion(index, 'up')}
                        disabled={index === 0}
                        className="h-6 w-6 p-0"
                        title="Move up"
                      >
                        <ChevronUp className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMoveFeedbackQuestion(index, 'down')}
                        disabled={index === feedbackQuestions.length - 1}
                        className="h-6 w-6 p-0"
                        title="Move down"
                      >
                        <ChevronDown className="w-4 h-4" />
                      </Button>
                    </div>
                    
                    <div className="flex-1 space-y-2">
                      <div className="flex gap-2">
                        <Input
                          value={question.id}
                          onChange={(e) => handleFeedbackQuestionChange(index, 'id', e.target.value)}
                          placeholder="ID (e.g., A1)"
                          className="w-20"
                          data-testid={`feedback-id-${index}`}
                        />
                        <Select
                          value={question.category}
                          onValueChange={(value) => handleFeedbackQuestionChange(index, 'category', value)}
                        >
                          <SelectTrigger className="w-48" data-testid={`feedback-category-${index}`}>
                            <SelectValue placeholder="Category" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="KUALITI KURSUS">A. KUALITI KURSUS</SelectItem>
                            <SelectItem value="PENYEDIA LATIHAN">B. PENYEDIA LATIHAN</SelectItem>
                            <SelectItem value="TRAINER">C. TRAINER</SelectItem>
                            <SelectItem value="UMUM">D. UMUM</SelectItem>
                          </SelectContent>
                        </Select>
                        <Select
                          value={question.type}
                          onValueChange={(value) => handleFeedbackQuestionChange(index, 'type', value)}
                        >
                          <SelectTrigger className="w-32" data-testid={`feedback-type-${index}`}>
                            <SelectValue placeholder="Type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="rating">Rating (1-5)</SelectItem>
                            <SelectItem value="text">Text</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <Input
                        value={question.question}
                        onChange={(e) => handleFeedbackQuestionChange(index, 'question', e.target.value)}
                        placeholder="Soalan (e.g., Penganjur menepati jangkaan saya)"
                        className="w-full"
                        data-testid={`feedback-question-text-${index}`}
                      />
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveFeedbackQuestion(index)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      title="Remove question"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              onClick={handleAddFeedbackQuestion}
              data-testid="add-feedback-question-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Question
            </Button>
            {feedbackQuestions.length > 0 && (
              <Button
                onClick={handleSaveFeedbackQuestions}
                disabled={savingFeedback}
                data-testid="save-feedback-questions-btn"
              >
                <Save className="w-4 h-4 mr-2" />
                {savingFeedback ? "Saving..." : "Save Questions"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleSaveSettings}
          disabled={saving}
          size="lg"
          data-testid="save-settings-button"
        >
          <Save className="w-4 h-4 mr-2" />
          {saving ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </div>
  );
};

export default Settings;
