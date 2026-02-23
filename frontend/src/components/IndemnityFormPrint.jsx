import React, { useRef } from 'react';
import { Button } from './ui/button';
import { X, Download, CheckCircle, XCircle } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const IndemnityFormPrint = ({ record, sessionInfo, companySettings, onClose }) => {
  const printRef = useRef(null);

  const handlePrint = () => {
    const printContent = printRef.current;
    const printWindow = window.open('', '_blank');
    
    const styling = companySettings?.document_styling || {};
    const primaryColor = styling.primary_color || '#1e40af';
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Indemnity Form - ${record.full_name}</title>
          <style>
            @page { size: A4; margin: 12mm; }
            @media print { 
              body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
              .no-break { page-break-inside: avoid; }
            }
            
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: Arial, sans-serif; font-size: 10px; line-height: 1.4; padding: 15px; }
            
            .header { text-align: center; margin-bottom: 15px; border-bottom: 2px solid ${primaryColor}; padding-bottom: 10px; }
            .logo { max-width: 100px; max-height: 50px; object-fit: contain; margin-bottom: 8px; }
            .company-name { font-size: 14px; font-weight: bold; color: ${primaryColor}; }
            .form-title { font-size: 14px; font-weight: bold; margin-top: 8px; text-transform: uppercase; }
            .form-subtitle { font-size: 11px; color: #666; }
            
            .info-section { background: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 12px; }
            .info-section h3 { font-size: 11px; font-weight: bold; margin-bottom: 8px; color: ${primaryColor}; }
            .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
            .info-item { font-size: 9px; }
            .info-item .label { color: #666; }
            .info-item .value { font-weight: bold; }
            
            .section { margin-bottom: 10px; border: 1px solid #ddd; border-radius: 5px; overflow: hidden; }
            .section-header { padding: 8px 10px; color: white; font-weight: bold; }
            .section-header-a { background: #dc2626; }
            .section-header-b { background: #ea580c; }
            .section-header-c { background: #9333ea; }
            .section-header-d { background: #2563eb; }
            .section-header-e { background: #059669; }
            .section-header-f { background: #0891b2; }
            .section-title { font-size: 10px; }
            .section-subtitle { font-size: 8px; opacity: 0.9; }
            .section-content { padding: 10px; font-size: 9px; }
            .section-content p { margin-bottom: 6px; }
            .section-content .malay { color: #555; font-style: italic; }
            .section-content ul { margin-left: 15px; margin-bottom: 6px; }
            
            .check-status { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 3px; font-size: 8px; font-weight: bold; margin-top: 6px; }
            .checked { background: #dcfce7; color: #166534; }
            .unchecked { background: #fee2e2; color: #991b1b; }
            
            .signature-section { margin-top: 15px; padding-top: 12px; border-top: 2px solid ${primaryColor}; }
            .signature-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }
            .signature-box { text-align: center; }
            .signature-line { border-bottom: 1px solid #000; height: 35px; margin-bottom: 4px; display: flex; align-items: flex-end; justify-content: center; }
            .signature-name { font-style: italic; padding-bottom: 3px; }
            .signature-label { font-size: 8px; color: #666; }
            .signature-value { font-weight: bold; font-size: 9px; margin-top: 3px; }
            
            .acceptance-badge { 
              display: inline-block; 
              padding: 6px 12px; 
              border-radius: 15px; 
              font-weight: bold;
              font-size: 10px;
              margin: 10px 0;
            }
            .accepted { background: #dcfce7; color: #166534; }
            .not-accepted { background: #fee2e2; color: #991b1b; }
            
            .footer { margin-top: 15px; text-align: center; font-size: 8px; color: #666; border-top: 1px solid #ccc; padding-top: 8px; }
          </style>
        </head>
        <body>
          ${printContent.innerHTML}
        </body>
      </html>
    `);
    
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 250);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  // Get sections accepted status (from new v2 form or legacy)
  const sectionsAccepted = record.indemnity_sections_accepted || {};
  const hasV2Data = Object.keys(sectionsAccepted).length > 0;

  // Section check indicator
  const SectionCheck = ({ checked }) => (
    <span className={`check-status ${checked ? 'checked' : 'unchecked'}`}>
      {checked ? '✓ ACKNOWLEDGED' : '✗ NOT CHECKED'}
    </span>
  );

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-lg w-full max-w-3xl max-h-[95vh] overflow-y-auto">
        {/* Action Bar */}
        <div className="sticky top-0 bg-white border-b p-3 flex justify-between items-center z-10">
          <h2 className="text-lg font-bold">Indemnity Form - {record.full_name}</h2>
          <div className="flex gap-2">
            <Button onClick={handlePrint} className="bg-green-600 hover:bg-green-700">
              <Download className="w-4 h-4 mr-2" />
              Download / Print
            </Button>
            <Button variant="outline" onClick={onClose}>
              <X className="w-4 h-4 mr-2" />
              Close
            </Button>
          </div>
        </div>

        {/* Printable Content */}
        <div ref={printRef} className="p-6 bg-white">
          {/* Header */}
          <div className="header">
            {companySettings?.logo_url && (
              <img src={companySettings.logo_url.startsWith('/') ? `${API_URL}${companySettings.logo_url}` : companySettings.logo_url} alt="Logo" className="logo" style={{ margin: '0 auto', display: 'block' }} />
            )}
            <div className="company-name">{companySettings?.company_name || 'MDDRC SDN BHD'}</div>
            <div className="form-title">PARTICIPANT INDEMNITY & DECLARATION</div>
            <div className="form-subtitle">AKUAN & INDEMNITI PESERTA</div>
          </div>

          {/* Session Information */}
          <div className="info-section">
            <h3>Training Session / Sesi Latihan</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="label">Programme: </span>
                <span className="value">{sessionInfo?.session_name || '-'}</span>
              </div>
              <div className="info-item">
                <span className="label">Company: </span>
                <span className="value">{sessionInfo?.company_name || '-'}</span>
              </div>
              <div className="info-item">
                <span className="label">Date: </span>
                <span className="value">{sessionInfo?.training_date || '-'}</span>
              </div>
              <div className="info-item">
                <span className="label">Location: </span>
                <span className="value">{sessionInfo?.location || '-'}</span>
              </div>
            </div>
          </div>

          {/* Participant Information */}
          <div className="info-section">
            <h3>Participant Information / Maklumat Peserta</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="label">Full Name: </span>
                <span className="value">{record.full_name}</span>
              </div>
              <div className="info-item">
                <span className="label">NRIC/Passport: </span>
                <span className="value">{record.id_number || '-'}</span>
              </div>
              <div className="info-item">
                <span className="label">Contact: </span>
                <span className="value">{record.phone_number || '-'}</span>
              </div>
              <div className="info-item">
                <span className="label">Email: </span>
                <span className="value">{record.email || '-'}</span>
              </div>
            </div>
          </div>

          {/* Emergency Contact */}
          {record.emergency_contact_name && (
            <div className="info-section">
              <h3>Emergency Contact / Hubungan Kecemasan</h3>
              <div className="info-grid">
                <div className="info-item">
                  <span className="label">Name: </span>
                  <span className="value">{record.emergency_contact_name}</span>
                </div>
                <div className="info-item">
                  <span className="label">Relationship: </span>
                  <span className="value">{record.emergency_contact_relationship || '-'}</span>
                </div>
                <div className="info-item">
                  <span className="label">Phone: </span>
                  <span className="value">{record.emergency_contact_phone || '-'}</span>
                </div>
              </div>
            </div>
          )}

          {/* SECTION A - Acknowledgement of Risk */}
          <div className="section no-break">
            <div className="section-header section-header-a">
              <div className="section-title">SECTION A – ACKNOWLEDGEMENT OF RISK</div>
              <div className="section-subtitle">SEKSYEN A – PENGAKUAN RISIKO</div>
            </div>
            <div className="section-content">
              <p><strong>English:</strong> I acknowledge that Defensive Driving and/or Defensive Riding training includes theoretical and practical activities which involve inherent risks. I voluntarily participate in this training and accept all associated risks.</p>
              <p className="malay"><strong>Bahasa Malaysia:</strong> Saya mengakui bahawa latihan Pemanduan Defensif dan/atau Tunggang Defensif melibatkan aktiviti teori dan praktikal yang mempunyai risiko tersendiri. Saya menyertai latihan ini secara sukarela dan menerima semua risiko yang berkaitan.</p>
              {hasV2Data && <SectionCheck checked={sectionsAccepted.section_a} />}
            </div>
          </div>

          {/* SECTION B - Vehicle Responsibility */}
          <div className="section no-break">
            <div className="section-header section-header-b">
              <div className="section-title">SECTION B – VEHICLE RESPONSIBILITY</div>
              <div className="section-subtitle">SEKSYEN B – TANGGUNGJAWAB KENDERAAN</div>
            </div>
            <div className="section-content">
              <p><strong>English:</strong> I confirm that I am using my own vehicle or motorcycle, and I am fully responsible for ensuring that it is:</p>
              <ul>
                <li>In good mechanical condition</li>
                <li>Roadworthy and legally compliant</li>
                <li>Properly insured</li>
                <li>Safe and suitable for training use</li>
              </ul>
              <p className="malay"><strong>Bahasa Malaysia:</strong> Saya mengesahkan bahawa saya menggunakan kenderaan atau motosikal milik sendiri, dan saya bertanggungjawab sepenuhnya untuk memastikan kenderaan tersebut berada dalam keadaan mekanikal yang baik, layak jalan dan mematuhi undang-undang, dilindungi insurans yang sah, serta selamat dan sesuai untuk latihan.</p>
              {hasV2Data && <SectionCheck checked={sectionsAccepted.section_b} />}
            </div>
          </div>

          {/* SECTION C - Trainer Authority */}
          <div className="section no-break">
            <div className="section-header section-header-c">
              <div className="section-title">SECTION C – TRAINER AUTHORITY</div>
              <div className="section-subtitle">SEKSYEN C – KUASA JURULATIH</div>
            </div>
            <div className="section-content">
              <p><strong>English:</strong> I understand and agree that the trainer has full authority to inspect my vehicle before training commences. The trainer reserves the right to disqualify any vehicle deemed unsafe or unsuitable. I will not hold the trainer or training provider liable for any decisions made regarding vehicle suitability.</p>
              <p className="malay"><strong>Bahasa Malaysia:</strong> Saya faham dan bersetuju bahawa jurulatih mempunyai kuasa penuh untuk memeriksa kenderaan saya sebelum latihan bermula. Jurulatih berhak menolak mana-mana kenderaan yang dianggap tidak selamat atau tidak sesuai. Saya tidak akan mempertanggungjawabkan jurulatih atau penyedia latihan atas sebarang keputusan yang dibuat mengenai kesesuaian kenderaan.</p>
              {hasV2Data && <SectionCheck checked={sectionsAccepted.section_c} />}
            </div>
          </div>

          {/* SECTION D - Compliance & Conduct */}
          <div className="section no-break">
            <div className="section-header section-header-d">
              <div className="section-title">SECTION D – COMPLIANCE & CONDUCT</div>
              <div className="section-subtitle">SEKSYEN D – PEMATUHAN & KELAKUAN</div>
            </div>
            <div className="section-content">
              <p><strong>English:</strong> I agree to comply with all safety instructions and guidelines provided by the training provider and trainers. I will conduct myself in a responsible and professional manner throughout the training. Non-compliance may result in immediate removal from the training program without refund.</p>
              <p className="malay"><strong>Bahasa Malaysia:</strong> Saya bersetuju untuk mematuhi semua arahan dan garis panduan keselamatan yang disediakan oleh penyedia latihan dan jurulatih. Saya akan berkelakuan secara bertanggungjawab dan profesional sepanjang latihan. Ketidakpatuhan boleh menyebabkan penyingkiran serta-merta daripada program latihan tanpa bayaran balik.</p>
              {hasV2Data && <SectionCheck checked={sectionsAccepted.section_d} />}
            </div>
          </div>

          {/* SECTION E - Indemnity */}
          <div className="section no-break">
            <div className="section-header section-header-e">
              <div className="section-title">SECTION E – INDEMNITY</div>
              <div className="section-subtitle">SEKSYEN E – INDEMNITI</div>
            </div>
            <div className="section-content">
              <p><strong>English:</strong> I hereby release, indemnify, and hold harmless {companySettings?.company_name || 'the Training Provider'}, its employees, agents, trainers, and representatives from any claims, damages, losses, injuries, or liabilities arising from my participation in this training program. This includes but is not limited to personal injury, property damage, or any other loss incurred during the training.</p>
              <p className="malay"><strong>Bahasa Malaysia:</strong> Dengan ini saya membebaskan, menanggung rugi, dan tidak mempertanggungjawabkan {companySettings?.company_name || 'Penyedia Latihan'}, pekerja, ejen, jurulatih, dan wakilnya daripada sebarang tuntutan, kerosakan, kerugian, kecederaan, atau liabiliti yang timbul daripada penyertaan saya dalam program latihan ini. Ini termasuk tetapi tidak terhad kepada kecederaan peribadi, kerosakan harta benda, atau sebarang kerugian lain yang ditanggung semasa latihan.</p>
              {hasV2Data && <SectionCheck checked={sectionsAccepted.section_e} />}
            </div>
          </div>

          {/* SECTION F - Final Declaration */}
          <div className="section no-break">
            <div className="section-header section-header-f">
              <div className="section-title">SECTION F – FINAL DECLARATION</div>
              <div className="section-subtitle">SEKSYEN F – AKUAN AKHIR</div>
            </div>
            <div className="section-content">
              <p><strong>English:</strong> I have read, understood, and agree to all terms and conditions stated in this indemnity form. I confirm that all information provided is true and accurate. I understand that providing false information may result in disqualification from the training.</p>
              <p className="malay"><strong>Bahasa Malaysia:</strong> Saya telah membaca, memahami, dan bersetuju dengan semua terma dan syarat yang dinyatakan dalam borang indemniti ini. Saya mengesahkan bahawa semua maklumat yang diberikan adalah benar dan tepat. Saya faham bahawa memberikan maklumat palsu boleh menyebabkan penyingkiran daripada latihan.</p>
              {hasV2Data && <SectionCheck checked={sectionsAccepted.section_f} />}
            </div>
          </div>

          {/* Acceptance Status */}
          <div style={{ textAlign: 'center', margin: '15px 0' }}>
            <span className={`acceptance-badge ${record.indemnity_accepted ? 'accepted' : 'not-accepted'}`}>
              {record.indemnity_accepted ? '✓ FORM ACCEPTED & SIGNED DIGITALLY' : '✗ NOT YET ACCEPTED'}
            </span>
          </div>

          {/* Signature Section */}
          <div className="signature-section">
            <div className="signature-grid">
              <div className="signature-box">
                <div className="signature-line">
                  {record.indemnity_signed_name && (
                    <span className="signature-name">{record.indemnity_signed_name}</span>
                  )}
                </div>
                <div className="signature-label">Participant Signature / Tandatangan Peserta</div>
                <div className="signature-value">{record.full_name}</div>
                {record.id_number && <div style={{ fontSize: '8px', color: '#666' }}>NRIC: {record.id_number}</div>}
              </div>
              <div className="signature-box">
                <div className="signature-line">
                  <span className="signature-name">{record.indemnity_signed_date ? formatDate(record.indemnity_signed_date) : '-'}</span>
                </div>
                <div className="signature-label">Date / Tarikh</div>
                <div className="signature-value">{record.indemnity_signed_date ? formatDate(record.indemnity_signed_date) : 'Not signed'}</div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="footer">
            <p>{companySettings?.company_name || 'Malaysian Defensive Driving and Riding Centre Sdn Bhd'}</p>
            <p>{companySettings?.address_line1 ? `${companySettings.address_line1}, ` : ''}{companySettings?.city || ''} {companySettings?.postcode || ''}</p>
            <p style={{ marginTop: '5px', fontSize: '7px' }}>This form was digitally signed and accepted through the Training Management System</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IndemnityFormPrint;
