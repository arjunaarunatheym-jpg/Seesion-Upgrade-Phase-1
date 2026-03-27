import { useState, useRef, useEffect } from "react";
import { Input } from "./ui/input";
import { axiosInstance } from "../App";
import { toast } from "sonner";
import { Building2, Plus, Check, Loader2 } from "lucide-react";

/**
 * CompanyCombobox — searchable dropdown with auto-create.
 * Props:
 *   companies: array of {id, name} 
 *   value: selected company_id
 *   onChange: (company_id, company_name) => void
 *   onCompanyCreated: (newCompany) => void — refresh parent company list
 *   excludeId: company_id to exclude from the list (e.g., primary company)
 *   placeholder: string
 */
export function CompanyCombobox({ companies = [], value, onChange, onCompanyCreated, excludeId, placeholder = "Search or type new company..." }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const wrapperRef = useRef(null);
  const inputRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = companies
    .filter((c) => (excludeId ? c.id !== excludeId : true))
    .filter((c) => c.name?.toLowerCase().includes(query.toLowerCase()));

  const exactMatch = filtered.some((c) => c.name?.toLowerCase() === query.toLowerCase());
  const selectedCompany = companies.find((c) => c.id === value);

  const handleSelect = (company) => {
    onChange(company.id, company.name);
    setQuery("");
    setOpen(false);
  };

  const handleCreate = async () => {
    if (!query.trim()) return;
    setCreating(true);
    try {
      const res = await axiosInstance.post("/companies", { name: query.trim() });
      const newCompany = res.data;
      toast.success(`Company "${newCompany.name}" created`);
      if (onCompanyCreated) onCompanyCreated(newCompany);
      onChange(newCompany.id, newCompany.name);
      setQuery("");
      setOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create company");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div ref={wrapperRef} className="relative" data-testid="company-combobox">
      <div
        className="flex items-center border rounded-md px-3 py-2 text-sm cursor-text bg-white hover:border-gray-400 transition-colors"
        onClick={() => { setOpen(true); inputRef.current?.focus(); }}
      >
        <Building2 className="w-4 h-4 text-gray-400 mr-2 flex-shrink-0" />
        {open ? (
          <input
            ref={inputRef}
            autoFocus
            className="flex-1 outline-none bg-transparent text-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            data-testid="company-combobox-input"
          />
        ) : (
          <span className={`flex-1 truncate ${selectedCompany ? "text-gray-900" : "text-gray-400"}`}>
            {selectedCompany?.name || placeholder}
          </span>
        )}
      </div>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white border rounded-md shadow-lg max-h-56 overflow-y-auto" data-testid="company-combobox-dropdown">
          {filtered.length === 0 && !query.trim() && (
            <div className="px-3 py-2 text-sm text-gray-400">Type to search or create...</div>
          )}

          {filtered.map((c) => (
            <div
              key={c.id}
              className={`flex items-center px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 transition-colors ${c.id === value ? "bg-blue-50 font-medium" : ""}`}
              onClick={() => handleSelect(c)}
              data-testid={`company-option-${c.id}`}
            >
              <span className="flex-1 truncate">{c.name}</span>
              {c.id === value && <Check className="w-4 h-4 text-blue-600 flex-shrink-0" />}
            </div>
          ))}

          {query.trim() && !exactMatch && (
            <div
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-green-50 border-t text-green-700 font-medium"
              onClick={handleCreate}
              data-testid="company-create-new"
            >
              {creating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
              Create "{query.trim()}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}
