/**
 * CompaniesTab Component - Extracted from AdminDashboard
 * Manages training companies
 */
import { useState } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Building2, Edit, Trash2 } from "lucide-react";
import { SearchBar } from "../SearchBar";

const initialCompanyForm = {
  name: '', 
  registration_no: '', 
  address_line1: '', 
  address_line2: '',
  city: '', 
  postcode: '', 
  state: '', 
  phone: '', 
  email: '', 
  contact_person: ''
};

// Moved outside component to prevent recreation on each render (fixes focus loss issue)
const CompanyFormFields = ({ data, setData }) => (
  <div className="grid grid-cols-2 gap-4">
    <div className="col-span-2">
      <Label htmlFor="company-name">Company Name *</Label>
      <Input
        id="company-name"
        data-testid="company-name-input"
        value={data.name}
        onChange={(e) => setData({...data, name: e.target.value})}
        required
      />
    </div>
    <div>
      <Label htmlFor="company-reg">Registration No.</Label>
      <Input
        id="company-reg"
        data-testid="company-reg-input"
        value={data.registration_no}
        onChange={(e) => setData({...data, registration_no: e.target.value})}
        placeholder="e.g., 1234567-A"
      />
    </div>
    <div>
      <Label htmlFor="company-contact">Contact Person</Label>
      <Input
        id="company-contact"
        value={data.contact_person}
        onChange={(e) => setData({...data, contact_person: e.target.value})}
      />
    </div>
    <div className="col-span-2">
      <Label htmlFor="company-address1">Address Line 1</Label>
      <Input
        id="company-address1"
        value={data.address_line1}
        onChange={(e) => setData({...data, address_line1: e.target.value})}
      />
    </div>
    <div className="col-span-2">
      <Label htmlFor="company-address2">Address Line 2</Label>
      <Input
        id="company-address2"
        value={data.address_line2}
        onChange={(e) => setData({...data, address_line2: e.target.value})}
      />
    </div>
    <div>
      <Label htmlFor="company-city">City</Label>
      <Input
        id="company-city"
        value={data.city}
        onChange={(e) => setData({...data, city: e.target.value})}
      />
    </div>
    <div>
      <Label htmlFor="company-postcode">Postcode</Label>
      <Input
        id="company-postcode"
        value={data.postcode}
        onChange={(e) => setData({...data, postcode: e.target.value})}
      />
    </div>
    <div>
      <Label htmlFor="company-state">State</Label>
      <Input
        id="company-state"
        value={data.state}
        onChange={(e) => setData({...data, state: e.target.value})}
      />
    </div>
    <div>
      <Label htmlFor="company-phone">Phone</Label>
      <Input
        id="company-phone"
        value={data.phone}
        onChange={(e) => setData({...data, phone: e.target.value})}
      />
    </div>
    <div className="col-span-2">
      <Label htmlFor="company-email">Email</Label>
      <Input
        id="company-email"
        type="email"
        value={data.email}
        onChange={(e) => setData({...data, email: e.target.value})}
      />
    </div>
  </div>
);

