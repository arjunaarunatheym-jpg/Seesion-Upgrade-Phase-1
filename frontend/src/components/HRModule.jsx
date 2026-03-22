import React, { useState, useEffect, useRef } from 'react';
import { axiosInstance } from '../App';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  Users, Plus, Edit, Trash2, Save, Search, DollarSign, 
  FileText, Building2, Printer, X, Calculator, Loader2, Lock, Unlock,
  Calendar, Eye, RefreshCw, Upload, Download, Link
} from 'lucide-react';
import PayslipPrint from './PayslipPrint';
import PayAdvicePrint from './PayAdvicePrint';
import { EAFormsTab } from './hr/EAFormsTab';


const HRModule = () => {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('staff');
  const [companySettings, setCompanySettings] = useState(null);
  
  // Staff state
  const [staff, setStaff] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState(null);
  
  // Payroll periods state
  const [periods, setPeriods] = useState([]);
  const [periodDialogOpen, setPeriodDialogOpen] = useState(false);
  const [newPeriod, setNewPeriod] = useState({ year: new Date().getFullYear(), month: new Date().getMonth() + 1 });
  
  // Payroll status (which staff have payslips this month)
  const [payrollStatus, setPayrollStatus] = useState({});
  
  // Payslips state
  const [payslips, setPayslips] = useState([]);
  const [payslipDialogOpen, setPayslipDialogOpen] = useState(false);
  const [selectedStaffForPayslip, setSelectedStaffForPayslip] = useState(null);
  const [payslipForm, setPayslipForm] = useState({
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    overtime: 0,
    bonus: 0,
    commission: 0,
    incentives: 0,
    annual_leave_pay: 0,
    pcb: 0,
    cp38: 0,
    loan_deduction: 0,
    mid_month_advance: 0,
    salary_adjustment: 0,
    unpaid_leave: 0,
    other_deductions: 0,
    epf_employee: null,
    epf_employer: null,
    socso_employee: null,
    socso_employer: null,
    eis_employee: null,
    eis_employer: null
  });
  const [viewPayslip, setViewPayslip] = useState(null);
  const [printPayslip, setPrintPayslip] = useState(null);
  const [editPayslipOpen, setEditPayslipOpen] = useState(false);
  const [editPayslipData, setEditPayslipData] = useState(null);
  const [editSaving, setEditSaving] = useState(false);
  
  // Manual link state
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [linkingStaff, setLinkingStaff] = useState(null);
  const [selectedLinkUser, setSelectedLinkUser] = useState('');
  
  // Pay advice state
  const [payAdviceList, setPayAdviceList] = useState([]);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [payAdviceDialogOpen, setPayAdviceDialogOpen] = useState(false);
  const [payAdviceForm, setPayAdviceForm] = useState({
    user_id: '',
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1
  });
  const [viewPayAdvice, setViewPayAdvice] = useState(null);
  const [printPayAdvice, setPrintPayAdvice] = useState(null);
  // Unlock Pay Advice Dialog state
  const [unlockPayAdviceDialog, setUnlockPayAdviceDialog] = useState({ open: false, id: null, reason: '' });
  
  // Statutory rates upload state
  const [statutoryRates, setStatutoryRates] = useState({ epf: [], socso: [], eis: [] });
  const fileInputRef = useRef(null);
  const [uploadRateType, setUploadRateType] = useState('epf');
  
  const [formData, setFormData] = useState({
    user_id: '',
    employee_id: '',
    full_name: '',
    nric: '',
    designation: '',
    department: '',
    date_joined: '',
    date_of_birth: '',
    bank_name: '',
    bank_account: '',
    basic_salary: '',
    fixed_allowance: '',
    housing_allowance: '',
    transport_allowance: '',
    meal_allowance: '',
    phone_allowance: '',
    other_allowance: '',
    epf_number: '',
    socso_number: '',
    tax_number: '',
    employee_epf_rate: '11',
    employer_epf_rate: '13',
    is_active: true
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [staffRes, periodsRes, payslipsRes, adviceRes, usersRes, settingsRes, epfRates, socsoRates, eisRates, payrollStatusRes] = await Promise.all([
        axiosInstance.get('/hr/staff').catch(() => ({ data: [] })),
        axiosInstance.get('/hr/payroll-periods').catch(() => ({ data: [] })),
        axiosInstance.get('/hr/payslips').catch(() => ({ data: [] })),
        axiosInstance.get('/hr/pay-advice').catch(() => ({ data: [] })),
        axiosInstance.get('/hr/available-users').catch(() => ({ data: [] })),
        axiosInstance.get('/finance/company-settings').catch(() => ({ data: {} })),
        axiosInstance.get('/hr/statutory-rates?rate_type=epf').catch(() => ({ data: [] })),
        axiosInstance.get('/hr/statutory-rates?rate_type=socso').catch(() => ({ data: [] })),
        axiosInstance.get('/hr/statutory-rates?rate_type=eis').catch(() => ({ data: [] })),
        axiosInstance.get(`/hr/payroll-status?year=${new Date().getFullYear()}&month=${new Date().getMonth() + 1}`).catch(() => ({ data: {} }))
      ]);
      
      setStaff(staffRes.data);
      setPeriods(periodsRes.data);
      setPayslips(payslipsRes.data);
      setPayAdviceList(adviceRes.data);
      setAvailableUsers(usersRes.data);
      setCompanySettings(settingsRes.data);
      setStatutoryRates({
        epf: epfRates.data,
        socso: socsoRates.data,
        eis: eisRates.data
      });
      // Build payroll status map by staff_id
      const statusMap = {};
      (payrollStatusRes.data?.staff || []).forEach(s => {
        statusMap[s.staff_id] = s;
      });
      setPayrollStatus(statusMap);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Upload statutory rates
  const handleStatutoryUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('rate_type', uploadRateType);
    
    try {
      const response = await axiosInstance.post('/hr/statutory-rates/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(response.data.message);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload rates');
    }
    
    e.target.value = '';
  };

  // Download statutory template
  const handleDownloadTemplate = async (rateType) => {
    try {
      const response = await axiosInstance.get(`/hr/statutory-rates/templates/${rateType}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${rateType}_rates_template.xlsx`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error('Failed to download template');
    }
  };

  // Staff CRUD
  const handleSaveStaff = async () => {
    try {
      const payload = {
        ...formData,
        basic_salary: parseFloat(formData.basic_salary) || 0,
        fixed_allowance: parseFloat(formData.fixed_allowance) || 0,
        housing_allowance: parseFloat(formData.housing_allowance) || 0,
        transport_allowance: parseFloat(formData.transport_allowance) || 0,
        meal_allowance: parseFloat(formData.meal_allowance) || 0,
        phone_allowance: parseFloat(formData.phone_allowance) || 0,
        other_allowance: parseFloat(formData.other_allowance) || 0,
        employee_epf_rate: parseFloat(formData.employee_epf_rate) || 11,
        employer_epf_rate: parseFloat(formData.employer_epf_rate) || 13,
      };

      if (editingStaff) {
        await axiosInstance.put(`/hr/staff/${editingStaff.id}`, payload);
        toast.success('Staff updated successfully');
      } else {
        await axiosInstance.post('/hr/staff', payload);
        toast.success('Staff added successfully');
      }
      
      setDialogOpen(false);
      resetForm();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save staff');
    }
  };

  const handleEditStaff = (staffMember) => {
    setEditingStaff(staffMember);
    setFormData({
      user_id: staffMember.user_id || '',
      employee_id: staffMember.employee_id || '',
      full_name: staffMember.full_name || '',
      nric: staffMember.nric || '',
      designation: staffMember.designation || '',
      department: staffMember.department || '',
      date_joined: staffMember.date_joined || '',
      date_of_birth: staffMember.date_of_birth || '',
      bank_name: staffMember.bank_name || '',
      bank_account: staffMember.bank_account || '',
      basic_salary: staffMember.basic_salary?.toString() || '',
      fixed_allowance: staffMember.fixed_allowance?.toString() || '',
      housing_allowance: staffMember.housing_allowance?.toString() || '',
      transport_allowance: staffMember.transport_allowance?.toString() || '',
      meal_allowance: staffMember.meal_allowance?.toString() || '',
      phone_allowance: staffMember.phone_allowance?.toString() || '',
      other_allowance: staffMember.other_allowance?.toString() || '',
      epf_number: staffMember.epf_number || '',
      socso_number: staffMember.socso_number || '',
      tax_number: staffMember.tax_number || '',
      employee_epf_rate: staffMember.employee_epf_rate?.toString() || '11',
      employer_epf_rate: staffMember.employer_epf_rate?.toString() || '13',
      is_active: staffMember.is_active !== false
    });
    setDialogOpen(true);
  };

  const handleDeleteStaff = async (id) => {
    if (!window.confirm('Are you sure you want to delete this staff record?')) return;
    try {
      await axiosInstance.delete(`/hr/staff/${id}`);
      toast.success('Staff deleted');
      loadData();
    } catch (error) {
      toast.error('Failed to delete staff');
    }
  };

  const resetForm = () => {
    setEditingStaff(null);
    setFormData({
      user_id: '', employee_id: '', full_name: '', nric: '', designation: '', department: '',
      date_joined: '', date_of_birth: '', bank_name: '', bank_account: '', basic_salary: '',
      fixed_allowance: '', housing_allowance: '', transport_allowance: '', meal_allowance: '', phone_allowance: '',
      other_allowance: '', epf_number: '', socso_number: '', tax_number: '',
      employee_epf_rate: '11', employer_epf_rate: '13', is_active: true
    });
  };

  // Manual link staff to user
  const handleManualLink = async () => {
    if (!linkingStaff || !selectedLinkUser) return;
    try {
      await axiosInstance.post(`/hr/staff/${linkingStaff.id}/link-user/${selectedLinkUser}`);
      toast.success(`Linked ${linkingStaff.full_name} to user account`);
      setLinkDialogOpen(false);
      setLinkingStaff(null);
      setSelectedLinkUser('');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to link');
    }
  };

  const handleUnlinkStaff = async (staffMember) => {
    if (!confirm(`Unlink ${staffMember.full_name} from their user account?`)) return;
    try {
      await axiosInstance.delete(`/hr/staff/${staffMember.id}/unlink-user`);
      toast.success('User unlinked');
      loadData();
    } catch (error) {
      toast.error('Failed to unlink');
    }
  };

  // Payroll Period Management
  const handleCreatePeriod = async () => {
    try {
      await axiosInstance.post('/hr/payroll-periods', newPeriod);
      toast.success('Payroll period created');
      setPeriodDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create period');
    }
  };

  const handleClosePeriod = async (periodId) => {
    if (!window.confirm('Are you sure you want to close this period? All payslips will become read-only.')) return;
    try {
      await axiosInstance.put(`/hr/payroll-periods/${periodId}/close`);
      toast.success('Period closed successfully');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to close period');
    }
  };

  // Calculate statutory deductions for preview
  const calculateStatutory = (staffMember) => {
    const basic = staffMember?.basic_salary || 0;
    const gross = basic + (staffMember?.fixed_allowance || 0) + (staffMember?.housing_allowance || 0) + (staffMember?.transport_allowance || 0) + 
                  (staffMember?.meal_allowance || 0) + (staffMember?.phone_allowance || 0) + (staffMember?.other_allowance || 0);
    
    // Estimate age from NRIC
    const nric = staffMember?.nric || '';
    let age = 30;
    if (nric.length >= 6) {
      const yy = parseInt(nric.substring(0, 2));
      const currentYY = new Date().getFullYear() % 100;
      const year = yy > currentYY + 5 ? 1900 + yy : 2000 + yy;
      age = new Date().getFullYear() - year;
    }
    
    const isAbove60 = age >= 60;
    const epfEeRate = isAbove60 ? 0 : 11;
    const epfErRate = isAbove60 ? 4 : (basic <= 5000 ? 13 : 12);
    const socsoEeRate = isAbove60 ? 0 : 0.5;
    const socsoErRate = isAbove60 ? 1.25 : 1.75;
    const eisEeRate = isAbove60 ? 0 : 0.2;
    const eisErRate = isAbove60 ? 0 : 0.2;
    
    const cappedGross = Math.min(gross, 6000);
    
    return {
      epf_employee: Math.round(basic * epfEeRate) / 100,
      epf_employer: Math.round(basic * epfErRate) / 100,
      socso_employee: Math.round(cappedGross * socsoEeRate) / 100,
      socso_employer: Math.round(cappedGross * socsoErRate) / 100,
      eis_employee: Math.round(cappedGross * eisEeRate) / 100,
      eis_employer: Math.round(cappedGross * eisErRate) / 100,
      age
    };
  };

  // Payslip Generation
  const openPayslipDialog = (staffMember) => {
    setSelectedStaffForPayslip(staffMember);
    const calc = calculateStatutory(staffMember);
    setPayslipForm({
      year: new Date().getFullYear(),
      month: new Date().getMonth() + 1,
      overtime: 0, bonus: 0, commission: 0, incentives: 0, annual_leave_pay: 0,
      pcb: 0, cp38: 0, loan_deduction: 0, mid_month_advance: 0, salary_adjustment: 0, unpaid_leave: 0, other_deductions: 0,
      epf_employee: calc.epf_employee,
      epf_employer: calc.epf_employer,
      socso_employee: calc.socso_employee,
      socso_employer: calc.socso_employer,
      eis_employee: calc.eis_employee,
      eis_employer: calc.eis_employer
    });
    setPayslipDialogOpen(true);
  };

  const handleGeneratePayslip = async () => {
    try {
      const response = await axiosInstance.post('/hr/payslips/generate', {
        staff_id: selectedStaffForPayslip.id,
        ...payslipForm
      });
      toast.success(`Payslip generated! Nett Pay: RM ${response.data.nett_pay?.toLocaleString()}`);
      setPayslipDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate payslip');
    }
  };

  const handleDeletePayslip = async (id) => {
    if (!window.confirm('Delete this payslip and its journal entry?')) return;
    try {
      await axiosInstance.delete(`/hr/payslips/${id}`);
      toast.success('Payslip and journal entry deleted');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete payslip');
    }
  };

  const openEditPayslip = (ps) => {
    setEditPayslipData({ ...ps });
    setEditPayslipOpen(true);
  };

  const handleEditPayslipSave = async () => {
    if (!editPayslipData) return;
    setEditSaving(true);
    try {
      const payload = {
        basic_salary: editPayslipData.basic_salary,
        fixed_allowance: editPayslipData.fixed_allowance,
        housing_allowance: editPayslipData.housing_allowance,
        transport_allowance: editPayslipData.transport_allowance,
        meal_allowance: editPayslipData.meal_allowance,
        phone_allowance: editPayslipData.phone_allowance,
        other_allowance: editPayslipData.other_allowance,
        overtime: editPayslipData.overtime,
        bonus: editPayslipData.bonus,
        commission: editPayslipData.commission,
        incentives: editPayslipData.incentives,
        annual_leave_pay: editPayslipData.annual_leave_pay,
        other_earnings: editPayslipData.other_earnings,
        epf_employee: editPayslipData.epf_employee,
        epf_employer: editPayslipData.epf_employer,
        socso_employee: editPayslipData.socso_employee,
        socso_employer: editPayslipData.socso_employer,
        eis_employee: editPayslipData.eis_employee,
        eis_employer: editPayslipData.eis_employer,
        pcb: editPayslipData.pcb,
        cp38: editPayslipData.cp38,
        loan_deduction: editPayslipData.loan_deduction,
        mid_month_advance: editPayslipData.mid_month_advance,
        salary_adjustment: editPayslipData.salary_adjustment,
        unpaid_leave: editPayslipData.unpaid_leave,
        other_deductions: editPayslipData.other_deductions,
      };
      await axiosInstance.put(`/hr/payslips/${editPayslipData.id}`, payload);
      toast.success('Payslip updated and journal entry re-posted');
      setEditPayslipOpen(false);
      setEditPayslipData(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update payslip');
    }
    setEditSaving(false);
  };

  const handleRefreshStaffInfo = async () => {
    if (!editPayslipData) return;
    setEditSaving(true);
    try {
      await axiosInstance.put(`/hr/payslips/${editPayslipData.id}`, { refresh_staff_info: true });
      toast.success('Staff info refreshed on payslip');
      // Reload the payslip data
      const res = await axiosInstance.get(`/hr/payslips/${editPayslipData.id}`);
      setEditPayslipData(res.data);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to refresh staff info');
    }
    setEditSaving(false);
  };

  // Pay Advice
  const handleGeneratePayAdvice = async () => {
    try {
      const response = await axiosInstance.post('/hr/pay-advice/generate', payAdviceForm);
      toast.success(`Pay advice generated! Total: RM ${response.data.total_amount?.toLocaleString()}`);
      setPayAdviceDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate pay advice');
    }
  };

  const handleDeletePayAdvice = async (id) => {
    if (!window.confirm('Delete this pay advice?')) return;
    try {
      await axiosInstance.delete(`/hr/pay-advice/${id}`);
      toast.success('Pay advice deleted');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete');
    }
  };

  const handleBulkGeneratePayAdvice = async () => {
    try {
      const response = await axiosInstance.post(`/hr/pay-advice/bulk-generate?year=${payAdviceForm.year}&month=${payAdviceForm.month}`);
      toast.success(`Generated ${response.data.generated} pay advice (${response.data.skipped} skipped)`);
      if (response.data.generated === 0 && response.data.skipped === 0) {
        toast.info(response.data.message || 'No sessions found for this training period');
      }
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to bulk generate');
    }
  };

  const handleDebugPayAdvice = async () => {
    try {
      const response = await axiosInstance.get(`/hr/pay-advice/debug/${payAdviceForm.year}/${payAdviceForm.month}`);
      const d = response.data;
      const msg = `Payment: ${d.payment_month} | Training: ${d.training_month}\nSessions found: ${d.sessions_found}\nWorkers: ${d.workers.total_unique} (T:${d.workers.trainers} C:${d.workers.coordinators} M:${d.workers.marketers})\nExisting pay advice: ${d.existing_pay_advice.by_payment_month}\nDate errors: ${d.date_parse_errors.length}`;
      if (d.sessions_found === 0) {
        const dates = d.all_session_dates.map(s => `${s.name}: ${s.start_date}`).join('\n');
        alert(`No sessions for training month ${d.training_month}.\n\n${msg}\n\nAll session dates:\n${dates}`);
      } else {
        const sessions = d.sessions.map(s => `${s.name} (${s.start_date})`).join('\n');
        alert(`${msg}\n\nMatched sessions:\n${sessions}`);
      }
    } catch (error) {
      toast.error('Debug failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleBulkLockPayAdvice = async () => {
    if (!window.confirm(`Lock all pay advice for ${getMonthName(payAdviceForm.month)} ${payAdviceForm.year}? Staff will be able to view their pay advice once locked.`)) return;
    try {
      const response = await axiosInstance.post(`/hr/pay-advice/bulk-lock?year=${payAdviceForm.year}&month=${payAdviceForm.month}`);
      toast.success(`Locked ${response.data.message}`);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to bulk lock');
    }
  };

  const handleLockPayAdvice = async (id) => {
    try {
      await axiosInstance.post(`/hr/pay-advice/${id}/lock`);
      toast.success('Pay advice locked');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to lock');
    }
  };

  const handleUnlockPayAdvice = (id) => {
    // Open dialog instead of using window.prompt
    setUnlockPayAdviceDialog({ open: true, id, reason: '' });
  };

  const confirmUnlockPayAdvice = async () => {
    const { id, reason } = unlockPayAdviceDialog;
    if (!reason || reason.trim().length < 5) {
      toast.error('Reason must be at least 5 characters');
      return;
    }
    try {
      await axiosInstance.post(`/hr/pay-advice/${id}/unlock?reason=${encodeURIComponent(reason)}`);
      toast.success('Pay advice unlocked');
      setUnlockPayAdviceDialog({ open: false, id: null, reason: '' });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unlock');
    }
  };

  const calculateTotalAllowances = (s) => {
    return (s.fixed_allowance || 0) + (s.housing_allowance || 0) + (s.transport_allowance || 0) + 
           (s.meal_allowance || 0) + (s.phone_allowance || 0) + (s.other_allowance || 0);
  };

  const filteredStaff = staff.filter(s => 
    s.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.employee_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getMonthName = (month) => {
    return new Date(2000, month - 1).toLocaleString('default', { month: 'long' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4 flex flex-wrap gap-1 h-auto w-full justify-start bg-gray-100 p-2 rounded-lg">
          <TabsTrigger value="staff" className="flex-shrink-0">Staff</TabsTrigger>
          <TabsTrigger value="periods" className="flex-shrink-0">Periods</TabsTrigger>
          <TabsTrigger value="payslips" className="flex-shrink-0">Payslips</TabsTrigger>
          <TabsTrigger value="pay-advice" className="flex-shrink-0">Pay Advice</TabsTrigger>
          <TabsTrigger value="ea-forms" className="flex-shrink-0">EA Forms</TabsTrigger>
          <TabsTrigger value="rates" className="flex-shrink-0">Rates</TabsTrigger>
        </TabsList>

        {/* Staff Management Tab */}
        <TabsContent value="staff">
          {/* Payroll status summary for current month */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg flex flex-wrap items-center gap-3 text-sm" data-testid="payroll-status-summary">
            <span className="font-medium text-gray-700">
              {new Date().toLocaleString('en', { month: 'long', year: 'numeric' })} Payroll:
            </span>
            <Badge className="bg-green-100 text-green-800">
              {Object.values(payrollStatus).filter(s => s.has_payslip).length} Paid
            </Badge>
            <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-300">
              {Object.values(payrollStatus).filter(s => !s.has_payslip).length} Unpaid
            </Badge>
            <Button 
              variant="outline" 
              size="sm" 
              className="ml-auto text-xs"
              data-testid="auto-link-users-btn"
              onClick={async () => {
                try {
                  const res = await axiosInstance.post('/hr/staff/auto-link-users');
                  toast.success(res.data.message);
                  loadData();
                } catch (err) {
                  toast.error(err.response?.data?.detail || 'Failed to auto-link');
                }
              }}
            >
              <Link className="w-3 h-3 mr-1" /> Auto-link Users
            </Button>
          </div>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search staff..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button onClick={() => { resetForm(); setDialogOpen(true); }} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" /> Add Staff
            </Button>
          </div>

          <div className="grid gap-4">
            {filteredStaff.length === 0 ? (
              <Card className="p-8 text-center text-gray-500">
                <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No staff records found</p>
              </Card>
            ) : (
              filteredStaff.map((s) => (
                <Card key={s.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex gap-4">
                        <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                          <span className="text-blue-600 font-bold text-lg">{s.full_name?.charAt(0) || '?'}</span>
                        </div>
                        <div>
                          <h3 className="font-semibold text-lg">{s.full_name}</h3>
                          <p className="text-sm text-gray-500">{s.designation || 'No designation'}</p>
                          <div className="flex gap-2 mt-1">
                            <Badge variant="outline">{s.employee_id || 'No ID'}</Badge>
                            <Badge variant="outline" className="bg-blue-50">{s.department || 'No dept'}</Badge>
                            {payrollStatus[s.id]?.has_payslip ? (
                              <Badge className="bg-green-100 text-green-800 border-green-300" data-testid={`payroll-paid-${s.id}`}>
                                Paid
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-300" data-testid={`payroll-unpaid-${s.id}`}>
                                Unpaid
                              </Badge>
                            )}
                            {!s.user_id ? (
                              <button
                                onClick={() => { setLinkingStaff(s); setSelectedLinkUser(''); setLinkDialogOpen(true); }}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-300 hover:bg-yellow-100 cursor-pointer transition-colors"
                                data-testid={`link-staff-${s.id}`}
                              >
                                <Link className="w-3 h-3" />
                                Link user
                              </button>
                            ) : (
                              <button
                                onClick={() => handleUnlinkStaff(s)}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-300 hover:bg-red-50 hover:text-red-700 hover:border-red-300 cursor-pointer transition-colors"
                                data-testid={`unlink-staff-${s.id}`}
                              >
                                <Link className="w-3 h-3" />
                                Linked
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-500">Basic Salary</div>
                        <div className="text-xl font-bold text-green-600">
                          RM {(s.basic_salary || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-gray-400">+ RM {calculateTotalAllowances(s).toLocaleString()} allowances</div>
                      </div>
                    </div>
                    <div className="mt-4 pt-4 border-t flex justify-between items-center">
                      <div className="flex gap-4 text-sm text-gray-500">
                        <span>EPF: {s.epf_number || 'N/A'}</span>
                        <span>SOCSO: {s.socso_number || 'N/A'}</span>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => openPayslipDialog(s)}>
                          <FileText className="w-4 h-4 mr-1" /> Generate Payslip
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleEditStaff(s)}>
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDeleteStaff(s.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        {/* Payroll Periods Tab */}
        <TabsContent value="periods">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Payroll Periods</h3>
            <Button onClick={() => setPeriodDialogOpen(true)} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" /> New Period
            </Button>
          </div>
          
          <div className="grid gap-3">
            {periods.length === 0 ? (
              <Card className="p-8 text-center text-gray-500">
                <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No payroll periods created yet</p>
              </Card>
            ) : (
              periods.map((p) => (
                <Card key={p.id} className={`${p.status === 'closed' ? 'bg-gray-50' : ''}`}>
                  <CardContent className="p-4 flex justify-between items-center">
                    <div>
                      <h4 className="font-semibold">{getMonthName(p.month)} {p.year}</h4>
                      <p className="text-sm text-gray-500">Period: {p.period_name}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge className={p.status === 'closed' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}>
                        {p.status === 'closed' ? <Lock className="w-3 h-3 mr-1" /> : <Unlock className="w-3 h-3 mr-1" />}
                        {p.status}
                      </Badge>
                      {p.status === 'open' && (
                        <Button size="sm" variant="destructive" onClick={() => handleClosePeriod(p.id)}>
                          <Lock className="w-4 h-4 mr-1" /> Close Period
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        {/* Payslips Tab */}
        <TabsContent value="payslips">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Generated Payslips</h3>
            <Button onClick={loadData} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" /> Refresh
            </Button>
          </div>
          
          <div className="grid gap-3">
            {payslips.length === 0 ? (
              <Card className="p-8 text-center text-gray-500">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No payslips generated yet</p>
              </Card>
            ) : (
              payslips.map((ps) => (
                <Card key={ps.id} className={ps.is_locked ? 'bg-gray-50' : ''}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <h4 className="font-semibold">{ps.full_name}</h4>
                        <p className="text-sm text-gray-500">{ps.designation} • {getMonthName(ps.month)} {ps.year}</p>
                        <div className="flex gap-2 mt-1">
                          <Badge variant="outline">Gross: RM {ps.gross_salary?.toLocaleString()}</Badge>
                          <Badge className="bg-green-100 text-green-700">Nett: RM {ps.nett_pay?.toLocaleString()}</Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {ps.is_locked && <Lock className="w-4 h-4 text-gray-400" />}
                        <Button size="sm" variant="outline" onClick={() => setViewPayslip(ps)} data-testid={`view-payslip-${ps.id}`}>
                          <Eye className="w-4 h-4 mr-1" /> View
                        </Button>
                        {!ps.is_locked && (
                          <Button size="sm" variant="outline" onClick={() => openEditPayslip(ps)} data-testid={`edit-payslip-${ps.id}`}>
                            <Edit className="w-4 h-4 mr-1" /> Edit
                          </Button>
                        )}
                        {!ps.is_locked && (
                          <Button size="sm" variant="destructive" onClick={() => handleDeletePayslip(ps.id)} data-testid={`delete-payslip-${ps.id}`}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        {/* Pay Advice Tab */}
        <TabsContent value="pay-advice">
          <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
            <div>
              <h3 className="text-lg font-semibold">Pay Advice (Session Workers)</h3>
              <p className="text-sm text-gray-500">Generate and manage pay advice for trainers, coordinators, and marketing</p>
            </div>
            <div className="flex gap-2 flex-wrap">
              {/* Period Selector */}
              <Select value={payAdviceForm.month?.toString()} onValueChange={(v) => setPayAdviceForm({ ...payAdviceForm, month: parseInt(v) })}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="Month" />
                </SelectTrigger>
                <SelectContent>
                  {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => (
                    <SelectItem key={m} value={m.toString()}>{getMonthName(m)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={payAdviceForm.year?.toString()} onValueChange={(v) => setPayAdviceForm({ ...payAdviceForm, year: parseInt(v) })}>
                <SelectTrigger className="w-[100px]">
                  <SelectValue placeholder="Year" />
                </SelectTrigger>
                <SelectContent>
                  {[2026, 2025, 2024].map(y => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={handleBulkGeneratePayAdvice} className="bg-green-600 hover:bg-green-700">
                <RefreshCw className="w-4 h-4 mr-2" /> Bulk Generate
              </Button>
              <Button onClick={handleDebugPayAdvice} variant="outline" size="sm" className="text-xs">
                Diagnose
              </Button>
              <Button onClick={handleBulkLockPayAdvice} variant="outline" className="border-orange-300 text-orange-600">
                <Lock className="w-4 h-4 mr-2" /> Lock All
              </Button>
              <Button onClick={() => setPayAdviceDialogOpen(true)} className="bg-blue-600 hover:bg-blue-700">
                <Plus className="w-4 h-4 mr-2" /> Individual
              </Button>
            </div>
          </div>
          
          {/* Filter by period */}
          <div className="mb-4">
            <p className="text-sm text-gray-600">
              Showing: <span className="font-medium">{getMonthName(payAdviceForm.month)} {payAdviceForm.year}</span>
              {' • '}{payAdviceList.filter(pa => pa.year === payAdviceForm.year && pa.month === payAdviceForm.month).length} records
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Training month: {getMonthName(payAdviceForm.month === 1 ? 12 : payAdviceForm.month - 1)} {payAdviceForm.month === 1 ? payAdviceForm.year - 1 : payAdviceForm.year}
              {' '}(sessions that ran in the previous month)
            </p>
          </div>
          
          <div className="grid gap-3">
            {payAdviceList.filter(pa => pa.year === payAdviceForm.year && pa.month === payAdviceForm.month).length === 0 ? (
              <Card className="p-8 text-center text-gray-500">
                <DollarSign className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No pay advice for {getMonthName(payAdviceForm.month)} {payAdviceForm.year}</p>
                <p className="text-sm mt-2">Click &quot;Bulk Generate&quot; to create pay advice for all session workers</p>
              </Card>
            ) : (
              payAdviceList.filter(pa => pa.year === payAdviceForm.year && pa.month === payAdviceForm.month).map((pa) => (
                <Card key={pa.id} className={pa.is_locked ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center flex-wrap gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold">{pa.full_name}</h4>
                          {pa.is_locked ? (
                            <Badge className="bg-green-100 text-green-700"><Lock className="w-3 h-3 mr-1" /> Locked</Badge>
                          ) : (
                            <Badge className="bg-yellow-100 text-yellow-700">Draft</Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-500">
                          {pa.advice_number || `PA/${pa.year}/${pa.month}`} • {pa.total_sessions} session(s)
                        </p>
                        <div className="flex gap-2 mt-1">
                          <Badge className="bg-blue-100 text-blue-700">Gross: RM {pa.gross_amount?.toLocaleString()}</Badge>
                          <Badge className="bg-green-100 text-green-700">Nett: RM {pa.nett_amount?.toLocaleString()}</Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={() => setViewPayAdvice(pa)}>
                          <Eye className="w-4 h-4 mr-1" /> View
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setPrintPayAdvice(pa)}>
                          <Printer className="w-4 h-4 mr-1" /> Print
                        </Button>
                        {!pa.is_locked ? (
                          <>
                            <Button size="sm" variant="outline" className="text-green-600" onClick={() => handleLockPayAdvice(pa.id)}>
                              <Lock className="w-4 h-4" />
                            </Button>
                            <Button size="sm" variant="destructive" onClick={() => handleDeletePayAdvice(pa.id)}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </>
                        ) : (
                          <Button size="sm" variant="ghost" className="text-orange-600" onClick={() => handleUnlockPayAdvice(pa.id)}>
                            <Unlock className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        {/* EA Forms Tab */}
        <TabsContent value="ea-forms">
          <EAFormsTab staff={staff} companySettings={companySettings} />
        </TabsContent>

        {/* Statutory Rates Tab */}
        <TabsContent value="rates">
          <Card>
            <CardHeader>
              <CardTitle>Statutory Contribution Rates</CardTitle>
              <CardDescription>Upload EPF, SOCSO, and EIS rate tables from Excel</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
                <div className="w-full sm:w-auto">
                  <Label>Rate Type</Label>
                  <Select value={uploadRateType} onValueChange={setUploadRateType}>
                    <SelectTrigger className="w-full sm:w-40"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="epf">EPF</SelectItem>
                      <SelectItem value="socso">SOCSO</SelectItem>
                      <SelectItem value="eis">EIS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <input type="file" ref={fileInputRef} onChange={handleStatutoryUpload} accept=".xlsx,.xls" className="hidden" />
                <div className="flex gap-2 w-full sm:w-auto">
                  <Button onClick={() => fileInputRef.current?.click()} className="bg-blue-600 flex-1 sm:flex-none">
                    <Upload className="w-4 h-4 mr-2" /> Upload Excel
                  </Button>
                  <Button variant="outline" onClick={() => handleDownloadTemplate(uploadRateType)} className="flex-1 sm:flex-none">
                    <Download className="w-4 h-4 mr-2" /> Download Template
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {['epf', 'socso', 'eis'].map((type) => (
                  <div key={type} className="border rounded-lg p-4">
                    <h4 className="font-semibold text-center mb-2">{type.toUpperCase()} Rates</h4>
                    <Badge className="w-full justify-center mb-2">
                      {statutoryRates[type]?.length || 0} records uploaded
                    </Badge>
                    {statutoryRates[type]?.length > 0 && (
                      <div className="text-xs text-gray-500 max-h-32 overflow-y-auto">
                        <table className="w-full">
                          <thead><tr><th>Min</th><th>Max</th><th>EE</th><th>ER</th></tr></thead>
                          <tbody>
                            {statutoryRates[type].slice(0, 5).map((r, i) => (
                              <tr key={i}>
                                <td>{r.min_wages}</td>
                                <td>{r.max_wages}</td>
                                <td>{r.employee_amount}</td>
                                <td>{r.employer_amount}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {statutoryRates[type].length > 5 && <p className="text-center mt-1">... and {statutoryRates[type].length - 5} more</p>}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="bg-yellow-50 p-4 rounded-lg text-sm">
                <h4 className="font-semibold text-yellow-700 mb-2">Age-Based Rules (Auto-applied)</h4>
                <ul className="list-disc list-inside text-yellow-600 space-y-1">
                  <li><strong>Below 60:</strong> Standard EPF (11%/13%), SOCSO (0.5%/1.75%), EIS (0.2%/0.2%)</li>
                  <li><strong>60 and above:</strong> EPF (0%/4%), SOCSO (0%/1.25% employer only), EIS (0%/0%)</li>
                  <li>Age is calculated from NRIC (first 6 digits = YYMMDD)</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add/Edit Staff Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingStaff ? 'Edit Staff' : 'Add New Staff'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Employee ID *</Label>
                <Input value={formData.employee_id} onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })} />
              </div>
              <div>
                <Label>Full Name *</Label>
                <Input value={formData.full_name} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} />
              </div>
              <div>
                <Label>NRIC</Label>
                <Input value={formData.nric} onChange={(e) => setFormData({ ...formData, nric: e.target.value })} placeholder="e.g., 850315-10-1234" />
              </div>
              <div>
                <Label>Designation</Label>
                <Input value={formData.designation} onChange={(e) => setFormData({ ...formData, designation: e.target.value })} />
              </div>
              <div>
                <Label>Department</Label>
                <Input value={formData.department} onChange={(e) => setFormData({ ...formData, department: e.target.value })} />
              </div>
              <div>
                <Label>Date of Birth</Label>
                <Input type="date" value={formData.date_of_birth} onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })} />
              </div>
              <div>
                <Label>Date Joined</Label>
                <Input type="date" value={formData.date_joined} onChange={(e) => setFormData({ ...formData, date_joined: e.target.value })} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Bank Name</Label>
                <Input value={formData.bank_name} onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })} />
              </div>
              <div>
                <Label>Bank Account</Label>
                <Input value={formData.bank_account} onChange={(e) => setFormData({ ...formData, bank_account: e.target.value })} />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Basic Salary (RM) *</Label>
                <Input type="number" value={formData.basic_salary} onChange={(e) => setFormData({ ...formData, basic_salary: e.target.value })} />
              </div>
              <div>
                <Label>Fixed Allowance</Label>
                <Input type="number" value={formData.fixed_allowance} onChange={(e) => setFormData({ ...formData, fixed_allowance: e.target.value })} />
              </div>
              <div>
                <Label>Housing Allowance</Label>
                <Input type="number" value={formData.housing_allowance} onChange={(e) => setFormData({ ...formData, housing_allowance: e.target.value })} />
              </div>
              <div>
                <Label>Transport Allowance</Label>
                <Input type="number" value={formData.transport_allowance} onChange={(e) => setFormData({ ...formData, transport_allowance: e.target.value })} />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>EPF Number</Label>
                <Input value={formData.epf_number} onChange={(e) => setFormData({ ...formData, epf_number: e.target.value })} />
              </div>
              <div>
                <Label>SOCSO Number</Label>
                <Input value={formData.socso_number} onChange={(e) => setFormData({ ...formData, socso_number: e.target.value })} />
              </div>
              <div>
                <Label>Tax Number</Label>
                <Input value={formData.tax_number} onChange={(e) => setFormData({ ...formData, tax_number: e.target.value })} />
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveStaff} className="bg-blue-600 hover:bg-blue-700">
              <Save className="w-4 h-4 mr-2" /> {editingStaff ? 'Update' : 'Add Staff'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* New Period Dialog */}
      <Dialog open={periodDialogOpen} onOpenChange={setPeriodDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Payroll Period</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-4">
            <div>
              <Label>Year</Label>
              <Input type="number" value={newPeriod.year} onChange={(e) => setNewPeriod({ ...newPeriod, year: parseInt(e.target.value) })} />
            </div>
            <div>
              <Label>Month</Label>
              <Select value={newPeriod.month.toString()} onValueChange={(v) => setNewPeriod({ ...newPeriod, month: parseInt(v) })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[...Array(12)].map((_, i) => (
                    <SelectItem key={i+1} value={(i+1).toString()}>{getMonthName(i+1)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setPeriodDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreatePeriod} className="bg-blue-600">Create</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Generate Payslip Dialog */}
      <Dialog open={payslipDialogOpen} onOpenChange={setPayslipDialogOpen}>
        <DialogContent className="max-w-xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>Generate Payslip</DialogTitle>
            <DialogDescription>{selectedStaffForPayslip?.full_name} • NRIC: {selectedStaffForPayslip?.nric || 'N/A'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Year</Label>
                <Input type="number" value={payslipForm.year} onChange={(e) => setPayslipForm({ ...payslipForm, year: parseInt(e.target.value) })} />
              </div>
              <div>
                <Label>Month</Label>
                <Select value={payslipForm.month.toString()} onValueChange={(v) => setPayslipForm({ ...payslipForm, month: parseInt(v) })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {[...Array(12)].map((_, i) => (
                      <SelectItem key={i+1} value={(i+1).toString()}>{getMonthName(i+1)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="border-t pt-4">
              <h4 className="font-semibold text-sm text-green-600 mb-2">Variable Earnings (this month)</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Commission (RM)</Label>
                  <Input type="number" value={payslipForm.commission} onChange={(e) => setPayslipForm({ ...payslipForm, commission: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">Incentives (RM)</Label>
                  <Input type="number" value={payslipForm.incentives} onChange={(e) => setPayslipForm({ ...payslipForm, incentives: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">Bonus (RM)</Label>
                  <Input type="number" value={payslipForm.bonus} onChange={(e) => setPayslipForm({ ...payslipForm, bonus: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">Annual Leave Pay (RM)</Label>
                  <Input type="number" value={payslipForm.annual_leave_pay} onChange={(e) => setPayslipForm({ ...payslipForm, annual_leave_pay: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">Overtime (RM)</Label>
                  <Input type="number" value={payslipForm.overtime} onChange={(e) => setPayslipForm({ ...payslipForm, overtime: parseFloat(e.target.value) || 0 })} />
                </div>
              </div>
            </div>
            
            <div className="border-t pt-4">
              <h4 className="font-semibold text-sm text-blue-600 mb-2">Statutory Deductions (Editable)</h4>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label className="text-xs">EPF (Employee)</Label>
                  <Input type="number" step="0.01" value={payslipForm.epf_employee} onChange={(e) => setPayslipForm({ ...payslipForm, epf_employee: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">SOCSO (Employee)</Label>
                  <Input type="number" step="0.01" value={payslipForm.socso_employee} onChange={(e) => setPayslipForm({ ...payslipForm, socso_employee: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">EIS (Employee)</Label>
                  <Input type="number" step="0.01" value={payslipForm.eis_employee} onChange={(e) => setPayslipForm({ ...payslipForm, eis_employee: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">EPF (Employer)</Label>
                  <Input type="number" step="0.01" value={payslipForm.epf_employer} onChange={(e) => setPayslipForm({ ...payslipForm, epf_employer: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">SOCSO (Employer)</Label>
                  <Input type="number" step="0.01" value={payslipForm.socso_employer} onChange={(e) => setPayslipForm({ ...payslipForm, socso_employer: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">EIS (Employer)</Label>
                  <Input type="number" step="0.01" value={payslipForm.eis_employer} onChange={(e) => setPayslipForm({ ...payslipForm, eis_employer: parseFloat(e.target.value) || 0 })} />
                </div>
              </div>
            </div>
            
            <div className="border-t pt-4">
              <h4 className="font-semibold text-sm text-red-600 mb-2">Other Deductions</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">CP39 / PCB Tax (RM)</Label>
                  <Input type="number" value={payslipForm.pcb} onChange={(e) => setPayslipForm({ ...payslipForm, pcb: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">CP38 (RM)</Label>
                  <Input type="number" value={payslipForm.cp38} onChange={(e) => setPayslipForm({ ...payslipForm, cp38: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">Loan (RM)</Label>
                  <Input type="number" value={payslipForm.loan_deduction} onChange={(e) => setPayslipForm({ ...payslipForm, loan_deduction: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">Mid-Month Advance (RM)</Label>
                  <Input type="number" value={payslipForm.mid_month_advance} onChange={(e) => setPayslipForm({ ...payslipForm, mid_month_advance: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">Salary Adjustment (RM)</Label>
                  <Input type="number" value={payslipForm.salary_adjustment} onChange={(e) => setPayslipForm({ ...payslipForm, salary_adjustment: parseFloat(e.target.value) || 0 })} />
                </div>
                <div>
                  <Label className="text-xs">Unpaid Leave (RM)</Label>
                  <Input type="number" value={payslipForm.unpaid_leave} onChange={(e) => setPayslipForm({ ...payslipForm, unpaid_leave: parseFloat(e.target.value) || 0 })} />
                </div>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setPayslipDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleGeneratePayslip} className="bg-green-600 hover:bg-green-700">
              <Calculator className="w-4 h-4 mr-2" /> Generate Payslip
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* View Payslip Dialog */}
      <Dialog open={!!viewPayslip} onOpenChange={() => setViewPayslip(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex justify-between items-start">
              <div>
                <DialogTitle>Payslip - {viewPayslip?.full_name}</DialogTitle>
                <DialogDescription>{getMonthName(viewPayslip?.month)} {viewPayslip?.year}</DialogDescription>
              </div>
              <Button size="sm" onClick={() => { setPrintPayslip(viewPayslip); setViewPayslip(null); }}>
                <Printer className="w-4 h-4 mr-1" /> Print
              </Button>
            </div>
          </DialogHeader>
          {viewPayslip && (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3 p-4 bg-gray-50 rounded text-sm">
                <div><strong>Employee ID:</strong> {viewPayslip.employee_id}</div>
                <div><strong>Designation:</strong> {viewPayslip.designation || '-'}</div>
                <div><strong>Department:</strong> {viewPayslip.department || '-'}</div>
                <div><strong>EPF No:</strong> {viewPayslip.epf_number || '-'}</div>
                <div><strong>SOCSO No:</strong> {viewPayslip.socso_number || '-'}</div>
                <div><strong>Bank:</strong> {viewPayslip.bank_name || '-'} | Acc: {viewPayslip.bank_account || '-'}</div>
                <div><strong>Age:</strong> {viewPayslip.age} years</div>
              </div>
              
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h4 className="font-semibold mb-2 text-green-600">EARNINGS</h4>
                  <table className="w-full text-sm">
                    <tbody>
                      <tr><td>Basic Salary</td><td className="text-right">RM {viewPayslip.basic_salary?.toLocaleString()}</td></tr>
                      <tr><td>Allowances</td><td className="text-right">RM {viewPayslip.total_allowances?.toLocaleString()}</td></tr>
                      {viewPayslip.commission > 0 && <tr><td>Commission</td><td className="text-right">RM {viewPayslip.commission?.toLocaleString()}</td></tr>}
                      {viewPayslip.incentives > 0 && <tr><td>Incentives</td><td className="text-right">RM {viewPayslip.incentives?.toLocaleString()}</td></tr>}
                      {viewPayslip.bonus > 0 && <tr><td>Bonus</td><td className="text-right">RM {viewPayslip.bonus?.toLocaleString()}</td></tr>}
                      {viewPayslip.annual_leave_pay > 0 && <tr><td>Annual Leave Pay</td><td className="text-right">RM {viewPayslip.annual_leave_pay?.toLocaleString()}</td></tr>}
                      {viewPayslip.overtime > 0 && <tr><td>Overtime</td><td className="text-right">RM {viewPayslip.overtime?.toLocaleString()}</td></tr>}
                      <tr className="font-bold border-t"><td>GROSS</td><td className="text-right">RM {viewPayslip.gross_salary?.toLocaleString()}</td></tr>
                    </tbody>
                  </table>
                </div>
                <div>
                  <h4 className="font-semibold mb-2 text-red-600">DEDUCTIONS</h4>
                  <table className="w-full text-sm">
                    <tbody>
                      <tr><td>EPF ({viewPayslip.epf_employee_rate}%)</td><td className="text-right">RM {viewPayslip.epf_employee?.toLocaleString()}</td></tr>
                      <tr><td>SOCSO</td><td className="text-right">RM {viewPayslip.socso_employee?.toLocaleString()}</td></tr>
                      <tr><td>EIS/SIP</td><td className="text-right">RM {viewPayslip.eis_employee?.toLocaleString()}</td></tr>
                      {(viewPayslip.pcb > 0) && <tr><td>CP39 / PCB Tax</td><td className="text-right">RM {viewPayslip.pcb?.toLocaleString()}</td></tr>}
                      {(viewPayslip.cp38 > 0) && <tr><td>CP38</td><td className="text-right">RM {viewPayslip.cp38?.toLocaleString()}</td></tr>}
                      {(viewPayslip.loan_deduction > 0) && <tr><td>Loan</td><td className="text-right">RM {viewPayslip.loan_deduction?.toLocaleString()}</td></tr>}
                      {(viewPayslip.mid_month_advance > 0) && <tr><td>Mid-Month Advance</td><td className="text-right">RM {viewPayslip.mid_month_advance?.toLocaleString()}</td></tr>}
                      {(viewPayslip.salary_adjustment > 0) && <tr><td>Salary Adjustment</td><td className="text-right">RM {viewPayslip.salary_adjustment?.toLocaleString()}</td></tr>}
                      {(viewPayslip.unpaid_leave > 0) && <tr><td>Unpaid Leave</td><td className="text-right">RM {viewPayslip.unpaid_leave?.toLocaleString()}</td></tr>}
                      <tr className="font-bold border-t"><td>TOTAL</td><td className="text-right">RM {viewPayslip.total_deductions?.toLocaleString()}</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="p-4 bg-green-50 rounded text-center">
                <div className="text-sm text-gray-600">NETT PAY</div>
                <div className="text-3xl font-bold text-green-600">RM {viewPayslip.nett_pay?.toLocaleString()}</div>
              </div>

              <div className="p-4 bg-blue-50 rounded">
                <h4 className="font-semibold mb-2 text-blue-600">EMPLOYER CONTRIBUTIONS</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>EPF: RM {viewPayslip.epf_employer?.toLocaleString()}</div>
                  <div>SOCSO: RM {viewPayslip.socso_employer?.toLocaleString()}</div>
                  <div>EIS: RM {viewPayslip.eis_employer?.toLocaleString()}</div>
                </div>
              </div>

              <div className="p-4 bg-yellow-50 rounded">
                <h4 className="font-semibold mb-2 text-yellow-700">YEAR-TO-DATE</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>YTD Gross: RM {viewPayslip.ytd_gross?.toLocaleString()}</div>
                  <div>YTD EPF (Employee): RM {viewPayslip.ytd_epf_employee?.toLocaleString()}</div>
                  <div>YTD EPF (Employer): RM {viewPayslip.ytd_epf_employer?.toLocaleString()}</div>
                  <div>YTD PCB: RM {viewPayslip.ytd_pcb?.toLocaleString()}</div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Payslip Dialog */}
      <Dialog open={editPayslipOpen} onOpenChange={(open) => { if (!open) { setEditPayslipOpen(false); setEditPayslipData(null); } }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Payslip</DialogTitle>
            <DialogDescription>
              {editPayslipData?.full_name} — {editPayslipData ? `${getMonthName(editPayslipData.month)} ${editPayslipData.year}` : ''}
            </DialogDescription>
          </DialogHeader>
          {editPayslipData && (
            <div className="space-y-4 py-2">
              {/* Staff Info Section */}
              <div className="p-3 bg-gray-50 rounded border">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="font-semibold text-sm">Staff Info (snapshot)</h4>
                  <Button size="sm" variant="outline" onClick={handleRefreshStaffInfo} disabled={editSaving} data-testid="refresh-staff-info-btn">
                    <RefreshCw className={`w-3 h-3 mr-1 ${editSaving ? 'animate-spin' : ''}`} /> Refresh from Staff Record
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-1 text-xs text-gray-600">
                  <div>Position: <strong>{editPayslipData.designation || '-'}</strong></div>
                  <div>Department: <strong>{editPayslipData.department || '-'}</strong></div>
                  <div>EPF No: <strong>{editPayslipData.epf_number || '-'}</strong></div>
                  <div>SOCSO No: <strong>{editPayslipData.socso_number || '-'}</strong></div>
                  <div>Bank: <strong>{editPayslipData.bank_name || '-'}</strong></div>
                  <div>Account: <strong>{editPayslipData.bank_account || '-'}</strong></div>
                </div>
              </div>

              {/* Earnings */}
              <div>
                <h4 className="font-semibold text-sm text-green-600 mb-2">Earnings</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Basic Salary</Label>
                    <Input type="number" step="0.01" value={editPayslipData.basic_salary || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, basic_salary: parseFloat(e.target.value) || 0 })} data-testid="edit-basic-salary" />
                  </div>
                  <div>
                    <Label className="text-xs">Fixed Allowance</Label>
                    <Input type="number" step="0.01" value={editPayslipData.fixed_allowance || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, fixed_allowance: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Housing Allowance</Label>
                    <Input type="number" step="0.01" value={editPayslipData.housing_allowance || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, housing_allowance: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Transport Allowance</Label>
                    <Input type="number" step="0.01" value={editPayslipData.transport_allowance || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, transport_allowance: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Commission</Label>
                    <Input type="number" step="0.01" value={editPayslipData.commission || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, commission: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Incentives</Label>
                    <Input type="number" step="0.01" value={editPayslipData.incentives || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, incentives: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Bonus</Label>
                    <Input type="number" step="0.01" value={editPayslipData.bonus || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, bonus: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Annual Leave Pay</Label>
                    <Input type="number" step="0.01" value={editPayslipData.annual_leave_pay || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, annual_leave_pay: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Overtime</Label>
                    <Input type="number" step="0.01" value={editPayslipData.overtime || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, overtime: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Other Earnings</Label>
                    <Input type="number" step="0.01" value={editPayslipData.other_earnings || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, other_earnings: parseFloat(e.target.value) || 0 })} />
                  </div>
                </div>
              </div>

              {/* Deductions */}
              <div>
                <h4 className="font-semibold text-sm text-red-600 mb-2">Deductions</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">EPF Employee</Label>
                    <Input type="number" step="0.01" value={editPayslipData.epf_employee || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, epf_employee: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">EPF Employer</Label>
                    <Input type="number" step="0.01" value={editPayslipData.epf_employer || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, epf_employer: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">SOCSO Employee</Label>
                    <Input type="number" step="0.01" value={editPayslipData.socso_employee || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, socso_employee: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">SOCSO Employer</Label>
                    <Input type="number" step="0.01" value={editPayslipData.socso_employer || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, socso_employer: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">EIS/SIP Employee</Label>
                    <Input type="number" step="0.01" value={editPayslipData.eis_employee || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, eis_employee: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">EIS/SIP Employer</Label>
                    <Input type="number" step="0.01" value={editPayslipData.eis_employer || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, eis_employer: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">CP39 / PCB Tax</Label>
                    <Input type="number" step="0.01" value={editPayslipData.pcb || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, pcb: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">CP38</Label>
                    <Input type="number" step="0.01" value={editPayslipData.cp38 || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, cp38: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Loan</Label>
                    <Input type="number" step="0.01" value={editPayslipData.loan_deduction || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, loan_deduction: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Mid-Month Advance</Label>
                    <Input type="number" step="0.01" value={editPayslipData.mid_month_advance || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, mid_month_advance: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Salary Adjustment</Label>
                    <Input type="number" step="0.01" value={editPayslipData.salary_adjustment || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, salary_adjustment: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Unpaid Leave</Label>
                    <Input type="number" step="0.01" value={editPayslipData.unpaid_leave || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, unpaid_leave: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <Label className="text-xs">Other Deductions</Label>
                    <Input type="number" step="0.01" value={editPayslipData.other_deductions || 0}
                      onChange={(e) => setEditPayslipData({ ...editPayslipData, other_deductions: parseFloat(e.target.value) || 0 })} />
                  </div>
                </div>
              </div>

              {/* Live calculation preview */}
              <div className="p-3 bg-green-50 rounded border border-green-200">
                <div className="flex justify-between text-sm">
                  <span>Gross Salary:</span>
                  <span className="font-semibold">RM {((editPayslipData.basic_salary || 0) + (editPayslipData.fixed_allowance || 0) + (editPayslipData.housing_allowance || 0) + (editPayslipData.transport_allowance || 0) + (editPayslipData.meal_allowance || 0) + (editPayslipData.phone_allowance || 0) + (editPayslipData.other_allowance || 0) + (editPayslipData.overtime || 0) + (editPayslipData.bonus || 0) + (editPayslipData.commission || 0) + (editPayslipData.incentives || 0) + (editPayslipData.annual_leave_pay || 0) + (editPayslipData.other_earnings || 0)).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between text-sm text-red-600">
                  <span>Total Deductions:</span>
                  <span>- RM {((editPayslipData.epf_employee || 0) + (editPayslipData.socso_employee || 0) + (editPayslipData.eis_employee || 0) + (editPayslipData.pcb || 0) + (editPayslipData.cp38 || 0) + (editPayslipData.loan_deduction || 0) + (editPayslipData.mid_month_advance || 0) + (editPayslipData.salary_adjustment || 0) + (editPayslipData.unpaid_leave || 0) + (editPayslipData.other_deductions || 0)).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between text-base font-bold text-green-700 border-t pt-1 mt-1">
                  <span>Nett Pay:</span>
                  <span>RM {(((editPayslipData.basic_salary || 0) + (editPayslipData.fixed_allowance || 0) + (editPayslipData.housing_allowance || 0) + (editPayslipData.transport_allowance || 0) + (editPayslipData.meal_allowance || 0) + (editPayslipData.phone_allowance || 0) + (editPayslipData.other_allowance || 0) + (editPayslipData.overtime || 0) + (editPayslipData.bonus || 0) + (editPayslipData.commission || 0) + (editPayslipData.incentives || 0) + (editPayslipData.annual_leave_pay || 0) + (editPayslipData.other_earnings || 0)) - ((editPayslipData.epf_employee || 0) + (editPayslipData.socso_employee || 0) + (editPayslipData.eis_employee || 0) + (editPayslipData.pcb || 0) + (editPayslipData.cp38 || 0) + (editPayslipData.loan_deduction || 0) + (editPayslipData.mid_month_advance || 0) + (editPayslipData.salary_adjustment || 0) + (editPayslipData.unpaid_leave || 0) + (editPayslipData.other_deductions || 0))).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span>
                </div>
              </div>

              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => { setEditPayslipOpen(false); setEditPayslipData(null); }}>Cancel</Button>
                <Button onClick={handleEditPayslipSave} disabled={editSaving} className="bg-blue-600 hover:bg-blue-700" data-testid="save-edit-payslip-btn">
                  {editSaving ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Save className="w-4 h-4 mr-1" />}
                  Save & Re-post Journal
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Generate Pay Advice Dialog */}
      <Dialog open={payAdviceDialogOpen} onOpenChange={setPayAdviceDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate Pay Advice</DialogTitle>
            <DialogDescription>For trainers/coordinators who worked on sessions</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Select Person</Label>
              <Select value={payAdviceForm.user_id} onValueChange={(v) => setPayAdviceForm({ ...payAdviceForm, user_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select a person" /></SelectTrigger>
                <SelectContent>
                  {staff.map((s) => (
                    <SelectItem key={s.user_id || s.id} value={s.user_id || s.id}>{s.full_name}</SelectItem>
                  ))}
                  {availableUsers.map((u) => (
                    <SelectItem key={u.id} value={u.id}>{u.full_name} ({u.role})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Year</Label>
                <Input type="number" value={payAdviceForm.year} onChange={(e) => setPayAdviceForm({ ...payAdviceForm, year: parseInt(e.target.value) })} />
              </div>
              <div>
                <Label>Month</Label>
                <Select value={payAdviceForm.month.toString()} onValueChange={(v) => setPayAdviceForm({ ...payAdviceForm, month: parseInt(v) })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {[...Array(12)].map((_, i) => (
                      <SelectItem key={i+1} value={(i+1).toString()}>{getMonthName(i+1)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setPayAdviceDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleGeneratePayAdvice} className="bg-green-600">Generate</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* View Pay Advice Dialog */}
      <Dialog open={!!viewPayAdvice} onOpenChange={() => setViewPayAdvice(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Pay Advice - {viewPayAdvice?.full_name}</DialogTitle>
            <DialogDescription>{getMonthName(viewPayAdvice?.month)} {viewPayAdvice?.year}</DialogDescription>
          </DialogHeader>
          {viewPayAdvice && (
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 rounded text-sm">
                <div><strong>IC:</strong> {viewPayAdvice.id_number}</div>
                <div><strong>Bank:</strong> {viewPayAdvice.bank_name} - {viewPayAdvice.bank_account}</div>
              </div>
              
              <table className="w-full text-sm border">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="p-2 text-left">Company</th>
                    <th className="p-2 text-left">Session</th>
                    <th className="p-2 text-left">Role</th>
                    <th className="p-2 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {viewPayAdvice.session_details?.map((sd, idx) => (
                    <tr key={idx} className="border-t">
                      <td className="p-2">{sd.company_name}</td>
                      <td className="p-2">{sd.session_name}</td>
                      <td className="p-2 capitalize">{sd.role}</td>
                      <td className="p-2 text-right">RM {sd.amount?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-green-50 font-bold">
                  <tr>
                    <td colSpan="3" className="p-2 text-right">TOTAL</td>
                    <td className="p-2 text-right">RM {viewPayAdvice.nett_amount?.toLocaleString()}</td>
                  </tr>
                </tfoot>
              </table>
              <div className="flex justify-end">
                <Button onClick={() => { setPrintPayAdvice(viewPayAdvice); setViewPayAdvice(null); }}>
                  <Printer className="w-4 h-4 mr-1" /> Print
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Print Payslip Modal */}
      {printPayslip && (
        <PayslipPrint 
          payslip={printPayslip} 
          companySettings={companySettings} 
          onClose={() => setPrintPayslip(null)} 
        />
      )}

      {/* Print Pay Advice Modal */}
      {printPayAdvice && (
        <PayAdvicePrint 
          payAdvice={printPayAdvice} 
          companySettings={companySettings} 
          onClose={() => setPrintPayAdvice(null)} 
        />
      )}

      {/* Unlock Pay Advice Dialog */}
      <Dialog open={unlockPayAdviceDialog.open} onOpenChange={(open) => setUnlockPayAdviceDialog({ ...unlockPayAdviceDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Unlock Pay Advice</DialogTitle>
            <DialogDescription>
              Enter a reason to unlock this pay advice. This action will be logged for audit purposes.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="unlock-reason">Reason (required, minimum 5 characters)</Label>
            <textarea
              id="unlock-reason"
              className="w-full mt-2 p-3 border rounded-md min-h-[100px]"
              placeholder="Enter reason for unlocking this pay advice..."
              value={unlockPayAdviceDialog.reason}
              onChange={(e) => setUnlockPayAdviceDialog({ ...unlockPayAdviceDialog, reason: e.target.value })}
              data-testid="unlock-pay-advice-reason"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setUnlockPayAdviceDialog({ open: false, id: null, reason: '' })}>
              Cancel
            </Button>
            <Button 
              onClick={confirmUnlockPayAdvice} 
              disabled={unlockPayAdviceDialog.reason.trim().length < 5}
              data-testid="confirm-unlock-pay-advice"
            >
              Unlock Pay Advice
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Manual Link Dialog */}
      <Dialog open={linkDialogOpen} onOpenChange={setLinkDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Link Staff to User Account</DialogTitle>
            <DialogDescription>
              Select the user account for <strong>{linkingStaff?.full_name}</strong>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <Select value={selectedLinkUser} onValueChange={setSelectedLinkUser}>
              <SelectTrigger data-testid="link-user-select">
                <SelectValue placeholder="Select a user account..." />
              </SelectTrigger>
              <SelectContent>
                {availableUsers.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.full_name} ({u.email}) — {u.role}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setLinkDialogOpen(false)}>Cancel</Button>
              <Button size="sm" disabled={!selectedLinkUser} onClick={handleManualLink} data-testid="confirm-link-btn">
                <Link className="w-4 h-4 mr-1" /> Link
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HRModule;
