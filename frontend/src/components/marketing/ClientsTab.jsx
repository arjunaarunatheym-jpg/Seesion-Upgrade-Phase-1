/**
 * ClientsTab - Marketing client management
 */
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Search, Plus, Edit, Trash2, User, Phone, Mail, MapPin } from "lucide-react";

const ClientsTab = ({
  clients,
  clientSearch,
  setClientSearch,
  onAddClient,
  onEditClient,
  onDeleteClient,
}) => {
  const filteredClients = clients.filter(c =>
    c.company_name?.toLowerCase().includes(clientSearch.toLowerCase()) ||
    c.contact_person?.toLowerCase().includes(clientSearch.toLowerCase())
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>My Clients</CardTitle>
            <CardDescription>Manage your client list</CardDescription>
          </div>
          <Button onClick={onAddClient}>
            <Plus className="w-4 h-4 mr-2" /> Add Client
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              placeholder="Search clients..."
              value={clientSearch}
              onChange={(e) => setClientSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredClients.map(client => (
            <Card key={client.id} className="border">
              <CardContent className="p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-gray-900">{client.company_name}</h3>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => onEditClient(client)}>
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onDeleteClient(client.id)} className="text-red-600">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                <div className="space-y-1 text-sm text-gray-600">
                  <p className="flex items-center gap-2"><User className="w-3 h-3" /> {client.contact_person}</p>
                  <p className="flex items-center gap-2"><Phone className="w-3 h-3" /> {client.contact_phone}</p>
                  <p className="flex items-center gap-2"><Mail className="w-3 h-3" /> {client.contact_email}</p>
                  {client.company_address && (
                    <p className="flex items-start gap-2"><MapPin className="w-3 h-3 mt-1" /> {client.company_address}</p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        
        {filteredClients.length === 0 && (
          <p className="text-center text-gray-500 py-8">No clients found. Add your first client!</p>
        )}
      </CardContent>
    </Card>
  );
};

export { ClientsTab };
