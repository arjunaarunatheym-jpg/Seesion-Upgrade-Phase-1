import React, { useState, useRef, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { Shield, AlertTriangle, Car, CheckCircle, UserCheck, FileText, Lock } from "lucide-react";

const IndemnityForm = ({ 
  open, 
  onAccept, 
  participant,  // User data with auto-filled fields
  trainingSession,  // Training session data (optional - for auto-fields)
  companySettings  // Company settings for branding
}) => {
  const scrollContainerRef = useRef(null);
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Section checkboxes state
  const [sections, setSections] = useState({
    section_a: false,  // Acknowledgement of Risk
    section_b: false,  // Vehicle Responsibility
    section_c: false,  // Trainer Authority
    section_d: false,  // Compliance & Conduct
    section_e: false,  // Indemnity
    section_f: false   // Final Declaration
  });
  
  // Signature data
  const [signatureData, setSignatureData] = useState({
    signed_name: participant?.full_name || '',
    signed_ic: participant?.id_number || '',
    signed_date: new Date().toISOString().split('T')[0]
  });

  // Check if all sections are checked
  const allSectionsChecked = Object.values(sections).every(v => v);
  
  // Check if form is valid
  const isFormValid = hasScrolledToBottom && 
                      allSectionsChecked && 
                      signatureData.signed_name.trim() && 
                      signatureData.signed_ic.trim() &&
                      signatureData.signed_date;

  // Handle scroll detection
  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    // Consider "scrolled to bottom" when within 50px of bottom
    if (scrollHeight - scrollTop - clientHeight < 50) {
      setHasScrolledToBottom(true);
    }
  };

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

  // Handle form submission
  const handleSubmit = async () => {
    if (!isFormValid) {
      toast.error("Please complete all sections and sign the form");
      return;
    }
    
    setIsSubmitting(true);
    try {
      await onAccept({
        ...signatureData,
        sections_accepted: sections,
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

  // Section checkbox component
  const SectionCheckbox = ({ id, label, checked, onChange }) => (
    <div className="flex items-center space-x-3 py-2 px-3 bg-white rounded border hover:bg-gray-50">
      <Checkbox 
        id={id}
        checked={checked}
        onCheckedChange={onChange}
        disabled={!hasScrolledToBottom}
      />
      <label 
        htmlFor={id}
        className={`text-sm font-medium cursor-pointer ${!hasScrolledToBottom ? 'text-gray-400' : 'text-gray-700'}`}
      >
        {label}
      </label>
      {checked && <CheckCircle className="w-4 h-4 text-green-500 ml-auto" />}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent 
        className="sm:max-w-3xl max-h-[95vh] overflow-hidden flex flex-col" 
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Shield className="w-6 h-6 text-blue-600" />
            PARTICIPANT INDEMNITY & DECLARATION
          </DialogTitle>
          <DialogDescription className="text-base">
            AKUAN & INDEMNITI PESERTA
          </DialogDescription>
        </DialogHeader>

        {/* Scroll indicator */}
        {!hasScrolledToBottom && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center gap-2 flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <span className="text-sm text-amber-800">
              Please scroll to the bottom to read the entire form before accepting
            </span>
          </div>
        )}

        {/* Scrollable content */}
        <div 
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto space-y-6 pr-2"
          style={{ maxHeight: 'calc(95vh - 300px)' }}
        >
          {/* Auto-filled Participant Info */}
          <div className="bg-blue-50 p-3 sm:p-4 rounded-lg border border-blue-200">
            <h3 className="font-semibold text-blue-900 mb-3 flex items-center gap-2 text-sm sm:text-base">
              <UserCheck className="w-4 h-4 sm:w-5 sm:h-5" />
              Participant Information / Maklumat Peserta
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 text-xs sm:text-sm">
              <div><span className="text-gray-600">Full Name:</span> <strong>{participant?.full_name || '-'}</strong></div>
              <div><span className="text-gray-600">NRIC/Passport:</span> <strong>{participant?.id_number || '-'}</strong></div>
              <div><span className="text-gray-600">Contact:</span> <strong>{participant?.contact_phone || participant?.phone_number || '-'}</strong></div>
              <div className="break-all"><span className="text-gray-600">Email:</span> <strong>{participant?.contact_email || participant?.email || '-'}</strong></div>
              {participant?.company_name && (
                <div className="col-span-1 sm:col-span-2"><span className="text-gray-600">Employer:</span> <strong>{participant.company_name}</strong></div>
              )}
            </div>
          </div>

          {/* Training Session Info (if available) */}
          {trainingSession && (
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <h3 className="font-semibold text-green-900 mb-3 flex items-center gap-2">
                <Car className="w-5 h-5" />
                Training Session / Sesi Latihan
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-gray-600">Programme:</span> <strong>{trainingSession.name || '-'}</strong></div>
                <div><span className="text-gray-600">Type:</span> <strong>{trainingSession.type || 'Driving/Riding'}</strong></div>
                <div><span className="text-gray-600">Date:</span> <strong>{trainingSession.start_date || '-'}</strong></div>
                <div><span className="text-gray-600">Location:</span> <strong>{trainingSession.venue || '-'}</strong></div>
                {trainingSession.trainer_name && (
                  <div className="col-span-2"><span className="text-gray-600">Facilitator:</span> <strong>{trainingSession.trainer_name}</strong></div>
                )}
              </div>
            </div>
          )}

          {/* Training Provider */}
          <div className="bg-gray-100 p-4 rounded-lg text-center">
            <p className="font-semibold text-gray-900">Training Provider / Penyedia Latihan:</p>
            <p className="text-gray-700">{companySettings?.company_name || 'Malaysian Defensive Driving and Riding Centre Sdn Bhd'}</p>
            <p className="text-sm text-gray-600">
              {companySettings?.address_line1 || 'Lot 3A, Jalan Utara'}, {companySettings?.city || 'Petaling Jaya'}, {companySettings?.postcode || '46200'}, {companySettings?.state || 'Selangor'}
            </p>
          </div>

          {/* SECTION A */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-red-600 text-white p-3">
              <h3 className="font-bold">SECTION A – ACKNOWLEDGEMENT OF RISK</h3>
              <p className="text-sm opacity-90">SEKSYEN A – PENGAKUAN RISIKO</p>
            </div>
            <div className="p-4 space-y-3 bg-red-50">
              <div className="bg-white p-3 rounded border-l-4 border-red-500">
                <p className="text-sm mb-2">
                  <strong>English:</strong> I acknowledge that Defensive Driving and/or Defensive Riding training includes theoretical and practical activities which involve inherent risks. I voluntarily participate in this training and accept all associated risks.
                </p>
                <p className="text-sm text-gray-600 italic">
                  <strong>Bahasa Malaysia:</strong> Saya mengakui bahawa latihan Pemanduan Defensif dan/atau Tunggang Defensif melibatkan aktiviti teori dan praktikal yang mempunyai risiko tersendiri. Saya menyertai latihan ini secara sukarela dan menerima semua risiko yang berkaitan.
                </p>
              </div>
              <SectionCheckbox 
                id="section_a"
                label="☐ I acknowledge / Saya mengakui"
                checked={sections.section_a}
                onChange={(v) => setSections({...sections, section_a: v})}
              />
            </div>
          </div>

          {/* SECTION B */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-orange-600 text-white p-3">
              <h3 className="font-bold">SECTION B – VEHICLE RESPONSIBILITY</h3>
              <p className="text-sm opacity-90">SEKSYEN B – TANGGUNGJAWAB KENDERAAN</p>
            </div>
            <div className="p-4 space-y-3 bg-orange-50">
              <div className="bg-white p-3 rounded border-l-4 border-orange-500">
                <p className="text-sm mb-2">
                  <strong>English:</strong> I confirm that I am using my own vehicle or motorcycle, and I am fully responsible for ensuring that it is:
                </p>
                <ul className="text-sm list-disc ml-5 mb-2">
                  <li>In good mechanical condition</li>
                  <li>Roadworthy and legally compliant</li>
                  <li>Properly insured</li>
                  <li>Safe and suitable for training use</li>
                </ul>
                <p className="text-sm text-gray-600 italic">
                  <strong>Bahasa Malaysia:</strong> Saya mengesahkan bahawa saya menggunakan kenderaan atau motosikal milik sendiri, dan saya bertanggungjawab sepenuhnya untuk memastikan kenderaan tersebut berada dalam keadaan mekanikal yang baik, layak jalan dan mematuhi undang-undang, dilindungi insurans yang sah, serta selamat dan sesuai untuk latihan.
                </p>
              </div>
              <SectionCheckbox 
                id="section_b"
                label="☐ I confirm / Saya mengesahkan"
                checked={sections.section_b}
                onChange={(v) => setSections({...sections, section_b: v})}
              />
            </div>
          </div>

          {/* SECTION C */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-purple-600 text-white p-3">
              <h3 className="font-bold">SECTION C – TRAINER AUTHORITY</h3>
              <p className="text-sm opacity-90">SEKSYEN C – KUASA JURULATIH</p>
            </div>
            <div className="p-4 space-y-3 bg-purple-50">
              <div className="bg-white p-3 rounded border-l-4 border-purple-500">
                <p className="text-sm mb-2">
                  <strong>English:</strong> I acknowledge that the Facilitator or Chief Trainer has the authority to inspect and assess my vehicle and may refuse or prohibit its use if it is deemed unsafe, unroadworthy, or unsuitable for training. <strong>Such decision shall be final and no refund shall be applicable.</strong>
                </p>
                <p className="text-sm text-gray-600 italic">
                  <strong>Bahasa Malaysia:</strong> Saya mengakui bahawa Fasilitator atau Ketua Jurulatih mempunyai kuasa untuk memeriksa dan menilai kenderaan saya dan boleh menolak atau melarang penggunaannya sekiranya didapati tidak selamat, tidak layak jalan, atau tidak sesuai untuk latihan. Keputusan tersebut adalah muktamad dan tiada bayaran balik akan diberikan.
                </p>
              </div>
              <SectionCheckbox 
                id="section_c"
                label="☐ I agree / Saya bersetuju"
                checked={sections.section_c}
                onChange={(v) => setSections({...sections, section_c: v})}
              />
            </div>
          </div>

          {/* SECTION D */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-teal-600 text-white p-3">
              <h3 className="font-bold">SECTION D – COMPLIANCE & CONDUCT</h3>
              <p className="text-sm opacity-90">SEKSYEN D – PEMATUHAN & TATATERTIB</p>
            </div>
            <div className="p-4 space-y-3 bg-teal-50">
              <div className="bg-white p-3 rounded border-l-4 border-teal-500">
                <p className="text-sm mb-2">
                  <strong>English:</strong> I agree to comply with all safety rules, instructions, and directions given by the Training Provider and its trainers. Failure to comply may result in removal from training.
                </p>
                <p className="text-sm text-gray-600 italic">
                  <strong>Bahasa Malaysia:</strong> Saya bersetuju untuk mematuhi semua peraturan keselamatan, arahan, dan panduan yang diberikan oleh Penyedia Latihan dan jurulatih. Kegagalan mematuhi boleh menyebabkan saya dikeluarkan daripada latihan.
                </p>
              </div>
              <SectionCheckbox 
                id="section_d"
                label="☐ I agree / Saya bersetuju"
                checked={sections.section_d}
                onChange={(v) => setSections({...sections, section_d: v})}
              />
            </div>
          </div>

          {/* SECTION E */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-blue-600 text-white p-3">
              <h3 className="font-bold">SECTION E – INDEMNITY (TRAINING PROVIDER & VENUE OWNER)</h3>
              <p className="text-sm opacity-90">SEKSYEN E – INDEMNITI (PENYEDIA LATIHAN & PEMILIK PREMIS)</p>
            </div>
            <div className="p-4 space-y-3 bg-blue-50">
              <div className="bg-white p-3 rounded border-l-4 border-blue-500">
                <p className="text-sm mb-2">
                  <strong>English:</strong> I agree to indemnify and hold harmless the Training Provider and, where applicable, the Venue Owner from any claims, losses, damages, or liabilities arising from my participation in the training or my use of any vehicle or equipment.
                </p>
                <p className="text-sm text-gray-600 italic">
                  <strong>Bahasa Malaysia:</strong> Saya bersetuju untuk memberi indemniti dan melindungi Penyedia Latihan dan, jika berkenaan, Pemilik Premis daripada sebarang tuntutan, kerugian, kerosakan, atau liabiliti yang timbul akibat penyertaan saya dalam latihan atau penggunaan kenderaan atau peralatan oleh saya.
                </p>
              </div>
              <SectionCheckbox 
                id="section_e"
                label="☐ I agree / Saya bersetuju"
                checked={sections.section_e}
                onChange={(v) => setSections({...sections, section_e: v})}
              />
            </div>
          </div>

          {/* SECTION F - Final Declaration */}
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-green-600 text-white p-3">
              <h3 className="font-bold">SECTION F – FINAL DECLARATION</h3>
              <p className="text-sm opacity-90">SEKSYEN F – AKUAN AKHIR</p>
            </div>
            <div className="p-4 space-y-3 bg-green-50">
              <div className="bg-white p-3 rounded border-l-4 border-green-500">
                <p className="text-sm mb-2">
                  <strong>English:</strong> By clicking "Agree & Proceed", I confirm that I have read, understood, and accepted this Indemnity & Declaration.
                </p>
                <p className="text-sm text-gray-600 italic">
                  <strong>Bahasa Malaysia:</strong> Dengan menekan "Setuju & Teruskan", saya mengesahkan bahawa saya telah membaca, memahami, dan bersetuju dengan Akuan & Indemniti ini.
                </p>
              </div>
              <SectionCheckbox 
                id="section_f"
                label="☐ I confirm and declare / Saya sahkan dan akui"
                checked={sections.section_f}
                onChange={(v) => setSections({...sections, section_f: v})}
              />
            </div>
          </div>

          {/* Digital Signature Section */}
          <div className="border-2 border-gray-300 rounded-lg p-4 bg-gray-50">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Digital Signature / Tandatangan Digital
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="signed_name">Full Name (as signature) / Nama Penuh</Label>
                <Input 
                  id="signed_name"
                  value={signatureData.signed_name}
                  onChange={(e) => setSignatureData({...signatureData, signed_name: e.target.value})}
                  placeholder="Type your full name"
                  className="mt-1 bg-white"
                  disabled={!hasScrolledToBottom}
                />
              </div>
              <div>
                <Label htmlFor="signed_ic">NRIC / Passport Number</Label>
                <Input 
                  id="signed_ic"
                  value={signatureData.signed_ic}
                  onChange={(e) => setSignatureData({...signatureData, signed_ic: e.target.value})}
                  placeholder="Your IC/Passport number"
                  className="mt-1 bg-white"
                  disabled={!hasScrolledToBottom}
                />
              </div>
            </div>
            
            <div className="mt-4 w-full md:w-1/2">
              <Label htmlFor="signed_date">Date / Tarikh</Label>
              <Input 
                id="signed_date"
                type="date"
                value={signatureData.signed_date}
                onChange={(e) => setSignatureData({...signatureData, signed_date: e.target.value})}
                className="mt-1 bg-white"
                disabled={!hasScrolledToBottom}
              />
            </div>
          </div>
        </div>

        {/* Footer with validation status and submit button */}
        <DialogFooter className="flex-shrink-0 border-t pt-4">
          <div className="w-full space-y-3">
            {/* Validation checklist */}
            <div className="flex flex-wrap gap-2 text-sm">
              <span className={`px-2 py-1 rounded ${hasScrolledToBottom ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'}`}>
                {hasScrolledToBottom ? '✓' : '○'} Scroll Complete
              </span>
              <span className={`px-2 py-1 rounded ${allSectionsChecked ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'}`}>
                {allSectionsChecked ? '✓' : '○'} All Sections ({Object.values(sections).filter(v=>v).length}/6)
              </span>
              <span className={`px-2 py-1 rounded ${signatureData.signed_name && signatureData.signed_ic ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'}`}>
                {signatureData.signed_name && signatureData.signed_ic ? '✓' : '○'} Signature
              </span>
            </div>
            
            <Button 
              onClick={handleSubmit}
              disabled={!isFormValid || isSubmitting}
              className="w-full h-12 text-lg"
              style={{ 
                backgroundColor: isFormValid ? (companySettings?.primary_color || '#1e40af') : undefined 
              }}
            >
              {isSubmitting ? (
                <>Processing...</>
              ) : (
                <>
                  <Lock className="w-5 h-5 mr-2" />
                  Agree & Proceed / Setuju & Teruskan
                </>
              )}
            </Button>
            
            <p className="text-xs text-center text-gray-500">
              By clicking above, you agree that your submission is legally binding and cannot be changed once submitted.
            </p>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default IndemnityForm;
