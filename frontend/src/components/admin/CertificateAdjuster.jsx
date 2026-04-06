/**
 * CertificateAdjuster - Live preview tool for certificate font/layout adjustments
 * Used by Admin & Coordinator to fine-tune certificate appearance before generation
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Eye, Save, FileDown, Loader2, RotateCcw, Settings2 } from "lucide-react";

const FIELD_LABELS = {
  participant_name: "Participant Name",
  ic_number: "IC Number",
  company_name: "Company Name",
  certificate_title: "Programme Title",
  certificate_subtitle: "Programme Subtitle",
  dates: "Training Dates",
  venue: "Venue",
  certificate_number: "Certificate Number",
};

const DEFAULTS = {
  participant_name: { font_size: 16, max_lines: 1, auto_fit: true, bold: true },
  ic_number: { font_size: 16, max_lines: 1, auto_fit: false, bold: false },
  company_name: { font_size: 12, max_lines: 1, auto_fit: true, bold: false },
  certificate_title: { font_size: 16, max_lines: 2, auto_fit: true, bold: true },
  certificate_subtitle: { font_size: 12, max_lines: 1, auto_fit: true, bold: false },
  dates: { font_size: 10, max_lines: 1, auto_fit: true, bold: false },
  venue: { font_size: 8, max_lines: 2, auto_fit: true, bold: false },
  certificate_number: { font_size: 10, max_lines: 1, auto_fit: false, bold: false },
  top_margin: 80,
  paragraph_spacing: 65,
};

export const CertificateAdjuster = ({ sessions = [], onClose }) => {
  const [settings, setSettings] = useState(DEFAULTS);
  const [selectedSession, setSelectedSession] = useState("");
  const [selectedParticipant, setSelectedParticipant] = useState("");
  const [participants, setParticipants] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const previewRef = useRef(null);
  const debounceRef = useRef(null);

  // Load saved settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  // Load participants when session changes
  useEffect(() => {
    if (selectedSession) {
      loadParticipants();
    } else {
      setParticipants([]);
      setSelectedParticipant("");
    }
  }, [selectedSession]);

  const loadSettings = async () => {
    try {
      const res = await axiosInstance.get("/certificates/font-settings");
      if (res.data) {
        setSettings(prev => ({ ...prev, ...res.data }));
      }
    } catch {
      // Use defaults
    }
  };

  const loadParticipants = async () => {
    try {
      const sessionRes = await axiosInstance.get(`/sessions/${selectedSession}`);
      const pids = sessionRes.data?.participant_ids || [];
      if (!pids.length) {
        setParticipants([]);
        setSelectedParticipant("");
        return;
      }
      const userRes = await axiosInstance.get("/users");
      const users = userRes.data.filter(u => pids.includes(u.id));
      setParticipants(users);
      if (users.length > 0) {
        setSelectedParticipant(users[0].id);
      }
    } catch {
      toast.error("Failed to load participants");
    }
  };

  const generatePreview = useCallback(async (currentSettings) => {
    if (!selectedSession || !selectedParticipant) return;
    setLoading(true);
    try {
      const res = await axiosInstance.post(
        `/certificates/preview-pdf/${selectedSession}/${selectedParticipant}`,
        currentSettings || settings,
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(res.data);
      setPreviewUrl(prev => {
        if (prev) URL.revokeObjectURL(prev);
        return url;
      });
    } catch (err) {
      toast.error("Preview failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [selectedSession, selectedParticipant, settings]);

  // Debounced preview on settings change
  const debouncedPreview = useCallback((newSettings) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      generatePreview(newSettings);
    }, 800);
  }, [generatePreview]);

  const updateFieldSetting = (field, key, value) => {
    setSettings(prev => {
      const updated = {
        ...prev,
        [field]: { ...prev[field], [key]: value }
      };
      debouncedPreview(updated);
      return updated;
    });
  };

  const updateGlobalSetting = (key, value) => {
    setSettings(prev => {
      const updated = { ...prev, [key]: value };
      debouncedPreview(updated);
      return updated;
    });
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      await axiosInstance.put("/certificates/font-settings", settings);
      toast.success("Settings saved as defaults");
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const resetDefaults = () => {
    setSettings(DEFAULTS);
    if (selectedSession && selectedParticipant) {
      debouncedPreview(DEFAULTS);
    }
    toast.info("Reset to defaults");
  };

  const handleGenerate = async (force = false) => {
    if (!selectedSession || !selectedParticipant) return;
    setGenerating(true);
    try {
      await axiosInstance.put("/certificates/font-settings", settings);
      const res = await axiosInstance.post(
        `/certificates/generate-pdf/${selectedSession}/${selectedParticipant}?force=${force}`
      );
      toast.success(res.data.message);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      if (detail.includes("not eligible")) {
        toast.error(detail, {
          action: { label: "Force Generate", onClick: () => handleGenerate(true) },
        });
      } else {
        toast.error(detail);
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleBulkGenerate = async (force = false) => {
    if (!selectedSession) return;
    setGenerating(true);
    try {
      await axiosInstance.put("/certificates/font-settings", settings);
      const res = await axiosInstance.post(
        `/certificates/generate-bulk-pdf/${selectedSession}?force=${force}`
      );
      toast.success(res.data.message);
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message);
    } finally {
      setGenerating(false);
    }
  };

  const FieldControl = ({ field }) => {
    const fs = settings[field] || {};
    const label = FIELD_LABELS[field] || field;

    return (
      <div data-testid={`field-control-${field}`} className="border border-zinc-700 rounded-lg p-3 space-y-2 bg-zinc-800/50">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-zinc-200">{label}</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-400">Auto-fit</span>
            <Switch
              data-testid={`auto-fit-${field}`}
              checked={fs.auto_fit || false}
              onCheckedChange={(v) => updateFieldSetting(field, "auto_fit", v)}
              className="scale-75"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-xs text-zinc-400">Font Size: {fs.font_size || 12}pt</Label>
            <Slider
              data-testid={`font-size-${field}`}
              value={[fs.font_size || 12]}
              onValueChange={([v]) => updateFieldSetting(field, "font_size", v)}
              min={6}
              max={24}
              step={0.5}
              className="mt-1"
            />
          </div>
          <div>
            <Label className="text-xs text-zinc-400">Max Lines: {fs.max_lines || 1}</Label>
            <Slider
              data-testid={`max-lines-${field}`}
              value={[fs.max_lines || 1]}
              onValueChange={([v]) => updateFieldSetting(field, "max_lines", v)}
              min={1}
              max={4}
              step={1}
              className="mt-1"
            />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div data-testid="certificate-adjuster" className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-4 h-full">
      {/* Controls Panel */}
      <div className="space-y-3 overflow-y-auto max-h-[85vh] pr-1">
        <Card className="bg-zinc-900 border-zinc-700">
          <CardHeader className="pb-2 pt-3 px-4">
            <CardTitle className="text-base flex items-center gap-2 text-zinc-100">
              <Settings2 className="h-4 w-4" /> Certificate Layout Settings
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 space-y-3">
            {/* Session & Participant Selection */}
            <div className="space-y-2">
              <Label className="text-xs text-zinc-400">Session</Label>
              <Select value={selectedSession} onValueChange={setSelectedSession}>
                <SelectTrigger data-testid="session-select" className="bg-zinc-800 border-zinc-600 text-zinc-200">
                  <SelectValue placeholder="Select session" />
                </SelectTrigger>
                <SelectContent>
                  {sessions.map(s => (
                    <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {participants.length > 0 && (
              <div className="space-y-2">
                <Label className="text-xs text-zinc-400">Preview Participant ({participants.length} total)</Label>
                <Select value={selectedParticipant} onValueChange={(v) => {
                  setSelectedParticipant(v);
                  setPreviewUrl(null);
                }}>
                  <SelectTrigger data-testid="participant-select" className="bg-zinc-800 border-zinc-600 text-zinc-200">
                    <SelectValue placeholder="Select participant" />
                  </SelectTrigger>
                  <SelectContent>
                    {participants.map(p => (
                      <SelectItem key={p.id} value={p.id}>{p.full_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            {selectedSession && participants.length === 0 && (
              <p className="text-xs text-amber-400">No participants in this session</p>
            )}

            {/* Global Controls */}
            <div className="border border-zinc-700 rounded-lg p-3 space-y-2 bg-zinc-800/50">
              <span className="text-sm font-medium text-zinc-200">Layout</span>
              <div>
                <Label className="text-xs text-zinc-400">Top Margin: {settings.top_margin}%</Label>
                <Slider
                  data-testid="top-margin-slider"
                  value={[settings.top_margin]}
                  onValueChange={([v]) => updateGlobalSetting("top_margin", v)}
                  min={40}
                  max={100}
                  step={5}
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs text-zinc-400">Paragraph Spacing: {settings.paragraph_spacing}%</Label>
                <Slider
                  data-testid="spacing-slider"
                  value={[settings.paragraph_spacing]}
                  onValueChange={([v]) => updateGlobalSetting("paragraph_spacing", v)}
                  min={30}
                  max={100}
                  step={5}
                  className="mt-1"
                />
              </div>
            </div>

            {/* Field Controls */}
            {Object.keys(FIELD_LABELS).map(field => (
              <FieldControl key={field} field={field} />
            ))}
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2 sticky bottom-0 bg-zinc-950 py-2">
          <Button
            data-testid="preview-btn"
            onClick={() => generatePreview()}
            disabled={!selectedSession || !selectedParticipant || loading}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Eye className="h-4 w-4 mr-1" />}
            Preview
          </Button>
          <Button
            data-testid="save-settings-btn"
            onClick={saveSettings}
            disabled={saving}
            variant="outline"
            className="border-zinc-600 text-zinc-200"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Save className="h-4 w-4 mr-1" />}
            Save Defaults
          </Button>
          <Button
            data-testid="reset-btn"
            onClick={resetDefaults}
            variant="ghost"
            className="text-zinc-400"
          >
            <RotateCcw className="h-4 w-4 mr-1" /> Reset
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            data-testid="generate-single-btn"
            onClick={() => handleGenerate(false)}
            disabled={!selectedSession || !selectedParticipant || generating}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            {generating ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FileDown className="h-4 w-4 mr-1" />}
            Generate This Cert
          </Button>
          <Button
            data-testid="generate-bulk-btn"
            onClick={() => handleBulkGenerate(false)}
            disabled={!selectedSession || generating}
            className="bg-amber-600 hover:bg-amber-700"
          >
            {generating ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <FileDown className="h-4 w-4 mr-1" />}
            Generate All (Eligible)
          </Button>
          <Button
            data-testid="generate-bulk-force-btn"
            onClick={() => handleBulkGenerate(true)}
            disabled={!selectedSession || generating}
            variant="outline"
            className="border-amber-600 text-amber-400 hover:bg-amber-900/30"
          >
            Force Generate All
          </Button>
        </div>
      </div>

      {/* Preview Panel */}
      <div className="flex flex-col items-center" ref={previewRef}>
        <div className="w-full bg-zinc-800 rounded-lg border border-zinc-700 overflow-hidden flex items-center justify-center min-h-[500px]">
          {loading && (
            <div className="flex flex-col items-center gap-2 text-zinc-400">
              <Loader2 className="h-8 w-8 animate-spin" />
              <span className="text-sm">Generating preview...</span>
            </div>
          )}
          {!loading && previewUrl && (
            <img
              data-testid="certificate-preview-image"
              src={previewUrl}
              alt="Certificate Preview"
              className="w-full h-auto object-contain"
            />
          )}
          {!loading && !previewUrl && (
            <div className="text-zinc-500 text-center p-8">
              <Eye className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Select a session and participant, then click Preview</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CertificateAdjuster;
