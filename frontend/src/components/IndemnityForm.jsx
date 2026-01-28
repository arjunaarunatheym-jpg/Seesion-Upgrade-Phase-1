import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { Shield, AlertTriangle, Car, CheckCircle, UserCheck, ChevronRight, ChevronLeft, FileText, Lock } from "lucide-react";
import { axiosInstance } from "../App";

const IndemnityForm = ({ 
  open, 
  onAccept, 
  participant,
  trainingSession,
  companySettings
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [customSections, setCustomSections] = useState([]);
  
  // Section acceptance state
  const [acceptedSections, setAcceptedSections] = useState({});
  
  // Signature data
  const [signatureData, setSignatureData] = useState({
    signed_name: participant?.full_name || '',
    signed_ic: participant?.id_number || '',
    signed_date: new Date().toISOString().split('T')[0]
  });

  // Default sections (can be overridden by admin)
  const defaultSections = [
    {
      id: 'section_a',
      title: 'SECTION A – ACKNOWLEDGEMENT OF RISK',
      title_bm: 'SEKSYEN A – PENGAKUAN RISIKO',
      color: 'red',
      content_en: 'I acknowledge that Defensive Driving and/or Defensive Riding training includes theoretical and practical activities which involve inherent risks. I voluntarily participate in this training and accept all associated risks.',
      content_bm: 'Saya mengakui bahawa latihan Pemanduan Defensif dan/atau Penunggang Defensif merangkumi aktiviti teori dan praktikal yang melibatkan risiko yang wujud. Saya secara sukarela menyertai latihan ini dan menerima semua risiko yang berkaitan.'
    },
    {
      id: 'section_b',
      title: 'SECTION B – VEHICLE RESPONSIBILITY',
      title_bm: 'SEKSYEN B – TANGGUNGJAWAB KENDERAAN',
      color: 'orange',
      content_en: 'I confirm that the vehicle used during training is in good and roadworthy condition. I assume full responsibility for my vehicle and its condition throughout the training duration.',
      content_bm: 'Saya mengesahkan bahawa kenderaan yang digunakan semasa latihan adalah dalam keadaan baik dan selamat untuk dipandu. Saya menanggung tanggungjawab penuh terhadap kenderaan saya dan keadaannya sepanjang tempoh latihan.'
    },
    {
      id: 'section_c',
      title: 'SECTION C – TRAINER AUTHORITY',
      title_bm: 'SEKSYEN C – KUASA JURULATIH',
      color: 'blue',
      content_en: 'I agree to follow all instructions given by the trainer/facilitator. I understand that the trainer has the right to stop my participation if my conduct poses a safety risk.',
      content_bm: 'Saya bersetuju untuk mengikuti semua arahan yang diberikan oleh jurulatih/fasilitator. Saya faham bahawa jurulatih mempunyai hak untuk menghentikan penyertaan saya jika kelakuan saya menimbulkan risiko keselamatan.'
    },
    {
      id: 'section_d',
      title: 'SECTION D – COMPLIANCE & CONDUCT',
      title_bm: 'SEKSYEN D – PEMATUHAN & TINGKAH LAKU',
      color: 'purple',
      content_en: 'I agree to comply with all safety rules and regulations during the training. I will conduct myself professionally and not engage in any reckless or dangerous behavior.',
      content_bm: 'Saya bersetuju untuk mematuhi semua peraturan dan peraturan keselamatan semasa latihan. Saya akan berkelakuan secara profesional dan tidak akan terlibat dalam sebarang tingkah laku melulu atau berbahaya.'
    },
    {
      id: 'section_e',
      title: 'SECTION E – INDEMNITY',
      title_bm: 'SEKSYEN E – INDEMNITI',
      color: 'red',
      content_en: 'I hereby release, indemnify and hold harmless the training provider, its employees, agents, and representatives from any claims, damages, or liabilities arising from my participation in this training.',
      content_bm: 'Dengan ini saya melepaskan, mengindemniti dan tidak mempertanggungjawabkan penyedia latihan, pekerja, ejen, dan wakilnya daripada sebarang tuntutan, kerosakan, atau liabiliti yang timbul daripada penyertaan saya dalam latihan ini.'
    },
    {
      id: 'section_f',
      title: 'SECTION F – FINAL DECLARATION',
      title_bm: 'SEKSYEN F – PENGISYTIHARAN AKHIR',
      color: 'green',
      content_en: 'I declare that all information provided is true and accurate. I have read and understood all sections of this indemnity form and agree to be bound by its terms.',
      content_bm: 'Saya mengisytiharkan bahawa semua maklumat yang diberikan adalah benar dan tepat. Saya telah membaca dan memahami semua bahagian borang indemniti ini dan bersetuju untuk terikat dengan syarat-syaratnya.'
    }
  ];

  // Load custom sections from settings
  useEffect(() => {
    const loadCustomSections = async () => {
      try {
        const response = await axiosInstance.get('/settings/indemnity-sections');
        if (response.data && response.data.length > 0) {
          setCustomSections(response.data);
        }
      } catch (error) {
        // Use default sections if custom not available
        console.log('Using default indemnity sections');
      }
    };
    if (open) {
      loadCustomSections();
    }
  }, [open]);

  // Get active sections (custom or default)
  const sections = customSections.length > 0 ? customSections : defaultSections;
  
  // Total steps = intro + sections + signature
  const totalSteps = sections.length + 2;

  // Pre-fill signature data from participant
  useEffect(() => {
    if (participant) {
      setSignatureData(prev => ({
        ...prev,
        signed_name: participant.full_name || '',
        signed_ic: participant.id_number || ''
      }));
    }
  }, [participant]);

  // Reset on open
  useEffect(() => {
    if (open) {
      setCurrentStep(0);
      setAcceptedSections({});
    }
  }, [open]);

  const handleAcceptSection = (sectionId) => {
    setAcceptedSections(prev => ({ ...prev, [sectionId]: true }));
    if (currentStep < totalSteps - 1) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handleSubmit = async () => {
    if (!signatureData.signed_name.trim() || !signatureData.signed_ic.trim()) {
      toast.error("Please enter your name and IC number");
      return;
    }
    
    setIsSubmitting(true);
    try {
      await onAccept({
        ...signatureData,
        sections_accepted: acceptedSections,
        training_id: trainingSession?.id || null,
        trainer_name: trainingSession?.trainer_name || null,
        vehicle_reg: participant?.vehicle_reg || null
      });
    } catch (error) {
      toast.error("Failed to submit indemnity form");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getColorClasses = (color) => {
    const colors = {
      red: { bg: 'bg-red-600', light: 'bg-red-50', border: 'border-red-500' },
      orange: { bg: 'bg-orange-600', light: 'bg-orange-50', border: 'border-orange-500' },
      blue: { bg: 'bg-blue-600', light: 'bg-blue-50', border: 'border-blue-500' },
      purple: { bg: 'bg-purple-600', light: 'bg-purple-50', border: 'border-purple-500' },
      green: { bg: 'bg-green-600', light: 'bg-green-50', border: 'border-green-500' },
    };
    return colors[color] || colors.blue;
  };

  // Render intro step
  const renderIntro = () => (
    <div className="space-y-4">
      {/* Participant Info */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <h3 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
          <UserCheck className="w-5 h-5" />
          Participant Information
        </h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-gray-600">Name:</span> <strong>{participant?.full_name || '-'}</strong></div>
          <div><span className="text-gray-600">IC:</span> <strong>{participant?.id_number || '-'}</strong></div>
          <div><span className="text-gray-600">Phone:</span> <strong>{participant?.contact_phone || participant?.phone_number || '-'}</strong></div>
          <div><span className="text-gray-600">Email:</span> <strong>{participant?.contact_email || participant?.email || '-'}</strong></div>
        </div>
      </div>

      {/* Training Info */}
      {trainingSession && (
        <div className="bg-green-50 p-4 rounded-lg border border-green-200">
          <h3 className="font-semibold text-green-900 mb-3 flex items-center gap-2">
            <Car className="w-5 h-5" />
            Training Session
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-gray-600">Programme:</span> <strong>{trainingSession.name || '-'}</strong></div>
            <div><span className="text-gray-600">Date:</span> <strong>{trainingSession.start_date || '-'}</strong></div>
            <div className="col-span-2"><span className="text-gray-600">Location:</span> <strong>{trainingSession.venue || '-'}</strong></div>
          </div>
        </div>
      )}

      {/* Training Provider */}
      <div className="bg-gray-100 p-4 rounded-lg text-center">
        <p className="font-semibold text-gray-900">Training Provider:</p>
        <p className="text-gray-700">{companySettings?.company_name || 'MDDRC Sdn Bhd'}</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-amber-800">Important Notice</p>
            <p className="text-sm text-amber-700 mt-1">
              You will need to read and accept {sections.length} sections of this indemnity form. 
              Each section will be presented one at a time. Please read carefully before accepting.
            </p>
          </div>
        </div>
      </div>
    </div>
  );

  // Render section step
  const renderSection = (section, index) => {
    const colors = getColorClasses(section.color);
    const isAccepted = acceptedSections[section.id];
    
    return (
      <div className="space-y-4">
        {/* Progress */}
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>Section {index + 1} of {sections.length}</span>
          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-600 transition-all" 
              style={{ width: `${((index + 1) / sections.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Section Header */}
        <div className={`${colors.bg} text-white p-4 rounded-t-lg`}>
          <h3 className="font-bold text-lg">{section.title}</h3>
          {section.title_bm && <p className="text-sm opacity-90">{section.title_bm}</p>}
        </div>

        {/* Section Content */}
        <div className={`${colors.light} p-4 rounded-b-lg border-2 ${colors.border} border-t-0`}>
          <div className="space-y-4">
            <div className="bg-white p-4 rounded border-l-4 border-gray-400">
              <p className="text-sm mb-2">
                <strong>English:</strong> {section.content_en}
              </p>
            </div>
            {section.content_bm && (
              <div className="bg-white p-4 rounded border-l-4 border-gray-300">
                <p className="text-sm text-gray-700">
                  <strong>Bahasa Malaysia:</strong> {section.content_bm}
                </p>
              </div>
            )}
          </div>
        </div>

        {isAccepted ? (
          <div className="flex items-center gap-2 text-green-600 font-medium">
            <CheckCircle className="w-5 h-5" />
            Section Accepted
          </div>
        ) : (
          <div className="flex items-center space-x-3 p-3 bg-white rounded border">
            <Checkbox 
              id={`accept-${section.id}`}
              checked={false}
              onCheckedChange={() => handleAcceptSection(section.id)}
            />
            <label htmlFor={`accept-${section.id}`} className="text-sm font-medium cursor-pointer">
              I have read, understood and agree to this section
            </label>
          </div>
        )}
      </div>
    );
  };

  // Render signature step
  const renderSignature = () => {
    const allAccepted = sections.every(s => acceptedSections[s.id]);
    
    return (
      <div className="space-y-4">
        {/* Summary */}
        <div className="bg-green-50 p-4 rounded-lg border border-green-200">
          <h3 className="font-semibold text-green-900 mb-3 flex items-center gap-2">
            <CheckCircle className="w-5 h-5" />
            All Sections Accepted
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {sections.map((section, idx) => (
              <div key={section.id} className="flex items-center gap-2 text-sm">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span>Section {String.fromCharCode(65 + idx)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Signature */}
        <div className="bg-gray-50 p-4 rounded-lg border">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Lock className="w-5 h-5 text-blue-600" />
            Digital Signature / Tandatangan Digital
          </h3>
          <div className="space-y-4">
            <div>
              <Label htmlFor="sign-name">Full Name (as per IC) *</Label>
              <Input
                id="sign-name"
                value={signatureData.signed_name}
                onChange={(e) => setSignatureData({ ...signatureData, signed_name: e.target.value })}
                placeholder="Enter your full name"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="sign-ic">IC Number *</Label>
              <Input
                id="sign-ic"
                value={signatureData.signed_ic}
                onChange={(e) => setSignatureData({ ...signatureData, signed_ic: e.target.value })}
                placeholder="e.g., 901231-14-5678"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="sign-date">Date</Label>
              <Input
                id="sign-date"
                type="date"
                value={signatureData.signed_date}
                onChange={(e) => setSignatureData({ ...signatureData, signed_date: e.target.value })}
                className="mt-1"
              />
            </div>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-sm text-amber-800">
            By clicking "Submit & Sign", you confirm that all information is accurate and you agree to be bound by the terms of this indemnity form.
          </p>
        </div>
      </div>
    );
  };

  // Determine what to render based on current step
  const renderContent = () => {
    if (currentStep === 0) {
      return renderIntro();
    } else if (currentStep <= sections.length) {
      return renderSection(sections[currentStep - 1], currentStep - 1);
    } else {
      return renderSignature();
    }
  };

  const canGoNext = () => {
    if (currentStep === 0) return true;
    if (currentStep <= sections.length) {
      return acceptedSections[sections[currentStep - 1]?.id];
    }
    return false;
  };

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent 
        className="sm:max-w-2xl max-h-[90vh] overflow-hidden flex flex-col" 
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600" />
            PARTICIPANT INDEMNITY & DECLARATION
          </DialogTitle>
          <DialogDescription>
            Step {currentStep + 1} of {totalSteps}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {renderContent()}
        </div>

        <DialogFooter className="flex-shrink-0 gap-2">
          {currentStep > 0 && currentStep <= sections.length && (
            <Button 
              variant="outline" 
              onClick={() => setCurrentStep(prev => prev - 1)}
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Back
            </Button>
          )}
          
          {currentStep === 0 && (
            <Button onClick={() => setCurrentStep(1)}>
              Begin
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          )}
          
          {currentStep > 0 && currentStep < sections.length && canGoNext() && (
            <Button onClick={() => setCurrentStep(prev => prev + 1)}>
              Next Section
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          )}
          
          {currentStep === sections.length && canGoNext() && (
            <Button onClick={() => setCurrentStep(totalSteps - 1)}>
              Proceed to Sign
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          )}
          
          {currentStep === totalSteps - 1 && (
            <Button 
              onClick={handleSubmit} 
              disabled={isSubmitting || !signatureData.signed_name.trim() || !signatureData.signed_ic.trim()}
              className="bg-green-600 hover:bg-green-700"
            >
              {isSubmitting ? 'Submitting...' : 'Submit & Sign'}
              <Lock className="w-4 h-4 ml-1" />
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default IndemnityForm;
