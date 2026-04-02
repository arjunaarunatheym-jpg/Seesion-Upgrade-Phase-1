import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL;

const CertificateVerify = () => {
  const { certNumber } = useParams();
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") || (certNumber ? "cert" : "ic");

  const [activeTab, setActiveTab] = useState(initialTab);
  const [certInput, setCertInput] = useState(certNumber || "");
  const [icInput, setIcInput] = useState("");
  const [result, setResult] = useState(null);
  const [icResults, setIcResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  // Auto-search if certNumber from URL
  useState(() => {
    if (certNumber) {
      handleCertSearch(certNumber);
      setActiveTab("cert");
    }
  });

  async function handleCertSearch(num) {
    const searchNum = num || certInput;
    if (!searchNum.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setSearched(true);
    try {
      const urlSafe = searchNum.replace(/\//g, "-");
      const res = await axios.get(`${API}/api/verify/certificate/${urlSafe}`);
      setResult(res.data);
    } catch (err) {
      if (err.response?.status === 404) {
        setError("Certificate not found. Please check the certificate number and try again.");
      } else {
        setError("An error occurred. Please try again.");
      }
    }
    setLoading(false);
  }

  async function handleIcSearch() {
    if (!icInput.trim()) return;
    setLoading(true);
    setError("");
    setIcResults([]);
    setSearched(true);
    try {
      const res = await axios.get(`${API}/api/verify/search-ic/${icInput.replace(/-/g, "")}`);
      setIcResults(res.data.certificates || []);
      if ((res.data.certificates || []).length === 0) {
        setError("No certificates found for this IC number.");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred. Please try again.");
    }
    setLoading(false);
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return new Date(dateStr).toLocaleDateString("en-MY", {
        day: "numeric", month: "long", year: "numeric"
      });
    } catch { return dateStr; }
  };

  const isExpired = (endDate) => {
    if (!endDate) return false;
    return new Date(endDate) < new Date();
  };

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(135deg, #f0f4f8 0%, #e8eef5 100%)" }}>
      {/* Header */}
      <div style={{
        background: "#1a365d",
        padding: "20px 0",
        textAlign: "center",
        color: "white",
        boxShadow: "0 2px 10px rgba(0,0,0,0.15)"
      }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, letterSpacing: "0.5px" }}>
          MDDRC Certificate Verification
        </h1>
        <p style={{ margin: "6px 0 0", fontSize: "13px", opacity: 0.85 }}>
          Malaysian Defensive Driving and Riding Centre Sdn Bhd
        </p>
      </div>

      {/* Main Content */}
      <div style={{ maxWidth: 620, margin: "30px auto", padding: "0 16px" }}>
        {/* Tab Switcher */}
        <div style={{
          display: "flex", borderRadius: "8px", overflow: "hidden",
          border: "1px solid #d1d9e6", marginBottom: 24, background: "white"
        }}>
          <button
            data-testid="tab-cert-number"
            onClick={() => { setActiveTab("cert"); setError(""); setSearched(false); }}
            style={{
              flex: 1, padding: "12px", border: "none", cursor: "pointer",
              fontWeight: 600, fontSize: "13px",
              background: activeTab === "cert" ? "#1a365d" : "white",
              color: activeTab === "cert" ? "white" : "#4a5568",
              transition: "all 0.2s"
            }}
          >
            Search by Certificate Number
          </button>
          <button
            data-testid="tab-ic-number"
            onClick={() => { setActiveTab("ic"); setError(""); setSearched(false); }}
            style={{
              flex: 1, padding: "12px", border: "none", cursor: "pointer",
              fontWeight: 600, fontSize: "13px",
              background: activeTab === "ic" ? "#1a365d" : "white",
              color: activeTab === "ic" ? "white" : "#4a5568",
              transition: "all 0.2s"
            }}
          >
            Search by IC Number
          </button>
        </div>

        {/* Search Box */}
        <div style={{
          background: "white", borderRadius: 10, padding: 24,
          boxShadow: "0 2px 12px rgba(0,0,0,0.06)", border: "1px solid #e2e8f0"
        }}>
          {activeTab === "cert" ? (
            <div>
              <label style={{ fontWeight: 600, fontSize: 13, color: "#2d3748", display: "block", marginBottom: 6 }}>
                Certificate Number
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  data-testid="cert-number-input"
                  type="text"
                  placeholder="e.g., MDDRC/COC/2026/03/000008"
                  value={certInput}
                  onChange={(e) => setCertInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCertSearch()}
                  style={{
                    flex: 1, padding: "10px 14px", borderRadius: 6,
                    border: "1px solid #d1d9e6", fontSize: 14, outline: "none"
                  }}
                />
                <button
                  data-testid="cert-search-btn"
                  onClick={() => handleCertSearch()}
                  disabled={loading}
                  style={{
                    padding: "10px 20px", borderRadius: 6, border: "none",
                    background: "#1a365d", color: "white", fontWeight: 600,
                    fontSize: 13, cursor: loading ? "wait" : "pointer"
                  }}
                >
                  {loading ? "..." : "Verify"}
                </button>
              </div>
            </div>
          ) : (
            <div>
              <label style={{ fontWeight: 600, fontSize: 13, color: "#2d3748", display: "block", marginBottom: 6 }}>
                IC Number
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  data-testid="ic-number-input"
                  type="text"
                  placeholder="e.g., 861125385720 or 861125-38-5720"
                  value={icInput}
                  onChange={(e) => setIcInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleIcSearch()}
                  style={{
                    flex: 1, padding: "10px 14px", borderRadius: 6,
                    border: "1px solid #d1d9e6", fontSize: 14, outline: "none"
                  }}
                />
                <button
                  data-testid="ic-search-btn"
                  onClick={handleIcSearch}
                  disabled={loading}
                  style={{
                    padding: "10px 20px", borderRadius: 6, border: "none",
                    background: "#1a365d", color: "white", fontWeight: 600,
                    fontSize: 13, cursor: loading ? "wait" : "pointer"
                  }}
                >
                  {loading ? "..." : "Search"}
                </button>
              </div>
            </div>
          )}

          {/* Error */}
          {error && searched && (
            <div data-testid="verify-error" style={{
              marginTop: 16, padding: "12px 16px", borderRadius: 8,
              background: "#fff5f5", border: "1px solid #fed7d7", color: "#c53030",
              fontSize: 13
            }}>
              {error}
            </div>
          )}

          {/* Single Certificate Result */}
          {result && activeTab === "cert" && (
            <div data-testid="cert-result" style={{ marginTop: 20 }}>
              <div style={{
                padding: 16, borderRadius: 8, border: "2px solid #48bb78",
                background: "#f0fff4"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <span style={{
                    background: "#48bb78", color: "white", padding: "4px 12px",
                    borderRadius: 20, fontSize: 11, fontWeight: 700, textTransform: "uppercase"
                  }}>
                    Verified
                  </span>
                  {result.show_validity && result.validity_end && (
                    <span style={{
                      background: isExpired(result.validity_end) ? "#fc8181" : "#4472C4",
                      color: "white", padding: "4px 12px", borderRadius: 20,
                      fontSize: 11, fontWeight: 700, textTransform: "uppercase"
                    }}>
                      {isExpired(result.validity_end) ? "Expired" : "Valid"}
                    </span>
                  )}
                </div>
                <CertDetail label="Certificate No" value={result.certificate_number} />
                <CertDetail label="Participant" value={result.participant_name} />
                <CertDetail label="IC Number" value={result.ic_number} />
                <CertDetail label="Company" value={result.company_name} />
                <CertDetail label="Programme" value={result.programme} />
                <CertDetail label="Training Date" value={formatDate(result.training_date)} />
                <CertDetail label="Venue" value={result.venue} />
                {result.show_validity && (
                  <CertDetail
                    label="Validity"
                    value={`${formatDate(result.validity_start)} - ${formatDate(result.validity_end)}`}
                  />
                )}
                <CertDetail label="Issued" value={formatDate(result.issue_date)} />
              </div>
            </div>
          )}

          {/* IC Search Results */}
          {icResults.length > 0 && activeTab === "ic" && (
            <div data-testid="ic-results" style={{ marginTop: 20 }}>
              <p style={{ fontSize: 13, color: "#4a5568", marginBottom: 12 }}>
                Found <strong>{icResults.length}</strong> certificate(s)
              </p>
              {icResults.map((cert, idx) => (
                <div key={idx} style={{
                  padding: 14, borderRadius: 8, border: "1px solid #e2e8f0",
                  background: "#fafbfc", marginBottom: 10
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", flexWrap: "wrap", gap: 8 }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14, color: "#1a365d" }}>
                        {cert.participant_name}
                      </div>
                      <div style={{ fontSize: 12, color: "#718096" }}>{cert.ic_number}</div>
                    </div>
                    <span style={{
                      background: cert.show_validity && cert.validity_end && isExpired(cert.validity_end) ? "#fc8181" : "#48bb78",
                      color: "white", padding: "3px 10px", borderRadius: 12,
                      fontSize: 10, fontWeight: 700
                    }}>
                      {cert.show_validity && cert.validity_end && isExpired(cert.validity_end) ? "EXPIRED" : "VALID"}
                    </span>
                  </div>
                  <div style={{ marginTop: 8, fontSize: 12, color: "#4a5568", lineHeight: 1.8 }}>
                    <div><strong>Cert:</strong> {cert.certificate_number}</div>
                    <div><strong>Programme:</strong> {cert.programme}</div>
                    <div><strong>Company:</strong> {cert.company_name}</div>
                    <div><strong>Date:</strong> {formatDate(cert.training_date)}</div>
                    {cert.show_validity && cert.validity_end && (
                      <div><strong>Valid:</strong> {formatDate(cert.validity_start)} - {formatDate(cert.validity_end)}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: 30, fontSize: 11, color: "#a0aec0" }}>
          <p>Malaysian Defensive Driving and Riding Centre Sdn Bhd</p>
          <p>This is an official certificate verification portal.</p>
        </div>
      </div>
    </div>
  );
};

const CertDetail = ({ label, value }) => (
  <div style={{
    display: "flex", justifyContent: "space-between", padding: "6px 0",
    borderBottom: "1px solid #e2e8f0", fontSize: 13
  }}>
    <span style={{ color: "#718096", fontWeight: 500 }}>{label}</span>
    <span style={{ color: "#1a365d", fontWeight: 600, textAlign: "right", maxWidth: "60%" }}>{value || "-"}</span>
  </div>
);

export default CertificateVerify;