const CompaniesTab = ({ 
  companies, 
  filteredCompanies, 
  onSearch, 
  onRefresh,
  onDeleteClick 
}) => {
  const [companyFormData, setCompanyFormData] = useState(initialCompanyForm);
  const [companyDialogOpen, setCompanyDialogOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [editCompanyDialogOpen, setEditCompanyDialogOpen] = useState(false);

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/companies", companyFormData);
      toast.success("Company created successfully");
      setCompanyFormData(initialCompanyForm);
      setCompanyDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create company");
    }
  };

  const handleEditCompany = (company) => {
    setEditingCompany({ ...company });
    setEditCompanyDialogOpen(true);
  };

  const handleUpdateCompany = async () => {
    try {
      await axiosInstance.put(`/companies/${editingCompany.id}`, {
        name: editingCompany.name,
        registration_no: editingCompany.registration_no,
        address_line1: editingCompany.address_line1,
        address_line2: editingCompany.address_line2,
        city: editingCompany.city,
        postcode: editingCompany.postcode,
        state: editingCompany.state,
        phone: editingCompany.phone,
        email: editingCompany.email,
        contact_person: editingCompany.contact_person
      });
      toast.success("Company updated successfully");
      setEditCompanyDialogOpen(false);
      setEditingCompany(null);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update company");
    }
  };

  // Reusable form fields component
  const CompanyFormFields = ({ data, setData }) => (
    <div className="grid grid-cols-2 gap-4">
      <div className="col-span-2">
        <Label htmlFor="company-name">Company Name *</Label>
        <Input
          id="company-name"
          data-testid="company-name-input"
          value={data.name}
          onChange={(e) => setData({...data, name: e.target.value})}
          required
        />
      </div>
      <div>
        <Label htmlFor="company-reg">Registration No.</Label>
        <Input
          id="company-reg"
          data-testid="company-reg-input"
          value={data.registration_no}
          onChange={(e) => setData({...data, registration_no: e.target.value})}
          placeholder="e.g., 1234567-A"
        />
      </div>
      <div>
        <Label htmlFor="company-contact">Contact Person</Label>
        <Input
          id="company-contact"
          value={data.contact_person}
          onChange={(e) => setData({...data, contact_person: e.target.value})}
        />
      </div>
      <div className="col-span-2">
        <Label htmlFor="company-address1">Address Line 1</Label>
        <Input
          id="company-address1"
          value={data.address_line1}
          onChange={(e) => setData({...data, address_line1: e.target.value})}
        />
      </div>
      <div className="col-span-2">
        <Label htmlFor="company-address2">Address Line 2</Label>
        <Input
          id="company-address2"
          value={data.address_line2}
          onChange={(e) => setData({...data, address_line2: e.target.value})}
        />
      </div>
      <div>
        <Label htmlFor="company-city">City</Label>
        <Input
          id="company-city"
          value={data.city}
          onChange={(e) => setData({...data, city: e.target.value})}
        />
      </div>
      <div>
        <Label htmlFor="company-postcode">Postcode</Label>
        <Input
          id="company-postcode"
          value={data.postcode}
          onChange={(e) => setData({...data, postcode: e.target.value})}
        />
      </div>
      <div>
        <Label htmlFor="company-state">State</Label>
        <Input
          id="company-state"
          value={data.state}
          onChange={(e) => setData({...data, state: e.target.value})}
        />
      </div>
      <div>
        <Label htmlFor="company-phone">Phone</Label>
        <Input
          id="company-phone"
          value={data.phone}
          onChange={(e) => setData({...data, phone: e.target.value})}
        />
      </div>
      <div className="col-span-2">
        <Label htmlFor="company-email">Email</Label>
        <Input
          id="company-email"
          type="email"
          value={data.email}
          onChange={(e) => setData({...data, email: e.target.value})}
        />
      </div>
    </div>
  );

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Companies</CardTitle>
              <CardDescription>Manage training companies</CardDescription>
            </div>
            <Dialog open={companyDialogOpen} onOpenChange={setCompanyDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="create-company-button">
                  <Building2 className="w-4 h-4 mr-2" />
                  Add Company
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create New Company</DialogTitle>
                  <DialogDescription>
                    Add a new company to the system
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateCompany} className="space-y-4">
                  <CompanyFormFields data={companyFormData} setData={setCompanyFormData} />
                  <Button data-testid="submit-company-button" type="submit" className="w-full">
                    Create Company
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <SearchBar
              placeholder="Search companies by name..."
              onSearch={onSearch}
              className="max-w-md"
            />
          </div>
          <div className="space-y-2">
            {filteredCompanies.length === 0 ? (
              <div className="text-center py-12">
                <Building2 className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-500">
                  {companies.length === 0 ? "No companies yet. Add your first company!" : "No companies match your search."}
                </p>
              </div>
            ) : (
              filteredCompanies.map((company) => (
                <div
                  key={company.id}
                  data-testid={`company-item-${company.id}`}
                  className="p-4 bg-gray-50 rounded-lg flex justify-between items-center hover:bg-gray-100 transition-colors"
                >
                  <div>
                    <h3 className="font-semibold text-gray-900">{company.name}</h3>
                    {company.registration_no && (
                      <p className="text-sm text-gray-600">Reg: {company.registration_no}</p>
                    )}
                    <p className="text-sm text-gray-500">
                      Created: {new Date(company.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      data-testid={`edit-company-${company.id}`}
                      size="sm"
                      variant="outline"
                      onClick={() => handleEditCompany(company)}
                    >
                      <Edit className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      data-testid={`delete-company-${company.id}`}
                      size="sm"
                      variant="destructive"
                      onClick={() => onDeleteClick("company", company)}
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Delete
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Edit Company Dialog */}
      <Dialog open={editCompanyDialogOpen} onOpenChange={setEditCompanyDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Company</DialogTitle>
            <DialogDescription>
              Update company details
            </DialogDescription>
          </DialogHeader>
          {editingCompany && (
            <div className="space-y-4">
              <CompanyFormFields data={editingCompany} setData={setEditingCompany} />
              <Button onClick={handleUpdateCompany} className="w-full">
                Update Company
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default CompaniesTab;
