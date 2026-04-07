/**
 * CertificateDesigner - Visual drag-and-drop certificate layout editor
 * Background image is static. Placeholders are draggable with font controls.
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Save, Eye, FileDown, Loader2, RotateCcw, GripVertical, Move } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

// Default placeholder layout (% positions relative to certificate dimensions)
const DEFAULT_LAYOUT = {
  participant_name: { x: 38, y: 27.5, fontSize: 18, fontWeight: "bold", textAlign: "center", width: 55, color: "#000000", label: "Participant Name" },
  ic_number: { x: 38, y: 31.5, fontSize: 14, fontWeight: "normal", textAlign: "center", width: 55, color: "#000000", label: "IC Number" },
  company_name: { x: 38, y: 36, fontSize: 13, fontWeight: "bold", textAlign: "center", width: 55, color: "#000000", label: "Company Name" },
  certificate_title: { x: 33, y: 42, fontSize: 16, fontWeight: "bold", textAlign: "center", width: 60, color: "#000000", label: "Programme Title" },
  certificate_subtitle: { x: 33, y: 47, fontSize: 11, fontWeight: "normal", textAlign: "center", width: 60, color: "#000000", label: "Programme Subtitle" },
  training_dates: { x: 38, y: 55, fontSize: 10, fontWeight: "normal", textAlign: "center", width: 55, color: "#000000", label: "Training Dates" },
  venue: { x: 38, y: 59.5, fontSize: 10, fontWeight: "normal", textAlign: "center", width: 55, color: "#000000", label: "Venue" },
  validity: { x: 38, y: 64, fontSize: 10, fontWeight: "normal", textAlign: "center", width: 55, color: "#000000", label: "Validity Period" },
  certificate_number: { x: 25, y: 93, fontSize: 9, fontWeight: "normal", textAlign: "left", width: 60, color: "#000000", label: "Certificate Number" },
};

const SAMPLE_DATA = {
  participant_name: "MOHD KHAIRUL BIN MAHAMOOD",
  ic_number: "I.C. No: 840421115693",
  company_name: "ACE GREENCEMT VENTURE (M) SDN. BHD.",
  certificate_title: "DEFENSIVE DRIVING FOR HEAVY COMMERCIAL VEHICLES",
  certificate_subtitle: "1 DAY PROGRAMME",
  training_dates: "17 December 2025",
  venue: "Asas Asia (M) Sdn Bhd, PT 10694, Kampung Chuah, 71960, Port Dickson",
  validity: "Valid: 17 December 2025 - 17 December 2027",
  certificate_number: "Certificate Serial No: MDDRC/COA/2026/04/00001",
};

export const CertificateDesigner = ({ sessions = [] }) => {
  const [layout, setLayout] = useState(DEFAULT_LAYOUT);
  const [selectedField, setSelectedField] = useState(null);
  const [selectedSession, setSelectedSession] = useState("");
  const [selectedParticipant, setSelectedParticipant] = useState("");
  const [participants, setParticipants] = useState([]);
  const [previewData, setPreviewData] = useState(SAMPLE_DATA);
  const [useLiveData, setUseLiveData] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [bgLoaded, setBgLoaded] = useState(false);
  const canvasRef = useRef(null);
  const dragRef = useRef({ active: false, field: null, startX: 0, startY: 0, origX: 0, origY: 0 });

  useEffect(() => { loadLayout(); }, []);

  useEffect(() => {
    if (selectedSession) loadParticipants();
    else { setParticipants([]); setSelectedParticipant(""); }
  }, [selectedSession]);

  useEffect(() => {
    if (useLiveData && selectedSession && selectedParticipant) loadLiveData();
    else if (!useLiveData) setPreviewData(SAMPLE_DATA);
  }, [useLiveData, selectedSession, selectedParticipant]);

  const loadLayout = async () => {
    try {
      const res = await axiosInstance.get("/certificates/designer-layout");
      if (res.data && Object.keys(res.data).length > 2) {
        setLayout(prev => {
          const merged = { ...prev };
          for (const [k, v] of Object.entries(res.data)) {
            if (k !== "id" && typeof v === "object") merged[k] = { ...prev[k], ...v };
          }
          return merged;
        });
      }
    } catch { /* use defaults */ }
  };

  const loadParticipants = async () => {
    try {
      const sRes = await axiosInstance.get(`/sessions/${selectedSession}`);
      const pids = sRes.data?.participant_ids || [];
      if (!pids.length) { setParticipants([]); return; }
      const uRes = await axiosInstance.get("/users");
      setParticipants(uRes.data.filter(u => pids.includes(u.id)));
    } catch { toast.error("Failed to load participants"); }
  };

  const loadLiveData = async () => {
    try {
      const res = await axiosInstance.post("/certificates/preview-data", {
        session_id: selectedSession, participant_id: selectedParticipant
      });
      if (res.data) setPreviewData(res.data);
    } catch { toast.error("Failed to load preview data"); }
  };

  const saveLayout = async () => {
    setSaving(true);
    try {
      await axiosInstance.put("/certificates/designer-layout", layout);
      toast.success("Layout saved");
    } catch { toast.error("Failed to save"); }
    finally { setSaving(false); }
  };

  const updateField = (field, key, value) => {
    setLayout(prev => ({ ...prev, [field]: { ...prev[field], [key]: value } }));
  };

  // Drag handlers
  const handleMouseDown = (e, field) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = canvasRef.current.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    dragRef.current = {
      active: true, field,
      startX: clientX, startY: clientY,
      origX: layout[field].x, origY: layout[field].y,
      canvasW: rect.width, canvasH: rect.height,
    };
    setSelectedField(field);
  };

  const handleMouseMove = useCallback((e) => {
    const d = dragRef.current;
    if (!d.active) return;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    const dx = ((clientX - d.startX) / d.canvasW) * 100;
    const dy = ((clientY - d.startY) / d.canvasH) * 100;
    const newX = Math.max(0, Math.min(95, d.origX + dx));
    const newY = Math.max(0, Math.min(98, d.origY + dy));
    setLayout(prev => ({ ...prev, [d.field]: { ...prev[d.field], x: Math.round(newX * 10) / 10, y: Math.round(newY * 10) / 10 } }));
  }, []);

  const handleMouseUp = useCallback(() => {
    dragRef.current.active = false;
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    window.addEventListener("touchmove", handleMouseMove, { passive: false });
    window.addEventListener("touchend", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("touchmove", handleMouseMove);
      window.removeEventListener("touchend", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const handleGenerate = async (bulk = false, force = false) => {
    if (!selectedSession) return toast.error("Select a session first");
    if (!bulk && !selectedParticipant) return toast.error("Select a participant");
    setGenerating(true);
    try {
      await axiosInstance.put("/certificates/designer-layout", layout);
      const url = bulk
        ? `/certificates/generate-designed/${selectedSession}?force=${force}`
        : `/certificates/generate-designed/${selectedSession}/${selectedParticipant}?force=${force}`;
      const res = await axiosInstance.post(url);
      toast.success(res.data.message);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      if (detail.includes("not eligible")) {
        toast.error(detail, { action: { label: "Force", onClick: () => handleGenerate(bulk, true) } });
      } else toast.error(detail);
    } finally { setGenerating(false); }
  };

  const sf = selectedField ? layout[selectedField] : null;

  return (
    <div data-testid="certificate-designer" className="flex flex-col xl:flex-row gap-3">
      {/* Left: Controls */}
      <div className="xl:w-[340px] space-y-3 shrink-0 order-2 xl:order-1">
        {/* Session/Participant Selection */}
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 space-y-2">
          <div className="space-y-1">
            <Label className="text-xs text-zinc-400">Session</Label>
            <Select value={selectedSession} onValueChange={setSelectedSession}>
              <SelectTrigger data-testid="designer-session-select" className="bg-zinc-800 border-zinc-600 text-zinc-200 h-8 text-xs">
                <SelectValue placeholder="Select session" />
              </SelectTrigger>
              <SelectContent>{sessions.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          {participants.length > 0 && (
            <div className="space-y-1">
              <Label className="text-xs text-zinc-400">Participant ({participants.length})</Label>
              <Select value={selectedParticipant} onValueChange={setSelectedParticipant}>
                <SelectTrigger data-testid="designer-participant-select" className="bg-zinc-800 border-zinc-600 text-zinc-200 h-8 text-xs">
                  <SelectValue placeholder="Select participant" />
                </SelectTrigger>
                <SelectContent>{participants.map(p => <SelectItem key={p.id} value={p.id}>{p.full_name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Switch checked={useLiveData} onCheckedChange={setUseLiveData} className="scale-75" />
            <span className="text-xs text-zinc-400">Use live participant data</span>
          </div>
        </div>

        {/* Field List - click to select */}
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 space-y-1">
          <span className="text-xs font-medium text-zinc-300">Placeholders (click to edit, drag on canvas)</span>
          {Object.entries(layout).map(([key, val]) => (
            <button
              key={key}
              onClick={() => setSelectedField(key)}
              className={`w-full text-left px-2 py-1.5 rounded text-xs flex items-center gap-2 transition-colors ${
                selectedField === key ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/50" : "text-zinc-400 hover:bg-zinc-800"
              }`}
            >
              <Move className="h-3 w-3 shrink-0 opacity-50" />
              <span className="truncate">{val.label}</span>
              <span className="ml-auto text-[10px] opacity-50">{val.fontSize}pt</span>
            </button>
          ))}
        </div>

        {/* Selected Field Controls */}
        {sf && (
          <div className="bg-zinc-900 border border-indigo-500/50 rounded-lg p-3 space-y-2">
            <span className="text-xs font-medium text-indigo-300">{sf.label}</span>
            <div>
              <Label className="text-[10px] text-zinc-400">Font Size: {sf.fontSize}pt</Label>
              <Slider value={[sf.fontSize]} onValueChange={([v]) => updateField(selectedField, "fontSize", v)} min={6} max={28} step={0.5} className="mt-1" />
            </div>
            <div>
              <Label className="text-[10px] text-zinc-400">Width: {sf.width}%</Label>
              <Slider value={[sf.width]} onValueChange={([v]) => updateField(selectedField, "width", v)} min={10} max={90} step={1} className="mt-1" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-[10px] text-zinc-400">X: {sf.x}%</Label>
                <Slider value={[sf.x]} onValueChange={([v]) => updateField(selectedField, "x", v)} min={0} max={95} step={0.5} className="mt-1" />
              </div>
              <div>
                <Label className="text-[10px] text-zinc-400">Y: {sf.y}%</Label>
                <Slider value={[sf.y]} onValueChange={([v]) => updateField(selectedField, "y", v)} min={0} max={98} step={0.5} className="mt-1" />
              </div>
            </div>
            <div className="flex gap-2 items-center flex-wrap">
              <Select value={sf.fontWeight} onValueChange={(v) => updateField(selectedField, "fontWeight", v)}>
                <SelectTrigger className="h-7 text-xs bg-zinc-800 border-zinc-600 w-24"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="bold">Bold</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sf.textAlign} onValueChange={(v) => updateField(selectedField, "textAlign", v)}>
                <SelectTrigger className="h-7 text-xs bg-zinc-800 border-zinc-600 w-24"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="left">Left</SelectItem>
                  <SelectItem value="center">Center</SelectItem>
                  <SelectItem value="right">Right</SelectItem>
                </SelectContent>
              </Select>
              <input
                type="color" value={sf.color}
                onChange={(e) => updateField(selectedField, "color", e.target.value)}
                className="w-7 h-7 rounded border border-zinc-600 cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          <Button onClick={saveLayout} disabled={saving} variant="outline" size="sm" className="border-zinc-600 text-zinc-200">
            {saving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Save className="h-3 w-3 mr-1" />} Save Layout
          </Button>
          <Button onClick={() => { setLayout(DEFAULT_LAYOUT); toast.info("Reset to defaults"); }} variant="ghost" size="sm" className="text-zinc-400">
            <RotateCcw className="h-3 w-3 mr-1" /> Reset
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => handleGenerate(false)} disabled={generating || !selectedParticipant} size="sm" className="bg-emerald-600 hover:bg-emerald-700">
            {generating ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <FileDown className="h-3 w-3 mr-1" />} Generate Cert
          </Button>
          <Button onClick={() => handleGenerate(true)} disabled={generating || !selectedSession} size="sm" className="bg-amber-600 hover:bg-amber-700">
            <FileDown className="h-3 w-3 mr-1" /> Generate All
          </Button>
          <Button onClick={() => handleGenerate(true, true)} disabled={generating || !selectedSession} variant="outline" size="sm" className="border-amber-600 text-amber-400">
            Force All
          </Button>
        </div>
      </div>

      {/* Right: Canvas */}
      <div className="flex-1 order-1 xl:order-2">
        <div
          ref={canvasRef}
          data-testid="certificate-canvas"
          className="relative bg-white rounded shadow-lg overflow-hidden select-none"
          style={{ aspectRatio: "1656/2341", maxHeight: "85vh", margin: "0 auto" }}
        >
          <img
            src={`${API}/api/static/templates/cert_background.png`}
            alt="Certificate Background"
            className="w-full h-full object-contain"
            draggable={false}
            onLoad={() => setBgLoaded(true)}
            onError={() => toast.error("Background image not found")}
          />
          {bgLoaded && Object.entries(layout).map(([key, f]) => (
            <div
              key={key}
              data-testid={`placeholder-${key}`}
              onMouseDown={(e) => handleMouseDown(e, key)}
              onTouchStart={(e) => handleMouseDown(e, key)}
              onClick={(e) => { e.stopPropagation(); setSelectedField(key); }}
              className={`absolute cursor-move transition-shadow ${
                selectedField === key ? "ring-2 ring-indigo-500 bg-indigo-500/10" : "hover:ring-1 hover:ring-blue-400/50"
              }`}
              style={{
                left: `${f.x}%`,
                top: `${f.y}%`,
                width: `${f.width}%`,
                fontSize: `${f.fontSize * 0.55}px`,
                fontWeight: f.fontWeight,
                textAlign: f.textAlign,
                color: f.color,
                lineHeight: 1.2,
                fontFamily: "'Calibri', 'Arial', sans-serif",
                whiteSpace: "nowrap",
                overflow: "visible",
                padding: "1px 3px",
              }}
            >
              {previewData[key] || `{{${key.toUpperCase()}}}`}
              {selectedField === key && (
                <div className="absolute -top-3 -left-1 bg-indigo-600 text-white text-[8px] px-1 rounded whitespace-nowrap">
                  {f.label}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CertificateDesigner;
