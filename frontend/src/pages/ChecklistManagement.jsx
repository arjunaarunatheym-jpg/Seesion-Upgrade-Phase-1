import { useState, useEffect } from "react";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Plus, Trash2, ClipboardList, Upload } from "lucide-react";

const ChecklistManagement = ({ program }) => {
  const [checklistTemplates, setChecklistTemplates] = useState([]);
  const [checklistDialogOpen, setChecklistDialogOpen] = useState(false);
  const [newChecklistItem, setNewChecklistItem] = useState("");
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (program) {
      loadChecklistTemplates();
    }
  }, [program]);

  const loadChecklistTemplates = async () => {
    try {
      const response = await axiosInstance.get("/checklist-templates");
      setChecklistTemplates(response.data);
    } catch (error) {
      console.error("Failed to load checklist templates:", error);
    }
  };

  const handleAddChecklistItem = async (e) => {
    e.preventDefault();
    
    if (!newChecklistItem.trim()) {
      toast.error("Please enter a checklist item");
      return;
    }

    try {
      await axiosInstance.post("/checklist-templates", {
        program_id: program.id,
        items: [newChecklistItem.trim()]
      });
      
      toast.success("Checklist item added successfully");
      setNewChecklistItem("");
      setChecklistDialogOpen(false);
      loadChecklistTemplates();
    } catch (error) {
      toast.error("Failed to add checklist item");
      console.error(error);
    }
  };

  const handleDeleteChecklistItem = async (templateId, itemIndex) => {
    try {
      await axiosInstance.delete(`/checklist-templates/${templateId}/items/${itemIndex}`);
      toast.success("Checklist item deleted");
      loadChecklistTemplates();
    } catch (error) {
      toast.error("Failed to delete checklist item");
      console.error(error);
    }
  };

  const handleBulkUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error("Please upload an Excel file (.xlsx or .xls)");
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('program_id', program.id);

      const response = await axiosInstance.post('/checklist-templates/bulk-upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const { total_uploaded, warnings } = response.data;
      
      let message = `✓ Successfully uploaded ${total_uploaded} checklist item(s)!`;
      if (warnings) {
        message += `\n⚠ ${warnings}`;
      }
      
      toast.success(message);
      setUploadDialogOpen(false);
      loadChecklistTemplates();
      
      e.target.value = '';
    } catch (error) {
      const errorMessage = error.response?.data?.detail || "Failed to upload file";
      toast.error(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  const currentTemplate = checklistTemplates.find(t => t.program_id === program.id);

  return (
    <Card>
      <CardHeader className="px-3 sm:px-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="min-w-0">
            <CardTitle className="text-sm sm:text-base">Vehicle Inspection Checklist</CardTitle>
            <CardDescription className="text-xs break-words">
              {program.name}
            </CardDescription>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
              <Button size="sm" variant="outline" className="text-xs" onClick={() => setUploadDialogOpen(true)}>
                <Upload className="w-3.5 h-3.5 mr-1" />
                Bulk Upload
              </Button>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Bulk Upload Checklist Items</DialogTitle>
                  <DialogDescription>
                    Upload an Excel file (.xlsx or .xls) with checklist items
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="bg-blue-50 p-4 rounded-lg space-y-2">
                    <p className="text-sm font-medium text-blue-900">Excel Format Required:</p>
                    <ul className="text-sm text-blue-700 space-y-1">
                      <li>• <strong>Program Name</strong> - Must match existing program</li>
                      <li>• <strong>Item Name</strong> - Name of checklist item</li>
                    </ul>
                    <p className="text-xs text-blue-600 mt-2">
                      Example: Defensive Riding | Helmet
                    </p>
                  </div>
                  
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                    <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                    <label className="cursor-pointer">
                      <span className="text-sm text-gray-600">
                        {uploading ? "Uploading..." : "Click to select Excel file"}
                      </span>
                      <Input
                        type="file"
                        accept=".xlsx,.xls"
                        onChange={handleBulkUpload}
                        disabled={uploading}
                        className="hidden"
                      />
                    </label>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            <Dialog open={checklistDialogOpen} onOpenChange={setChecklistDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm" className="text-xs">
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Add Item
                </Button>
              </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Checklist Item</DialogTitle>
                <DialogDescription>
                  Add a new item to the vehicle inspection checklist
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleAddChecklistItem} className="space-y-4">
                <div>
                  <Label htmlFor="checklist-item">Item Name</Label>
                  <Input
                    id="checklist-item"
                    value={newChecklistItem}
                    onChange={(e) => setNewChecklistItem(e.target.value)}
                    placeholder="e.g., Brakes, Lights, Tires, Horn"
                    required
                  />
                </div>
                <Button type="submit" className="w-full">
                  Add Item
                </Button>
              </form>
            </DialogContent>
          </Dialog>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-3 sm:px-6">
        {!currentTemplate || currentTemplate.items.length === 0 ? (
          <div className="text-center py-12">
            <ClipboardList className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">No checklist items yet</p>
            <p className="text-sm text-gray-400 mt-2">
              Add inspection items using the button above
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {currentTemplate.items.map((item, idx) => {
              const itemName = typeof item === "string" ? item : (item.name || item.item || JSON.stringify(item));
              return (
                <div
                  key={idx}
                  className="flex justify-between items-center p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-semibold text-gray-700 bg-white px-2 py-0.5 rounded text-xs flex-shrink-0">
                      {idx + 1}
                    </span>
                    <span className="text-sm text-gray-900 break-words">{itemName}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="flex-shrink-0"
                    onClick={() => handleDeleteChecklistItem(currentTemplate.id, idx)}
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ChecklistManagement;
