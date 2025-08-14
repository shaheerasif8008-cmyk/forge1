"use client";

import { useState } from "react";

interface Employee {
  id: string;
  name: string;
  role: string;
  status: 'active' | 'paused' | 'error';
  tasksCompleted: number;
  avgResponseTime: string;
  lastActive: string;
  model: string;
  costPerDay: string;
}
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Plus, Play, Pause, Trash2, Edit, Eye, Download } from "lucide-react";
import { toast } from "react-hot-toast";

// Mock data - replace with real API calls
const mockEmployees: Employee[] = [
  {
    id: "emp_001",
    name: "Sales Assistant",
    role: "Customer Support",
    status: "active",
    tasksCompleted: 1247,
    avgResponseTime: "2.3s",
    lastActive: "2 minutes ago",
    model: "gpt-4",
    costPerDay: "$12.45",
  },
  {
    id: "emp_002",
    name: "Data Analyst",
    role: "Data Processing",
    status: "paused",
    tasksCompleted: 892,
    avgResponseTime: "5.1s",
    lastActive: "1 hour ago",
    model: "gpt-4",
    costPerDay: "$18.20",
  },
  {
    id: "emp_003",
    name: "Content Writer",
    role: "Content Creation",
    status: "active",
    tasksCompleted: 567,
    avgResponseTime: "8.7s",
    lastActive: "15 minutes ago",
    model: "gpt-4",
    costPerDay: "$15.80",
  },
];

export default function EmployeesPage() {
  const [employees, setEmployees] = useState(mockEmployees);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);

  const handleStatusToggle = (employeeId: string) => {
    setEmployees(prev => 
      prev.map(emp => 
        emp.id === employeeId 
          ? { ...emp, status: emp.status === 'active' ? 'paused' : 'active' }
          : emp
      )
    );
    toast.success("Employee status updated");
  };

  const handleDelete = (employeeId: string) => {
    setEmployees(prev => prev.filter(emp => emp.id !== employeeId));
    toast.success("Employee deleted");
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Active</Badge>;
      case 'paused':
        return <Badge variant="warning">Paused</Badge>;
      case 'error':
        return <Badge variant="destructive">Error</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold">AI Employees</h1>
            <p className="text-muted-foreground">
              Manage your AI workforce and monitor their performance
            </p>
          </div>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Employee
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px]">
              <DialogHeader>
                <DialogTitle>Create New AI Employee</DialogTitle>
                <DialogDescription>
                  Configure a new AI employee for your workforce
                </DialogDescription>
              </DialogHeader>
              <CreateEmployeeForm onSuccess={() => setIsCreateDialogOpen(false)} />
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-sm font-medium text-muted-foreground">Total Employees</div>
              <div className="text-2xl font-semibold">{employees.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-sm font-medium text-muted-foreground">Active</div>
              <div className="text-2xl font-semibold text-green-600">
                {employees.filter(e => e.status === 'active').length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-sm font-medium text-muted-foreground">Total Tasks</div>
              <div className="text-2xl font-semibold">
                {employees.reduce((sum, e) => sum + e.tasksCompleted, 0).toLocaleString()}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-sm font-medium text-muted-foreground">Daily Cost</div>
              <div className="text-2xl font-semibold">
                ${employees.reduce((sum, e) => sum + parseFloat(e.costPerDay.replace('$', '')), 0).toFixed(2)}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Employees Table */}
        <Card>
          <CardHeader>
            <CardTitle>Employee List</CardTitle>
            <CardDescription>
              View and manage all your AI employees
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Tasks Completed</TableHead>
                  <TableHead>Avg Response</TableHead>
                  <TableHead>Last Active</TableHead>
                  <TableHead>Daily Cost</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {employees.map((employee) => (
                  <TableRow key={employee.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{employee.name}</div>
                        <div className="text-sm text-muted-foreground">{employee.model}</div>
                      </div>
                    </TableCell>
                    <TableCell>{employee.role}</TableCell>
                    <TableCell>{getStatusBadge(employee.status)}</TableCell>
                    <TableCell>{employee.tasksCompleted.toLocaleString()}</TableCell>
                    <TableCell>{employee.avgResponseTime}</TableCell>
                    <TableCell>{employee.lastActive}</TableCell>
                    <TableCell>{employee.costPerDay}</TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleStatusToggle(employee.id)}
                        >
                          {employee.status === 'active' ? (
                            <Pause className="h-4 w-4" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingEmployee(employee);
                            setIsEditDialogOpen(true);
                          }}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(employee.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Edit Employee Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Edit AI Employee</DialogTitle>
              <DialogDescription>
                Update the configuration for {editingEmployee?.name}
              </DialogDescription>
            </DialogHeader>
            {editingEmployee && (
              <EditEmployeeForm 
                employee={editingEmployee} 
                onSuccess={() => setIsEditDialogOpen(false)}
              />
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AuthenticatedLayout>
  );
}

function CreateEmployeeForm({ onSuccess }: { onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    name: "",
    role: "",
    description: "",
    model: "gpt-4",
    isActive: true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement API call
    toast.success("Employee created successfully");
    onSuccess();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., Sales Assistant"
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="role">Role</Label>
          <Input
            id="role"
            value={formData.role}
            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            placeholder="e.g., Customer Support"
            required
          />
        </div>
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Describe the employee's responsibilities..."
          rows={3}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="model">AI Model</Label>
          <Select value={formData.model} onValueChange={(value) => setFormData({ ...formData, model: value })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="gpt-4">GPT-4</SelectItem>
              <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
              <SelectItem value="claude-3">Claude-3</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="isActive">Active Status</Label>
          <div className="flex items-center space-x-2">
            <Switch
              id="isActive"
              checked={formData.isActive}
              onCheckedChange={(checked: boolean) => setFormData({ ...formData, isActive: checked })}
            />
            <span className="text-sm">{formData.isActive ? "Active" : "Paused"}</span>
          </div>
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-4">
        <Button type="submit">Create Employee</Button>
      </div>
    </form>
  );
}

function EditEmployeeForm({ employee, onSuccess }: { employee: Employee; onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    name: employee.name,
    role: employee.role,
    description: "",
    model: employee.model,
    status: employee.status,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement API call
    toast.success("Employee updated successfully");
    onSuccess();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="edit-name">Name</Label>
          <Input
            id="edit-name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit-role">Role</Label>
          <Input
            id="edit-role"
            value={formData.role}
            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            required
          />
        </div>
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="edit-description">Description</Label>
        <Textarea
          id="edit-description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          rows={3}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="edit-model">AI Model</Label>
          <Select value={formData.model} onValueChange={(value) => setFormData({ ...formData, model: value })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="gpt-4">GPT-4</SelectItem>
              <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
              <SelectItem value="claude-3">Claude-3</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit-isActive">Active Status</Label>
          <div className="flex items-center space-x-2">
            <Switch
              id="edit-status"
              checked={formData.status === 'active'}
              onCheckedChange={(checked: boolean) => setFormData({ ...formData, status: checked ? 'active' : 'paused' })}
            />
            <span className="text-sm">{formData.status === 'active' ? "Active" : "Paused"}</span>
          </div>
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-4">
        <Button type="submit">Update Employee</Button>
      </div>
    </form>
  );
}