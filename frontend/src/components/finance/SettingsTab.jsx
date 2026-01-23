/**
 * SettingsTab Component - Extracted from FinanceDashboard
 * Manages company settings, billing parties, social media links, and document styling
 */
import { useState, useEffect } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Settings, Plus, Edit, X, FileText, Globe } from "lucide-react";
import { FaFacebook, FaInstagram, FaTiktok, FaYoutube, FaTwitter, FaLinkedin } from 'react-icons/fa';

const SettingsTab = ({ 
  companySettings, 
  setCompanySettings, 
  billingParties,
  loadBillingParties,
  socialMediaLinks,
  setSocialMediaLinks
}) => {
  const [settingsLoading, setSettingsLoading] = useState(false);
  
  // Billing Party State
  const [showBillingPartyModal, setShowBillingPartyModal] = useState(false);
  const [editingBillingParty, setEditingBillingParty] = useState(null);
  const [billingPartyForm, setBillingPartyForm] = useState({
    name: '',
    registration_no: '',
    address_line1: '',
    address_line2: '',
    city: '',
    postcode: '',
    state: '',
    country: 'Malaysia',
    phone: '',
    email: '',
    contact_person: ''
  });

  // Social Media State
  const [showSocialMediaModal, setShowSocialMediaModal] = useState(false);
  const [editingSocialMedia, setEditingSocialMedia] = useState(null);
  const [socialMediaForm, setSocialMediaForm] = useState({
    platform: '',
    url: '',
    icon: 'globe',
    is_active: true
  });

  // Save Settings Handler
  const handleSaveSettings = async () => {
    setSettingsLoading(true);
    try {
      await axiosInstance.put('/finance/company-settings', companySettings);
      toast.success('Company settings saved');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSettingsLoading(false);
    }
  };

  // Billing Party Handlers
  const handleBillingPartySubmit = async () => {
    if (!billingPartyForm.name.trim()) {
      toast.error('Party name is required');
      return;
    }
    try {
      if (editingBillingParty) {
        await axiosInstance.put(`/finance/billing-parties/${editingBillingParty.id}`, billingPartyForm);
        toast.success('Billing party updated');
      } else {
        await axiosInstance.post('/finance/billing-parties', billingPartyForm);
        toast.success('Billing party created');
      }
      setShowBillingPartyModal(false);
      setEditingBillingParty(null);
      loadBillingParties();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save billing party');
    }
  };

  const handleDeleteBillingParty = async (partyId) => {
    if (!confirm('Delete this billing party?')) return;
    try {
      await axiosInstance.delete(`/finance/billing-parties/${partyId}`);
      toast.success('Billing party deleted');
      loadBillingParties();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete billing party');
    }
  };

  const openEditBillingParty = (party) => {
    setEditingBillingParty(party);
    setBillingPartyForm({
      name: party.name || '',
      registration_no: party.registration_no || '',
      address_line1: party.address_line1 || '',
      address_line2: party.address_line2 || '',
      city: party.city || '',
      postcode: party.postcode || '',
      state: party.state || '',
      country: party.country || 'Malaysia',
      phone: party.phone || '',
      email: party.email || '',
      contact_person: party.contact_person || ''
    });
    setShowBillingPartyModal(true);
  };

  // Social Media Handlers
  const handleSaveSocialMedia = async () => {
    if (!socialMediaForm.platform.trim() || !socialMediaForm.url.trim()) {
      toast.error('Platform and URL are required');
      return;
    }
    
    let updatedLinks = [...socialMediaLinks];
    if (editingSocialMedia !== null) {
      updatedLinks[editingSocialMedia] = socialMediaForm;
    } else {
      updatedLinks.push(socialMediaForm);
    }
    
    try {
      await axiosInstance.put('/finance/company-settings', {
        ...companySettings,
        social_media_links: updatedLinks
      });
      setSocialMediaLinks(updatedLinks);
      setShowSocialMediaModal(false);
      setEditingSocialMedia(null);
      toast.success('Social media link saved');
    } catch (error) {
      toast.error('Failed to save social media link');
    }
  };

  const handleDeleteSocialMedia = async (index) => {
    if (!confirm('Delete this social media link?')) return;
    const updatedLinks = socialMediaLinks.filter((_, i) => i !== index);
    try {
      await axiosInstance.put('/finance/company-settings', {
        ...companySettings,
        social_media_links: updatedLinks
      });
      setSocialMediaLinks(updatedLinks);
      toast.success('Social media link deleted');
    } catch (error) {
      toast.error('Failed to delete social media link');
    }
  };

  // Custom Field Handlers
  const addCustomField = (docType) => {
    const fieldKey = `${docType}_custom_fields`;
    const currentFields = companySettings[fieldKey] || [];
    setCompanySettings({
      ...companySettings,
      [fieldKey]: [...currentFields, { label: '', type: 'text', position: 'header' }]
    });
  };

  const updateCustomField = (docType, index, field, value) => {
    const fieldKey = `${docType}_custom_fields`;
    const currentFields = [...(companySettings[fieldKey] || [])];
    currentFields[index] = { ...currentFields[index], [field]: value };
    setCompanySettings({ ...companySettings, [fieldKey]: currentFields });
  };

  const removeCustomField = (docType, index) => {
    const fieldKey = `${docType}_custom_fields`;
    const currentFields = (companySettings[fieldKey] || []).filter((_, i) => i !== index);
    setCompanySettings({ ...companySettings, [fieldKey]: currentFields });
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Company Settings
          </CardTitle>
          <CardDescription>
            Customize your company details for invoices and receipts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Company Info */}
          <div className="p-4 bg-blue-50 rounded-lg space-y-4">
            <h3 className="font-semibold text-blue-900">Company Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Company Name</Label>
                <Input
                  value={companySettings.company_name}
                  onChange={(e) => setCompanySettings({...companySettings, company_name: e.target.value})}
                />
              </div>
              <div>
                <Label>Registration No.</Label>
                <Input
                  value={companySettings.company_reg_no}
                  onChange={(e) => setCompanySettings({...companySettings, company_reg_no: e.target.value})}
                  placeholder="e.g., 1234567-A"
                />
              </div>
              <div>
                <Label>Address Line 1</Label>
                <Input
                  value={companySettings.address_line1}
                  onChange={(e) => setCompanySettings({...companySettings, address_line1: e.target.value})}
                />
              </div>
              <div>
                <Label>Address Line 2</Label>
                <Input
                  value={companySettings.address_line2}
                  onChange={(e) => setCompanySettings({...companySettings, address_line2: e.target.value})}
                />
              </div>
              <div>
                <Label>City</Label>
                <Input
                  value={companySettings.city}
                  onChange={(e) => setCompanySettings({...companySettings, city: e.target.value})}
                />
              </div>
              <div>
                <Label>Postcode</Label>
                <Input
                  value={companySettings.postcode}
                  onChange={(e) => setCompanySettings({...companySettings, postcode: e.target.value})}
                />
              </div>
              <div>
                <Label>State</Label>
                <Input
                  value={companySettings.state}
                  onChange={(e) => setCompanySettings({...companySettings, state: e.target.value})}
                />
              </div>
              <div>
                <Label>Phone</Label>
                <Input
                  value={companySettings.phone}
                  onChange={(e) => setCompanySettings({...companySettings, phone: e.target.value})}
                />
              </div>
              <div>
                <Label>Email</Label>
                <Input
                  value={companySettings.email}
                  onChange={(e) => setCompanySettings({...companySettings, email: e.target.value})}
                />
              </div>
              <div>
                <Label>Website</Label>
                <Input
                  value={companySettings.website}
                  onChange={(e) => setCompanySettings({...companySettings, website: e.target.value})}
                />
              </div>
            </div>
          </div>

          {/* Company Logo Upload */}
          <div className="p-4 bg-purple-50 rounded-lg space-y-4">
            <h3 className="font-semibold text-purple-900">Company Logo</h3>
            <p className="text-sm text-purple-700">
              Upload your company logo. This will appear on Invoices, Pay Slips, Pay Advice, and other documents.
            </p>
            <div className="flex flex-col gap-4">
              {companySettings.logo_url && (
                <div className="flex items-center gap-4 p-4 bg-white rounded border">
                  <img 
                    src={`${process.env.REACT_APP_BACKEND_URL}${companySettings.logo_url}`}
                    alt="Company Logo"
                    className="h-16 max-w-[200px] object-contain border rounded"
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                  <div className="flex-1">
                    <p className="font-medium">Current Logo</p>
                    <p className="text-sm text-gray-500">{companySettings.logo_filename || 'logo.png'}</p>
                  </div>
                </div>
              )}
              <div>
                <Label>Upload New Logo</Label>
                <input 
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
                  onChange={async (e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    try {
                      toast.info('Uploading logo...');
                      const response = await axiosInstance.post('/finance/company-settings/upload-logo', formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                      });
                      setCompanySettings({
                        ...companySettings, 
                        logo_url: response.data.url,
                        logo_filename: response.data.filename
                      });
                      toast.success('Logo uploaded successfully');
                      e.target.value = '';
                    } catch (error) {
                      toast.error(error.response?.data?.detail || 'Failed to upload logo');
                    }
                  }}
                  className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                />
                <p className="text-xs text-gray-500 mt-1">Recommended: PNG or JPG, max 2MB, transparent background for best results</p>
              </div>
            </div>
          </div>

          {/* Billing Parties / Vendors */}
          <div className="p-4 bg-amber-50 rounded-lg space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-semibold text-amber-900">Billing Parties / Vendors</h3>
                <p className="text-sm text-amber-700">Manage alternative billing entities (e.g., HRDC, sponsors) for invoicing</p>
              </div>
              <Button 
                size="sm" 
                onClick={() => {
                  setEditingBillingParty(null);
                  setBillingPartyForm({
                    name: '', registration_no: '', address_line1: '', address_line2: '',
                    city: '', postcode: '', state: '', country: 'Malaysia', phone: '', email: '', contact_person: ''
                  });
                  setShowBillingPartyModal(true);
                }}
                data-testid="add-billing-party-btn"
              >
                <Plus className="w-4 h-4 mr-1" /> Add Billing Party
              </Button>
            </div>
            
            {billingParties.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">No billing parties added yet. Add one to use as an alternative "Bill To" on invoices.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {billingParties.map((party) => (
                  <div key={party.id} className="bg-white p-3 rounded border border-amber-200 flex justify-between items-start" data-testid={`billing-party-${party.id}`}>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{party.name}</p>
                      {party.registration_no && <p className="text-xs text-gray-500">Reg: {party.registration_no}</p>}
                      {party.address_line1 && <p className="text-xs text-gray-500 truncate">{party.address_line1}</p>}
                      {party.contact_person && <p className="text-xs text-gray-400">Contact: {party.contact_person}</p>}
                    </div>
                    <div className="flex gap-1 ml-2">
                      <Button variant="ghost" size="sm" onClick={() => openEditBillingParty(party)} data-testid={`edit-billing-party-${party.id}`}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-600 hover:text-red-700 hover:bg-red-50" 
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleDeleteBillingParty(party.id);
                        }} 
                        data-testid={`delete-billing-party-${party.id}`}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Social Media Links */}
          <div className="p-4 bg-pink-50 rounded-lg space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-semibold text-pink-900">Social Media Links</h3>
                <p className="text-sm text-pink-700">Add your social media pages for participants to follow</p>
              </div>
              <Button 
                size="sm" 
                onClick={() => {
                  setEditingSocialMedia(null);
                  setSocialMediaForm({ platform: '', url: '', icon: 'globe', is_active: true });
                  setShowSocialMediaModal(true);
                }}
                data-testid="add-social-media-btn"
              >
                <Plus className="w-4 h-4 mr-1" /> Add Social Media
              </Button>
            </div>
            
            {socialMediaLinks.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">No social media links added yet.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {socialMediaLinks.map((link, index) => (
                  <div key={index} className={`bg-white p-3 rounded border ${link.is_active ? 'border-pink-200' : 'border-gray-200 opacity-50'} flex justify-between items-center`}>
                    <div className="flex items-center gap-2">
                      <span className="text-xl">
                        {link.icon === 'facebook' ? <FaFacebook className="text-[#1877F2]" /> : 
                         link.icon === 'instagram' ? <FaInstagram className="text-[#E4405F]" /> : 
                         link.icon === 'tiktok' ? <FaTiktok className="text-black" /> : 
                         link.icon === 'youtube' ? <FaYoutube className="text-[#FF0000]" /> : 
                         link.icon === 'twitter' ? <FaTwitter className="text-[#1DA1F2]" /> : 
                         link.icon === 'linkedin' ? <FaLinkedin className="text-[#0A66C2]" /> : <Globe className="text-gray-500" />}
                      </span>
                      <div>
                        <p className="font-medium text-sm">{link.platform}</p>
                        <p className="text-xs text-gray-500 truncate max-w-[150px]">{link.url}</p>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => {
                        setEditingSocialMedia(index);
                        setSocialMediaForm(link);
                        setShowSocialMediaModal(true);
                      }}>
                        <Edit className="w-3 h-3" />
                      </Button>
                      <Button variant="ghost" size="sm" className="text-red-600" onClick={() => handleDeleteSocialMedia(index)}>
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Bank Details */}
          <div className="p-4 bg-green-50 rounded-lg space-y-4">
            <h3 className="font-semibold text-green-900">Bank Details (for invoices)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Bank Name</Label>
                <Input
                  value={companySettings.bank_name}
                  onChange={(e) => setCompanySettings({...companySettings, bank_name: e.target.value})}
                  placeholder="e.g., Maybank"
                />
              </div>
              <div>
                <Label>Account Name</Label>
                <Input
                  value={companySettings.bank_account_name}
                  onChange={(e) => setCompanySettings({...companySettings, bank_account_name: e.target.value})}
                />
              </div>
              <div>
                <Label>Account Number</Label>
                <Input
                  value={companySettings.bank_account_number}
                  onChange={(e) => setCompanySettings({...companySettings, bank_account_number: e.target.value})}
                />
              </div>
            </div>
          </div>

          {/* Invoice Settings */}
          <div className="p-4 bg-purple-50 rounded-lg space-y-4">
            <h3 className="font-semibold text-purple-900">Invoice Settings</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Payment Terms</Label>
                <Input
                  value={companySettings.invoice_terms}
                  onChange={(e) => setCompanySettings({...companySettings, invoice_terms: e.target.value})}
                />
              </div>
              <div>
                <Label>Footer Note</Label>
                <Input
                  value={companySettings.invoice_footer_note}
                  onChange={(e) => setCompanySettings({...companySettings, invoice_footer_note: e.target.value})}
                />
              </div>
              <div className="md:col-span-2">
                <Label>Logo URL (optional)</Label>
                <Input
                  value={companySettings.logo_url || ''}
                  onChange={(e) => setCompanySettings({...companySettings, logo_url: e.target.value})}
                  placeholder="https://your-logo-url.com/logo.png"
                />
              </div>
            </div>
          </div>

          {/* Document Styling Settings */}
          <div className="p-4 bg-orange-50 rounded-lg space-y-4">
            <h3 className="font-semibold text-orange-900">📄 Document Styling (Invoice, Payslip, Pay Advice)</h3>
            <p className="text-sm text-orange-700">Customize the look of all printed documents</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Logo Settings */}
              <div>
                <Label>Logo Width (px)</Label>
                <Input
                  type="number"
                  min="50"
                  max="300"
                  value={companySettings.logo_width || 150}
                  onChange={(e) => setCompanySettings({...companySettings, logo_width: parseInt(e.target.value) || 150})}
                />
                <p className="text-xs text-gray-500 mt-1">Default: 150px. Max: 300px</p>
              </div>
              <div>
                <Label>Logo Position</Label>
                <Select 
                  value={companySettings.logo_position || 'center'} 
                  onValueChange={(v) => setCompanySettings({...companySettings, logo_position: v})}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="left">Left</SelectItem>
                    <SelectItem value="center">Center</SelectItem>
                    <SelectItem value="right">Right</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="show_watermark"
                  checked={companySettings.show_watermark !== false}
                  onChange={(e) => setCompanySettings({...companySettings, show_watermark: e.target.checked})}
                  className="h-4 w-4"
                />
                <Label htmlFor="show_watermark" className="cursor-pointer">Show Logo Watermark</Label>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Colors */}
              <div>
                <Label>Primary Color (Headers)</Label>
                <div className="flex gap-2">
                  <Input
                    type="color"
                    value={companySettings.primary_color || '#1a365d'}
                    onChange={(e) => setCompanySettings({...companySettings, primary_color: e.target.value})}
                    className="w-12 h-10 p-1 cursor-pointer"
                  />
                  <Input
                    value={companySettings.primary_color || '#1a365d'}
                    onChange={(e) => setCompanySettings({...companySettings, primary_color: e.target.value})}
                    className="flex-1"
                  />
                </div>
              </div>
              <div>
                <Label>Secondary Color (Accents)</Label>
                <div className="flex gap-2">
                  <Input
                    type="color"
                    value={companySettings.secondary_color || '#4472C4'}
                    onChange={(e) => setCompanySettings({...companySettings, secondary_color: e.target.value})}
                    className="w-12 h-10 p-1 cursor-pointer"
                  />
                  <Input
                    value={companySettings.secondary_color || '#4472C4'}
                    onChange={(e) => setCompanySettings({...companySettings, secondary_color: e.target.value})}
                    className="flex-1"
                  />
                </div>
              </div>
              <div>
                <Label>Watermark Opacity</Label>
                <Input
                  type="range"
                  min="0.02"
                  max="0.2"
                  step="0.01"
                  value={companySettings.watermark_opacity || 0.08}
                  onChange={(e) => setCompanySettings({...companySettings, watermark_opacity: parseFloat(e.target.value)})}
                  className="mt-2"
                />
                <p className="text-xs text-gray-500">{((companySettings.watermark_opacity || 0.08) * 100).toFixed(0)}% opacity</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Fonts */}
              <div>
                <Label>Header Font</Label>
                <Select 
                  value={companySettings.header_font || 'Arial'} 
                  onValueChange={(v) => setCompanySettings({...companySettings, header_font: v})}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Arial">Arial</SelectItem>
                    <SelectItem value="Helvetica">Helvetica</SelectItem>
                    <SelectItem value="Times New Roman">Times New Roman</SelectItem>
                    <SelectItem value="Georgia">Georgia</SelectItem>
                    <SelectItem value="Verdana">Verdana</SelectItem>
                    <SelectItem value="Tahoma">Tahoma</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Body Font</Label>
                <Select 
                  value={companySettings.body_font || 'Arial'} 
                  onValueChange={(v) => setCompanySettings({...companySettings, body_font: v})}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Arial">Arial</SelectItem>
                    <SelectItem value="Helvetica">Helvetica</SelectItem>
                    <SelectItem value="Times New Roman">Times New Roman</SelectItem>
                    <SelectItem value="Georgia">Georgia</SelectItem>
                    <SelectItem value="Verdana">Verdana</SelectItem>
                    <SelectItem value="Tahoma">Tahoma</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Tagline */}
            <div className="border-t pt-4">
              <h4 className="font-medium mb-2">Footer Tagline</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-1">
                  <Label>Tagline Text</Label>
                  <Input
                    value={companySettings.tagline || 'Towards a Nation of Safe Drivers'}
                    onChange={(e) => setCompanySettings({...companySettings, tagline: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Tagline Font</Label>
                  <Select 
                    value={companySettings.tagline_font || 'Georgia'} 
                    onValueChange={(v) => setCompanySettings({...companySettings, tagline_font: v})}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Georgia">Georgia (Elegant)</SelectItem>
                      <SelectItem value="Times New Roman">Times New Roman</SelectItem>
                      <SelectItem value="Palatino">Palatino</SelectItem>
                      <SelectItem value="Garamond">Garamond</SelectItem>
                      <SelectItem value="Arial">Arial</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Tagline Style</Label>
                  <Select 
                    value={companySettings.tagline_style || 'italic'} 
                    onValueChange={(v) => setCompanySettings({...companySettings, tagline_style: v})}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="italic">Italic</SelectItem>
                      <SelectItem value="bold">Bold</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {/* Preview */}
              <div className="mt-3 p-3 bg-white border rounded text-center">
                <p className="text-xs text-gray-500 mb-1">Preview:</p>
                <p style={{
                  fontFamily: companySettings.tagline_font || 'Georgia',
                  fontStyle: companySettings.tagline_style === 'italic' ? 'italic' : 'normal',
                  fontWeight: companySettings.tagline_style === 'bold' ? 'bold' : 'normal',
                  color: companySettings.primary_color || '#1a365d',
                  fontSize: '14px'
                }}>
                  "{companySettings.tagline || 'Towards a Nation of Safe Drivers'}"
                </p>
              </div>
            </div>
          </div>

          {/* Custom Fields for Documents */}
          <div className="p-4 bg-indigo-50 rounded-lg space-y-4">
            <h3 className="font-semibold text-indigo-900">🔧 Custom Fields (Add to Documents)</h3>
            <p className="text-sm text-indigo-700">Add extra fields to any document type without coding. These will appear in the respective documents.</p>
            
            <Tabs defaultValue="invoice_fields" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="invoice_fields">Invoice</TabsTrigger>
                <TabsTrigger value="indemnity_fields">Indemnity</TabsTrigger>
                <TabsTrigger value="payslip_fields">Payslip</TabsTrigger>
                <TabsTrigger value="payadvice_fields">Pay Advice</TabsTrigger>
              </TabsList>
              
              {/* Invoice Custom Fields */}
              <TabsContent value="invoice_fields" className="mt-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <Label>Invoice Custom Fields</Label>
                    <Button size="sm" variant="outline" onClick={() => addCustomField('invoice')}>
                      <Plus className="w-3 h-3 mr-1" /> Add Field
                    </Button>
                  </div>
                  {(companySettings.invoice_custom_fields || []).length === 0 ? (
                    <p className="text-sm text-gray-500">No custom fields. Add one to show extra info on invoices.</p>
                  ) : (
                    <div className="space-y-2">
                      {(companySettings.invoice_custom_fields || []).map((field, idx) => (
                        <div key={idx} className="flex gap-2 items-center bg-white p-2 rounded border">
                          <Input
                            value={field.label}
                            onChange={(e) => updateCustomField('invoice', idx, 'label', e.target.value)}
                            placeholder="Field Label"
                            className="flex-1"
                          />
                          <Select value={field.position || 'header'} onValueChange={(v) => updateCustomField('invoice', idx, 'position', v)}>
                            <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="header">Header</SelectItem>
                              <SelectItem value="footer">Footer</SelectItem>
                            </SelectContent>
                          </Select>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => removeCustomField('invoice', idx)}>
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Indemnity Custom Fields */}
              <TabsContent value="indemnity_fields" className="mt-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <Label>Indemnity Form Custom Fields</Label>
                    <Button size="sm" variant="outline" onClick={() => addCustomField('indemnity')}>
                      <Plus className="w-3 h-3 mr-1" /> Add Field
                    </Button>
                  </div>
                  {(companySettings.indemnity_custom_fields || []).length === 0 ? (
                    <p className="text-sm text-gray-500">No custom fields for indemnity forms.</p>
                  ) : (
                    <div className="space-y-2">
                      {(companySettings.indemnity_custom_fields || []).map((field, idx) => (
                        <div key={idx} className="flex gap-2 items-center bg-white p-2 rounded border">
                          <Input
                            value={field.label}
                            onChange={(e) => updateCustomField('indemnity', idx, 'label', e.target.value)}
                            placeholder="Field Label"
                            className="flex-1"
                          />
                          <Select value={field.type || 'text'} onValueChange={(v) => updateCustomField('indemnity', idx, 'type', v)}>
                            <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="text">Text</SelectItem>
                              <SelectItem value="checkbox">Checkbox</SelectItem>
                            </SelectContent>
                          </Select>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => removeCustomField('indemnity', idx)}>
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Payslip Custom Fields */}
              <TabsContent value="payslip_fields" className="mt-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <Label>Payslip Custom Fields (Earnings/Deductions)</Label>
                    <Button size="sm" variant="outline" onClick={() => addCustomField('payslip')}>
                      <Plus className="w-3 h-3 mr-1" /> Add Field
                    </Button>
                  </div>
                  {(companySettings.payslip_custom_fields || []).length === 0 ? (
                    <p className="text-sm text-gray-500">No custom earnings/deductions for payslips.</p>
                  ) : (
                    <div className="space-y-2">
                      {(companySettings.payslip_custom_fields || []).map((field, idx) => (
                        <div key={idx} className="flex gap-2 items-center bg-white p-2 rounded border">
                          <Input
                            value={field.label}
                            onChange={(e) => updateCustomField('payslip', idx, 'label', e.target.value)}
                            placeholder="Field Label (e.g., Transport Allowance)"
                            className="flex-1"
                          />
                          <Select value={field.type || 'earning'} onValueChange={(v) => updateCustomField('payslip', idx, 'type', v)}>
                            <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="earning">Earning</SelectItem>
                              <SelectItem value="deduction">Deduction</SelectItem>
                            </SelectContent>
                          </Select>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => removeCustomField('payslip', idx)}>
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Pay Advice Custom Fields */}
              <TabsContent value="payadvice_fields" className="mt-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <Label>Pay Advice Custom Fields</Label>
                    <Button size="sm" variant="outline" onClick={() => addCustomField('payadvice')}>
                      <Plus className="w-3 h-3 mr-1" /> Add Field
                    </Button>
                  </div>
                  {(companySettings.payadvice_custom_fields || []).length === 0 ? (
                    <p className="text-sm text-gray-500">No custom fields for pay advice.</p>
                  ) : (
                    <div className="space-y-2">
                      {(companySettings.payadvice_custom_fields || []).map((field, idx) => (
                        <div key={idx} className="flex gap-2 items-center bg-white p-2 rounded border">
                          <Input
                            value={field.label}
                            onChange={(e) => updateCustomField('payadvice', idx, 'label', e.target.value)}
                            placeholder="Field Label"
                            className="flex-1"
                          />
                          <Select value={field.position || 'header'} onValueChange={(v) => updateCustomField('payadvice', idx, 'position', v)}>
                            <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="header">Header</SelectItem>
                              <SelectItem value="footer">Footer</SelectItem>
                            </SelectContent>
                          </Select>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => removeCustomField('payadvice', idx)}>
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* Indemnity Form Upload */}
          <div className="p-4 bg-orange-50 rounded-lg space-y-4">
            <h3 className="font-semibold text-orange-900">Custom Indemnity Form</h3>
            <p className="text-sm text-orange-700">
              Upload your custom indemnity form (PDF, DOC, or DOCX). This will be shown to participants for signing.
            </p>
            <div className="flex flex-col gap-4">
              {companySettings.indemnity_form_url && (
                <div className="flex items-center gap-3 p-3 bg-white rounded border">
                  <FileText className="w-8 h-8 text-orange-600" />
                  <div className="flex-1">
                    <p className="font-medium">{companySettings.indemnity_form_filename || 'Current Form'}</p>
                    <a 
                      href={`${process.env.REACT_APP_BACKEND_URL}${companySettings.indemnity_form_url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      View / Download
                    </a>
                  </div>
                </div>
              )}
              <div>
                <Label>Upload New Indemnity Form</Label>
                <input 
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={async (e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    try {
                      toast.info('Uploading indemnity form...');
                      const response = await axiosInstance.post('/finance/company-settings/upload-indemnity-form', formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                      });
                      setCompanySettings({
                        ...companySettings, 
                        indemnity_form_url: response.data.url,
                        indemnity_form_filename: response.data.filename
                      });
                      toast.success('Indemnity form uploaded successfully');
                      e.target.value = '';
                    } catch (error) {
                      toast.error(error.response?.data?.detail || 'Failed to upload indemnity form');
                    }
                  }}
                  className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-orange-50 file:text-orange-700 hover:file:bg-orange-100"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <Button onClick={handleSaveSettings} disabled={settingsLoading}>
              {settingsLoading ? 'Saving...' : 'Save Settings'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Billing Party Modal */}
      <Dialog open={showBillingPartyModal} onOpenChange={setShowBillingPartyModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingBillingParty ? 'Edit Billing Party' : 'Add New Billing Party'}</DialogTitle>
            <DialogDescription>
              Billing parties can be selected as alternative "Bill To" addresses on invoices
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Party Name *</Label>
                <Input
                  value={billingPartyForm.name}
                  onChange={(e) => setBillingPartyForm({...billingPartyForm, name: e.target.value})}
                  placeholder="e.g., HRD Corp"
                  data-testid="billing-party-name"
                />
              </div>
              <div>
                <Label>Registration No.</Label>
                <Input
                  value={billingPartyForm.registration_no}
                  onChange={(e) => setBillingPartyForm({...billingPartyForm, registration_no: e.target.value})}
                  placeholder="e.g., 1234567-X"
                  data-testid="billing-party-regno"
                />
              </div>
              <div>
                <Label>Contact Person</Label>
                <Input
                  value={billingPartyForm.contact_person}
                  onChange={(e) => setBillingPartyForm({...billingPartyForm, contact_person: e.target.value})}
                  placeholder="Contact name"
                  data-testid="billing-party-contact"
                />
              </div>
            </div>
            
            <div className="border-t pt-4 space-y-4">
              <h4 className="font-medium">Address</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>Address Line 1</Label>
                  <Input
                    value={billingPartyForm.address_line1}
                    onChange={(e) => setBillingPartyForm({...billingPartyForm, address_line1: e.target.value})}
                    placeholder="Street address"
                    data-testid="billing-party-addr1"
                  />
                </div>
                <div className="col-span-2">
                  <Label>Address Line 2</Label>
                  <Input
                    value={billingPartyForm.address_line2}
                    onChange={(e) => setBillingPartyForm({...billingPartyForm, address_line2: e.target.value})}
                    placeholder="Building, suite, etc."
                    data-testid="billing-party-addr2"
                  />
                </div>
                <div>
                  <Label>City</Label>
                  <Input
                    value={billingPartyForm.city}
                    onChange={(e) => setBillingPartyForm({...billingPartyForm, city: e.target.value})}
                    data-testid="billing-party-city"
                  />
                </div>
                <div>
                  <Label>Postcode</Label>
                  <Input
                    value={billingPartyForm.postcode}
                    onChange={(e) => setBillingPartyForm({...billingPartyForm, postcode: e.target.value})}
                    data-testid="billing-party-postcode"
                  />
                </div>
                <div>
                  <Label>State</Label>
                  <Input
                    value={billingPartyForm.state}
                    onChange={(e) => setBillingPartyForm({...billingPartyForm, state: e.target.value})}
                    data-testid="billing-party-state"
                  />
                </div>
                <div>
                  <Label>Country</Label>
                  <Input
                    value={billingPartyForm.country}
                    onChange={(e) => setBillingPartyForm({...billingPartyForm, country: e.target.value})}
                    data-testid="billing-party-country"
                  />
                </div>
                <div>
                  <Label>Phone</Label>
                  <Input
                    value={billingPartyForm.phone}
                    onChange={(e) => setBillingPartyForm({...billingPartyForm, phone: e.target.value})}
                    placeholder="+60-xxx-xxx-xxxx"
                    data-testid="billing-party-phone"
                  />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={billingPartyForm.email}
                    onChange={(e) => setBillingPartyForm({...billingPartyForm, email: e.target.value})}
                    placeholder="email@example.com"
                    data-testid="billing-party-email"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowBillingPartyModal(false)}>
                Cancel
              </Button>
              <Button onClick={handleBillingPartySubmit} data-testid="save-billing-party-btn">
                {editingBillingParty ? 'Update' : 'Create'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Social Media Modal */}
      <Dialog open={showSocialMediaModal} onOpenChange={setShowSocialMediaModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingSocialMedia !== null ? 'Edit Social Media Link' : 'Add Social Media Link'}</DialogTitle>
            <DialogDescription>Add your social media page for participants to follow</DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <Label>Platform Name *</Label>
              <Input
                value={socialMediaForm.platform}
                onChange={(e) => setSocialMediaForm({...socialMediaForm, platform: e.target.value})}
                placeholder="e.g., Facebook, Instagram, TikTok"
              />
            </div>
            <div>
              <Label>URL *</Label>
              <Input
                value={socialMediaForm.url}
                onChange={(e) => setSocialMediaForm({...socialMediaForm, url: e.target.value})}
                placeholder="https://facebook.com/yourpage"
              />
            </div>
            <div>
              <Label>Icon</Label>
              <Select value={socialMediaForm.icon} onValueChange={(v) => setSocialMediaForm({...socialMediaForm, icon: v})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="facebook"><span className="flex items-center gap-2"><FaFacebook className="text-[#1877F2]" /> Facebook</span></SelectItem>
                  <SelectItem value="instagram"><span className="flex items-center gap-2"><FaInstagram className="text-[#E4405F]" /> Instagram</span></SelectItem>
                  <SelectItem value="tiktok"><span className="flex items-center gap-2"><FaTiktok /> TikTok</span></SelectItem>
                  <SelectItem value="youtube"><span className="flex items-center gap-2"><FaYoutube className="text-[#FF0000]" /> YouTube</span></SelectItem>
                  <SelectItem value="twitter"><span className="flex items-center gap-2"><FaTwitter className="text-[#1DA1F2]" /> Twitter/X</span></SelectItem>
                  <SelectItem value="linkedin"><span className="flex items-center gap-2"><FaLinkedin className="text-[#0A66C2]" /> LinkedIn</span></SelectItem>
                  <SelectItem value="globe"><span className="flex items-center gap-2"><Globe className="w-4 h-4" /> Other</span></SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="social-active"
                checked={socialMediaForm.is_active}
                onChange={(e) => setSocialMediaForm({...socialMediaForm, is_active: e.target.checked})}
                className="rounded"
              />
              <Label htmlFor="social-active">Active (visible to participants)</Label>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowSocialMediaModal(false)}>Cancel</Button>
            <Button onClick={handleSaveSocialMedia}>{editingSocialMedia !== null ? 'Update' : 'Add'}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export { SettingsTab };
