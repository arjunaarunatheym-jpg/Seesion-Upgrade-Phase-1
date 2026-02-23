/**
 * Certificate Template Designer
 * 
 * Features:
 * - Custom Designer with drag-drop positioning
 * - Multiple logos support
 * - Pre-built templates
 * - Live preview
 */
import { useState, useEffect, useRef } from 'react';
import { axiosInstance } from '../../App';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Slider } from '../ui/slider';
import { Switch } from '../ui/switch';
import { 
  Palette, Image as ImageIcon, Type, FileSignature, Upload, Save, 
  Trash2, Move, Plus, Eye, Download, RotateCcw, Layers, Settings,
  GripVertical, ChevronUp, ChevronDown, Copy, X, Check
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Pre-built template configurations
const PRE_BUILT_TEMPLATES = {
  classic_gold: {
    name: 'Classic Gold',
    description: 'Traditional elegant design with gold accents',
    background: 'linear-gradient(135deg, #fefcea 0%, #f1da36 100%)',
    backgroundColor: '#fffef5',
    borderStyle: '8px double #c9a227',
    elements: [
      { id: 'logo', type: 'logo', x: 50, y: 8, width: 100, height: 60, label: 'Company Logo' },
      { id: 'title', type: 'text', x: 50, y: 20, text: 'CERTIFICATE OF COMPLETION', fontSize: 32, fontFamily: 'Georgia', fontWeight: 'bold', color: '#8B4513' },
      { id: 'subtitle', type: 'text', x: 50, y: 28, text: 'This is to certify that', fontSize: 14, fontFamily: 'Georgia', fontStyle: 'italic', color: '#555' },
      { id: 'participant', type: 'text', x: 50, y: 38, text: '{Participant Name}', fontSize: 28, fontFamily: 'Great Vibes, cursive', color: '#1a365d' },
      { id: 'body1', type: 'text', x: 50, y: 48, text: 'has successfully completed the', fontSize: 14, fontFamily: 'Georgia', color: '#555' },
      { id: 'program', type: 'text', x: 50, y: 56, text: '{Program Name}', fontSize: 20, fontFamily: 'Georgia', fontWeight: 'bold', color: '#1a365d' },
      { id: 'date', type: 'text', x: 50, y: 66, text: 'on {Date}', fontSize: 14, fontFamily: 'Georgia', color: '#555' },
      { id: 'sig1', type: 'signature', x: 25, y: 80, width: 100, height: 40, label: 'Director' },
      { id: 'sig2', type: 'signature', x: 75, y: 80, width: 100, height: 40, label: 'Manager' },
      { id: 'certnum', type: 'text', x: 50, y: 94, text: '{Certificate Number}', fontSize: 10, fontFamily: 'Arial', color: '#888' },
    ]
  },
  modern_minimal: {
    name: 'Modern Minimal',
    description: 'Clean contemporary design with lots of whitespace',
    background: '#ffffff',
    backgroundColor: '#ffffff',
    borderStyle: '2px solid #e5e7eb',
    elements: [
      { id: 'logo', type: 'logo', x: 50, y: 6, width: 80, height: 50, label: 'Company Logo' },
      { id: 'line1', type: 'line', x: 50, y: 14, width: 60, color: '#3b82f6', height: 3 },
      { id: 'title', type: 'text', x: 50, y: 22, text: 'Certificate of Completion', fontSize: 28, fontFamily: 'Inter, sans-serif', fontWeight: '300', color: '#1f2937' },
      { id: 'participant', type: 'text', x: 50, y: 38, text: '{Participant Name}', fontSize: 32, fontFamily: 'Inter, sans-serif', fontWeight: '600', color: '#111827' },
      { id: 'body1', type: 'text', x: 50, y: 50, text: 'Successfully completed', fontSize: 14, fontFamily: 'Inter, sans-serif', color: '#6b7280' },
      { id: 'program', type: 'text', x: 50, y: 58, text: '{Program Name}', fontSize: 18, fontFamily: 'Inter, sans-serif', fontWeight: '500', color: '#1f2937' },
      { id: 'date', type: 'text', x: 50, y: 68, text: '{Date}', fontSize: 14, fontFamily: 'Inter, sans-serif', color: '#6b7280' },
      { id: 'sig1', type: 'signature', x: 30, y: 82, width: 100, height: 40, label: 'Authorized Signatory' },
      { id: 'certnum', type: 'text', x: 85, y: 92, text: '{Certificate Number}', fontSize: 9, fontFamily: 'monospace', color: '#9ca3af' },
    ]
  },
  corporate_blue: {
    name: 'Corporate Blue',
    description: 'Professional design with blue corporate theme',
    background: 'linear-gradient(180deg, #1e3a5f 0%, #1e3a5f 15%, #ffffff 15%, #ffffff 100%)',
    backgroundColor: '#ffffff',
    borderStyle: 'none',
    elements: [
      { id: 'logo', type: 'logo', x: 50, y: 5, width: 80, height: 50, label: 'Company Logo' },
      { id: 'title', type: 'text', x: 50, y: 10, text: 'CERTIFICATE', fontSize: 24, fontFamily: 'Arial', fontWeight: 'bold', color: '#ffffff' },
      { id: 'subtitle', type: 'text', x: 50, y: 22, text: 'OF COMPLETION', fontSize: 18, fontFamily: 'Arial', letterSpacing: '4px', color: '#1e3a5f' },
      { id: 'line1', type: 'line', x: 50, y: 27, width: 30, color: '#c9a227', height: 3 },
      { id: 'body1', type: 'text', x: 50, y: 34, text: 'This is to certify that', fontSize: 12, fontFamily: 'Arial', color: '#666' },
      { id: 'participant', type: 'text', x: 50, y: 44, text: '{Participant Name}', fontSize: 26, fontFamily: 'Times New Roman', fontWeight: 'bold', color: '#1e3a5f' },
      { id: 'body2', type: 'text', x: 50, y: 54, text: 'has successfully completed the training program', fontSize: 12, fontFamily: 'Arial', color: '#666' },
      { id: 'program', type: 'text', x: 50, y: 62, text: '{Program Name}', fontSize: 18, fontFamily: 'Arial', fontWeight: 'bold', color: '#1e3a5f' },
      { id: 'date', type: 'text', x: 50, y: 72, text: 'Awarded on {Date}', fontSize: 12, fontFamily: 'Arial', color: '#666' },
      { id: 'sig1', type: 'signature', x: 25, y: 82, width: 100, height: 40, label: 'Training Director' },
      { id: 'sig2', type: 'signature', x: 75, y: 82, width: 100, height: 40, label: 'Program Manager' },
      { id: 'certnum', type: 'text', x: 50, y: 96, text: '{Certificate Number}', fontSize: 9, fontFamily: 'Arial', color: '#999' },
    ]
  }
};

// Default empty template for custom designer
const DEFAULT_TEMPLATE = {
  name: 'Custom Template',
  background: '#ffffff',
  backgroundColor: '#ffffff',
  borderStyle: '1px solid #e5e7eb',
  elements: []
};

const CertificateDesigner = () => {
  const [activeMode, setActiveMode] = useState('templates'); // 'templates' or 'custom'
  const [template, setTemplate] = useState({ ...DEFAULT_TEMPLATE });
  const [selectedElement, setSelectedElement] = useState(null);
  const [savedTemplates, setSavedTemplates] = useState([]);
  const [saving, setSaving] = useState(false);
  const [templateName, setTemplateName] = useState('My Certificate');
  const [previewTemplate, setPreviewTemplate] = useState(null);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [draggedElement, setDraggedElement] = useState(null);
  const previewRef = useRef(null);
  
  // Sample data for preview
  const sampleData = {
    participantName: 'JOHN DOE',
    programName: 'Defensive Driving Programme',
    date: '23 February 2026',
    certificateNumber: 'CERT/MDDRC/2026/02/00001',
    companyName: 'MDDRC Sdn Bhd'
  };

  useEffect(() => {
    loadSavedTemplates();
  }, []);

  const loadSavedTemplates = async () => {
    try {
      const response = await axiosInstance.get('/settings/certificate-templates');
      setSavedTemplates(response.data || []);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const handleSelectPrebuilt = (templateKey) => {
    const selected = PRE_BUILT_TEMPLATES[templateKey];
    setPreviewTemplate({ ...selected, key: templateKey });
  };

  const handleUseTemplate = () => {
    if (previewTemplate) {
      setTemplate({ ...previewTemplate });
      setActiveMode('custom');
      setTemplateName(previewTemplate.name + ' (Copy)');
      toast.success('Template loaded! You can now customize it.');
    }
  };

  const handleAddElement = (type) => {
    const newElement = {
      id: `${type}_${Date.now()}`,
      type,
      x: 50,
      y: 50,
      ...(type === 'text' && { 
        text: 'New Text', 
        fontSize: 16, 
        fontFamily: 'Arial', 
        fontWeight: 'normal',
        fontStyle: 'normal',
        color: '#000000' 
      }),
      ...(type === 'logo' && { 
        width: 100, 
        height: 60, 
        imageUrl: null,
        label: 'Logo' 
      }),
      ...(type === 'signature' && { 
        width: 100, 
        height: 40, 
        imageUrl: null,
        label: 'Signature' 
      }),
      ...(type === 'line' && { 
        width: 40, 
        height: 2, 
        color: '#000000' 
      }),
    };
    setTemplate(prev => ({
      ...prev,
      elements: [...prev.elements, newElement]
    }));
    setSelectedElement(newElement.id);
  };

  const handleUpdateElement = (id, updates) => {
    setTemplate(prev => ({
      ...prev,
      elements: prev.elements.map(el => 
        el.id === id ? { ...el, ...updates } : el
      )
    }));
  };

  const handleDeleteElement = (id) => {
    setTemplate(prev => ({
      ...prev,
      elements: prev.elements.filter(el => el.id !== id)
    }));
    setSelectedElement(null);
  };

  const handleImageUpload = async (elementId, file, type = 'logo') => {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);
    
    try {
      const response = await axiosInstance.post('/settings/certificate-assets', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      handleUpdateElement(elementId, { imageUrl: response.data.url });
      toast.success(`${type === 'logo' ? 'Logo' : 'Signature'} uploaded!`);
    } catch (error) {
      toast.error('Failed to upload image');
    }
  };

  const handleSaveTemplate = async () => {
    setSaving(true);
    try {
      const templateData = {
        name: templateName,
        ...template,
        is_default: savedTemplates.length === 0
      };
      
      await axiosInstance.post('/settings/certificate-templates', templateData);
      toast.success('Template saved successfully!');
      setShowSaveDialog(false);
      loadSavedTemplates();
    } catch (error) {
      toast.error('Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  const handleLoadSavedTemplate = async (templateId) => {
    try {
      const response = await axiosInstance.get(`/settings/certificate-templates/${templateId}`);
      setTemplate(response.data);
      setTemplateName(response.data.name);
      setActiveMode('custom');
      toast.success('Template loaded!');
    } catch (error) {
      toast.error('Failed to load template');
    }
  };

  const handleDeleteSavedTemplate = async (templateId) => {
    if (!confirm('Are you sure you want to delete this template?')) return;
    try {
      await axiosInstance.delete(`/settings/certificate-templates/${templateId}`);
      toast.success('Template deleted');
      loadSavedTemplates();
    } catch (error) {
      toast.error('Failed to delete template');
    }
  };

  // Drag handling for positioning elements
  const handleDragStart = (e, elementId) => {
    setDraggedElement(elementId);
    setSelectedElement(elementId);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    if (!draggedElement || !previewRef.current) return;
    
    const rect = previewRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    
    handleUpdateElement(draggedElement, { 
      x: Math.max(5, Math.min(95, x)), 
      y: Math.max(5, Math.min(95, y)) 
    });
    setDraggedElement(null);
  };

  // Render text with placeholder replacement
  const renderText = (text) => {
    return text
      .replace('{Participant Name}', sampleData.participantName)
      .replace('{Program Name}', sampleData.programName)
      .replace('{Date}', sampleData.date)
      .replace('{Certificate Number}', sampleData.certificateNumber)
      .replace('{Company Name}', sampleData.companyName);
  };

  // Get selected element data
  const selectedElementData = template.elements.find(el => el.id === selectedElement);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileSignature className="w-5 h-5" />
          Certificate Template Designer
        </CardTitle>
        <CardDescription>
          Create custom certificates or choose from pre-built templates. All changes show in live preview.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activeMode} onValueChange={setActiveMode} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-4">
            <TabsTrigger value="templates" className="flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Pre-built Templates
            </TabsTrigger>
            <TabsTrigger value="custom" className="flex items-center gap-2">
              <Palette className="w-4 h-4" />
              Custom Designer
            </TabsTrigger>
          </TabsList>

          {/* Pre-built Templates Tab */}
          <TabsContent value="templates" className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(PRE_BUILT_TEMPLATES).map(([key, tmpl]) => (
                <div 
                  key={key}
                  onClick={() => handleSelectPrebuilt(key)}
                  className={`cursor-pointer rounded-lg border-2 p-3 transition-all hover:shadow-lg ${
                    previewTemplate?.key === key ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                >
                  <div 
                    className="aspect-[1.4/1] rounded mb-2 flex items-center justify-center text-xs text-gray-500"
                    style={{ 
                      background: tmpl.background,
                      border: tmpl.borderStyle 
                    }}
                  >
                    <span className="bg-white/80 px-2 py-1 rounded">{tmpl.name}</span>
                  </div>
                  <h4 className="font-medium text-sm">{tmpl.name}</h4>
                  <p className="text-xs text-gray-500">{tmpl.description}</p>
                </div>
              ))}
            </div>

            {/* Live Preview for Pre-built */}
            {previewTemplate && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">Live Preview: {previewTemplate.name}</h3>
                  <Button onClick={handleUseTemplate}>
                    <Copy className="w-4 h-4 mr-2" />
                    Use This Template
                  </Button>
                </div>
                <div 
                  className="aspect-[1.4/1] rounded-lg shadow-lg mx-auto max-w-3xl relative overflow-hidden"
                  style={{ 
                    background: previewTemplate.background,
                    border: previewTemplate.borderStyle,
                    backgroundColor: previewTemplate.backgroundColor
                  }}
                >
                  {previewTemplate.elements.map(el => (
                    <div
                      key={el.id}
                      className="absolute transform -translate-x-1/2"
                      style={{
                        left: `${el.x}%`,
                        top: `${el.y}%`,
                      }}
                    >
                      {el.type === 'text' && (
                        <div
                          style={{
                            fontSize: `${el.fontSize * 0.6}px`,
                            fontFamily: el.fontFamily,
                            fontWeight: el.fontWeight || 'normal',
                            fontStyle: el.fontStyle || 'normal',
                            color: el.color,
                            letterSpacing: el.letterSpacing || 'normal',
                            textAlign: 'center',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {renderText(el.text)}
                        </div>
                      )}
                      {el.type === 'logo' && (
                        <div 
                          className="flex items-center justify-center bg-gray-100 rounded"
                          style={{ width: el.width * 0.8, height: el.height * 0.8 }}
                        >
                          <ImageIcon className="w-6 h-6 text-gray-400" />
                        </div>
                      )}
                      {el.type === 'signature' && (
                        <div className="text-center">
                          <div 
                            className="border-b border-gray-400 mb-1"
                            style={{ width: el.width * 0.8 }}
                          />
                          <span className="text-xs text-gray-600">{el.label}</span>
                        </div>
                      )}
                      {el.type === 'line' && (
                        <div 
                          style={{ 
                            width: `${el.width * 2}px`, 
                            height: el.height, 
                            backgroundColor: el.color 
                          }} 
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Saved Templates */}
            {savedTemplates.length > 0 && (
              <div className="mt-6 pt-6 border-t">
                <h3 className="font-semibold mb-3">Your Saved Templates</h3>
                <div className="grid grid-cols-4 gap-3">
                  {savedTemplates.map(tmpl => (
                    <div key={tmpl.id} className="border rounded-lg p-2 group relative">
                      <div 
                        className="aspect-[1.4/1] rounded bg-gray-100 mb-2 cursor-pointer"
                        onClick={() => handleLoadSavedTemplate(tmpl.id)}
                      />
                      <p className="text-sm font-medium truncate">{tmpl.name}</p>
                      <button
                        onClick={() => handleDeleteSavedTemplate(tmpl.id)}
                        className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>

          {/* Custom Designer Tab */}
          <TabsContent value="custom" className="space-y-4">
            <div className="flex gap-4">
              {/* Left Panel - Elements */}
              <div className="w-64 space-y-4 flex-shrink-0">
                {/* Add Elements */}
                <div className="border rounded-lg p-3">
                  <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Add Elements
                  </h4>
                  <div className="grid grid-cols-2 gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleAddElement('logo')}>
                      <ImageIcon className="w-3 h-3 mr-1" />
                      Logo
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleAddElement('text')}>
                      <Type className="w-3 h-3 mr-1" />
                      Text
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleAddElement('signature')}>
                      <FileSignature className="w-3 h-3 mr-1" />
                      Signature
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleAddElement('line')}>
                      <div className="w-3 h-0.5 bg-current mr-1" />
                      Line
                    </Button>
                  </div>
                </div>

                {/* Elements List */}
                <div className="border rounded-lg p-3">
                  <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                    <Layers className="w-4 h-4" />
                    Elements ({template.elements.length})
                  </h4>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {template.elements.map(el => (
                      <div
                        key={el.id}
                        onClick={() => setSelectedElement(el.id)}
                        className={`flex items-center justify-between p-2 rounded cursor-pointer text-xs ${
                          selectedElement === el.id ? 'bg-blue-100 border border-blue-300' : 'hover:bg-gray-100'
                        }`}
                      >
                        <span className="flex items-center gap-1 truncate">
                          {el.type === 'text' && <Type className="w-3 h-3" />}
                          {el.type === 'logo' && <ImageIcon className="w-3 h-3" />}
                          {el.type === 'signature' && <FileSignature className="w-3 h-3" />}
                          {el.type === 'line' && <div className="w-3 h-0.5 bg-current" />}
                          <span className="truncate">
                            {el.type === 'text' ? el.text?.substring(0, 15) + '...' : el.label || el.type}
                          </span>
                        </span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDeleteElement(el.id); }}
                          className="text-red-500 hover:text-red-700"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                    {template.elements.length === 0 && (
                      <p className="text-xs text-gray-400 text-center py-2">No elements added yet</p>
                    )}
                  </div>
                </div>

                {/* Background Settings */}
                <div className="border rounded-lg p-3">
                  <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                    <Settings className="w-4 h-4" />
                    Background
                  </h4>
                  <div className="space-y-2">
                    <div>
                      <Label className="text-xs">Color</Label>
                      <div className="flex gap-2">
                        <Input
                          type="color"
                          value={template.backgroundColor || '#ffffff'}
                          onChange={(e) => setTemplate(prev => ({ 
                            ...prev, 
                            backgroundColor: e.target.value,
                            background: e.target.value 
                          }))}
                          className="w-10 h-8 p-0"
                        />
                        <Input
                          type="text"
                          value={template.backgroundColor || '#ffffff'}
                          onChange={(e) => setTemplate(prev => ({ 
                            ...prev, 
                            backgroundColor: e.target.value,
                            background: e.target.value 
                          }))}
                          className="flex-1 text-xs h-8"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs">Border</Label>
                      <Select
                        value={template.borderStyle || 'none'}
                        onValueChange={(v) => setTemplate(prev => ({ ...prev, borderStyle: v }))}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">None</SelectItem>
                          <SelectItem value="1px solid #e5e7eb">Thin Gray</SelectItem>
                          <SelectItem value="2px solid #1e3a5f">Blue Border</SelectItem>
                          <SelectItem value="4px double #c9a227">Gold Double</SelectItem>
                          <SelectItem value="8px double #c9a227">Thick Gold</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                {/* Selected Element Properties */}
                {selectedElementData && (
                  <div className="border rounded-lg p-3 bg-blue-50">
                    <h4 className="font-medium text-sm mb-2">Edit: {selectedElementData.type}</h4>
                    
                    {/* Position */}
                    <div className="grid grid-cols-2 gap-2 mb-2">
                      <div>
                        <Label className="text-xs">X Position (%)</Label>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          value={Math.round(selectedElementData.x)}
                          onChange={(e) => handleUpdateElement(selectedElement, { x: parseFloat(e.target.value) })}
                          className="h-7 text-xs"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Y Position (%)</Label>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          value={Math.round(selectedElementData.y)}
                          onChange={(e) => handleUpdateElement(selectedElement, { y: parseFloat(e.target.value) })}
                          className="h-7 text-xs"
                        />
                      </div>
                    </div>

                    {/* Text Properties */}
                    {selectedElementData.type === 'text' && (
                      <div className="space-y-2">
                        <div>
                          <Label className="text-xs">Text</Label>
                          <Input
                            value={selectedElementData.text}
                            onChange={(e) => handleUpdateElement(selectedElement, { text: e.target.value })}
                            className="h-7 text-xs"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <Label className="text-xs">Font Size</Label>
                            <Input
                              type="number"
                              value={selectedElementData.fontSize}
                              onChange={(e) => handleUpdateElement(selectedElement, { fontSize: parseInt(e.target.value) })}
                              className="h-7 text-xs"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Color</Label>
                            <Input
                              type="color"
                              value={selectedElementData.color}
                              onChange={(e) => handleUpdateElement(selectedElement, { color: e.target.value })}
                              className="h-7 w-full"
                            />
                          </div>
                        </div>
                        <div>
                          <Label className="text-xs">Font Family</Label>
                          <Select
                            value={selectedElementData.fontFamily}
                            onValueChange={(v) => handleUpdateElement(selectedElement, { fontFamily: v })}
                          >
                            <SelectTrigger className="h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Arial">Arial</SelectItem>
                              <SelectItem value="Georgia">Georgia</SelectItem>
                              <SelectItem value="Times New Roman">Times New Roman</SelectItem>
                              <SelectItem value="Inter, sans-serif">Inter</SelectItem>
                              <SelectItem value="Great Vibes, cursive">Great Vibes (Script)</SelectItem>
                              <SelectItem value="monospace">Monospace</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant={selectedElementData.fontWeight === 'bold' ? 'default' : 'outline'}
                            onClick={() => handleUpdateElement(selectedElement, { 
                              fontWeight: selectedElementData.fontWeight === 'bold' ? 'normal' : 'bold' 
                            })}
                            className="h-7 w-8 p-0"
                          >
                            <span className="font-bold">B</span>
                          </Button>
                          <Button
                            size="sm"
                            variant={selectedElementData.fontStyle === 'italic' ? 'default' : 'outline'}
                            onClick={() => handleUpdateElement(selectedElement, { 
                              fontStyle: selectedElementData.fontStyle === 'italic' ? 'normal' : 'italic' 
                            })}
                            className="h-7 w-8 p-0"
                          >
                            <span className="italic">I</span>
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Logo/Signature Properties */}
                    {(selectedElementData.type === 'logo' || selectedElementData.type === 'signature') && (
                      <div className="space-y-2">
                        <div>
                          <Label className="text-xs">Label</Label>
                          <Input
                            value={selectedElementData.label || ''}
                            onChange={(e) => handleUpdateElement(selectedElement, { label: e.target.value })}
                            className="h-7 text-xs"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <Label className="text-xs">Width</Label>
                            <Input
                              type="number"
                              value={selectedElementData.width}
                              onChange={(e) => handleUpdateElement(selectedElement, { width: parseInt(e.target.value) })}
                              className="h-7 text-xs"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Height</Label>
                            <Input
                              type="number"
                              value={selectedElementData.height}
                              onChange={(e) => handleUpdateElement(selectedElement, { height: parseInt(e.target.value) })}
                              className="h-7 text-xs"
                            />
                          </div>
                        </div>
                        <div>
                          <Label className="text-xs">Upload Image</Label>
                          <Input
                            type="file"
                            accept="image/*"
                            onChange={(e) => handleImageUpload(selectedElement, e.target.files[0], selectedElementData.type)}
                            className="h-7 text-xs"
                          />
                        </div>
                      </div>
                    )}

                    {/* Line Properties */}
                    {selectedElementData.type === 'line' && (
                      <div className="space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <Label className="text-xs">Width (%)</Label>
                            <Input
                              type="number"
                              value={selectedElementData.width}
                              onChange={(e) => handleUpdateElement(selectedElement, { width: parseInt(e.target.value) })}
                              className="h-7 text-xs"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Thickness</Label>
                            <Input
                              type="number"
                              value={selectedElementData.height}
                              onChange={(e) => handleUpdateElement(selectedElement, { height: parseInt(e.target.value) })}
                              className="h-7 text-xs"
                            />
                          </div>
                        </div>
                        <div>
                          <Label className="text-xs">Color</Label>
                          <Input
                            type="color"
                            value={selectedElementData.color}
                            onChange={(e) => handleUpdateElement(selectedElement, { color: e.target.value })}
                            className="h-7 w-full"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="space-y-2">
                  <Button 
                    className="w-full" 
                    onClick={() => setShowSaveDialog(true)}
                    disabled={template.elements.length === 0}
                  >
                    <Save className="w-4 h-4 mr-2" />
                    Save Template
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={() => {
                      setTemplate({ ...DEFAULT_TEMPLATE });
                      setSelectedElement(null);
                      setTemplateName('My Certificate');
                    }}
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Reset
                  </Button>
                </div>
              </div>

              {/* Right Panel - Live Preview */}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Eye className="w-4 h-4" />
                    Live Preview
                  </h3>
                  <span className="text-xs text-gray-500">Drag elements to reposition</span>
                </div>
                <div 
                  ref={previewRef}
                  className="aspect-[1.4/1] rounded-lg shadow-lg relative overflow-hidden"
                  style={{ 
                    background: template.background || template.backgroundColor,
                    border: template.borderStyle || '1px solid #e5e7eb',
                    backgroundColor: template.backgroundColor
                  }}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                >
                  {template.elements.map(el => (
                    <div
                      key={el.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, el.id)}
                      onClick={() => setSelectedElement(el.id)}
                      className={`absolute transform -translate-x-1/2 cursor-move transition-all ${
                        selectedElement === el.id ? 'ring-2 ring-blue-500 ring-offset-2' : ''
                      }`}
                      style={{
                        left: `${el.x}%`,
                        top: `${el.y}%`,
                      }}
                    >
                      {el.type === 'text' && (
                        <div
                          style={{
                            fontSize: `${el.fontSize * 0.6}px`,
                            fontFamily: el.fontFamily,
                            fontWeight: el.fontWeight || 'normal',
                            fontStyle: el.fontStyle || 'normal',
                            color: el.color,
                            letterSpacing: el.letterSpacing || 'normal',
                            textAlign: 'center',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {renderText(el.text)}
                        </div>
                      )}
                      {el.type === 'logo' && (
                        <div 
                          className="flex items-center justify-center bg-gray-100/80 rounded border-2 border-dashed border-gray-300"
                          style={{ width: el.width * 0.8, height: el.height * 0.8 }}
                        >
                          {el.imageUrl ? (
                            <img src={`${API_URL}${el.imageUrl}`} alt={el.label} className="max-w-full max-h-full object-contain" />
                          ) : (
                            <div className="text-center">
                              <ImageIcon className="w-6 h-6 text-gray-400 mx-auto" />
                              <span className="text-xs text-gray-400">{el.label}</span>
                            </div>
                          )}
                        </div>
                      )}
                      {el.type === 'signature' && (
                        <div className="text-center">
                          {el.imageUrl ? (
                            <img src={`${API_URL}${el.imageUrl}`} alt={el.label} style={{ width: el.width * 0.8, height: el.height * 0.8 }} className="object-contain" />
                          ) : (
                            <div 
                              className="border-b-2 border-gray-400 mb-1"
                              style={{ width: el.width * 0.8 }}
                            />
                          )}
                          <span className="text-xs text-gray-600">{el.label}</span>
                        </div>
                      )}
                      {el.type === 'line' && (
                        <div 
                          style={{ 
                            width: `${el.width * 3}px`, 
                            height: el.height, 
                            backgroundColor: el.color 
                          }} 
                        />
                      )}
                    </div>
                  ))}
                  
                  {template.elements.length === 0 && (
                    <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                      <div className="text-center">
                        <Layers className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p>Add elements from the left panel</p>
                        <p className="text-sm">or select a pre-built template</p>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Placeholders Help */}
                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                  <h4 className="text-sm font-medium mb-2">Available Placeholders:</h4>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <code className="bg-gray-200 px-2 py-1 rounded">{'{Participant Name}'}</code>
                    <code className="bg-gray-200 px-2 py-1 rounded">{'{Program Name}'}</code>
                    <code className="bg-gray-200 px-2 py-1 rounded">{'{Date}'}</code>
                    <code className="bg-gray-200 px-2 py-1 rounded">{'{Certificate Number}'}</code>
                    <code className="bg-gray-200 px-2 py-1 rounded">{'{Company Name}'}</code>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Save Dialog */}
        <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Save Certificate Template</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label>Template Name</Label>
                <Input
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="Enter template name"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowSaveDialog(false)}>Cancel</Button>
              <Button onClick={handleSaveTemplate} disabled={saving || !templateName.trim()}>
                {saving ? 'Saving...' : 'Save Template'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};

export default CertificateDesigner;
