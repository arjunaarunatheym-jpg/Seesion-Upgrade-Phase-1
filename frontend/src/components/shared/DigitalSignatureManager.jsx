import { useState, useRef } from 'react';
import { axiosInstance } from '../../App';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { toast } from 'sonner';
import { Upload, Trash2, Pen } from 'lucide-react';

export const DigitalSignatureManager = ({ user, onUpdate }) => {
  const [signature, setSignature] = useState(user?.digital_signature || '');
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);

  const handleUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 500000) {
      toast.error('Signature image must be under 500KB');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      setSignature(ev.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axiosInstance.put('/users/profile', { digital_signature: signature });
      toast.success('Digital signature saved');
      if (onUpdate) onUpdate(signature);
    } catch {
      toast.error('Failed to save signature');
    } finally { setSaving(false); }
  };

  const handleClear = async () => {
    setSignature('');
    try {
      await axiosInstance.put('/users/profile', { digital_signature: '' });
      toast.success('Signature removed');
      if (onUpdate) onUpdate('');
    } catch {
      toast.error('Failed to remove signature');
    }
  };

  return (
    <Card data-testid="digital-signature-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Pen className="w-4 h-4" />
          Digital Signature
        </CardTitle>
        <CardDescription>Upload your signature image. It will appear on quotations, invoices, and other official documents.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {signature ? (
          <div className="flex items-center gap-4">
            <div className="border rounded-lg p-3 bg-white inline-block">
              <img src={signature} alt="Signature" className="max-h-16 max-w-[200px] object-contain" data-testid="signature-preview" />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} data-testid="change-signature-btn">
                <Upload className="w-3 h-3 mr-1" />Change
              </Button>
              <Button variant="outline" size="sm" onClick={handleClear} className="text-red-600 hover:text-red-700" data-testid="remove-signature-btn">
                <Trash2 className="w-3 h-3 mr-1" />Remove
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="outline" onClick={() => fileRef.current?.click()} data-testid="upload-signature-btn">
            <Upload className="w-4 h-4 mr-2" />Upload Signature Image
          </Button>
        )}
        <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleUpload} />
        {signature && signature !== (user?.digital_signature || '') && (
          <Button onClick={handleSave} disabled={saving} size="sm" data-testid="save-signature-btn">
            {saving ? 'Saving...' : 'Save Signature'}
          </Button>
        )}
        <p className="text-xs text-gray-500">Recommended: PNG with transparent background, max 500KB. Ideal size: 300x100 pixels.</p>
      </CardContent>
    </Card>
  );
};
