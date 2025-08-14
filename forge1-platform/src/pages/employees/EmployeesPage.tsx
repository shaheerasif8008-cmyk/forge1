import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  Bot,
  Plus,
  Search,
  Grid,
  List,
  Play,
  Pause,
  Settings,
  Trash2,
  MoreVertical,
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';

// Mock data - replace with API calls
const mockEmployees = [
  {
    id: '1',
    name: 'Sales Assistant AI',
    type: 'Sales',
    status: 'active',
    tasks_completed: 1234,
    success_rate: 95.2,
    last_active: '2 minutes ago',
    created: '2024-01-15',
    description: 'Handles outbound sales calls and email campaigns'
  },
  {
    id: '2',
    name: 'Customer Support AI',
    type: 'Support',
    status: 'active',
    tasks_completed: 892,
    success_rate: 98.1,
    last_active: '5 minutes ago',
    created: '2024-01-20',
    description: 'Responds to customer inquiries and resolves tickets'
  },
  {
    id: '3',
    name: 'Data Analyst AI',
    type: 'Analytics',
    status: 'paused',
    tasks_completed: 456,
    success_rate: 92.7,
    last_active: '1 hour ago',
    created: '2024-02-01',
    description: 'Analyzes business data and generates reports'
  },
  {
    id: '4',
    name: 'Marketing Automation AI',
    type: 'Marketing',
    status: 'error',
    tasks_completed: 678,
    success_rate: 88.5,
    last_active: '3 hours ago',
    created: '2024-02-10',
    description: 'Creates and manages marketing campaigns'
  },
];

export default function EmployeesPage() {
  const [employees, setEmployees] = useState(mockEmployees);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const filteredEmployees = employees.filter(emp =>
    emp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    emp.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'paused':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const handleToggleStatus = (id: string) => {
    setEmployees(prev => prev.map(emp => {
      if (emp.id === id) {
        return {
          ...emp,
          status: emp.status === 'active' ? 'paused' : 'active'
        };
      }
      return emp;
    }));
  };

  const EmployeeCard = ({ employee }: { employee: typeof mockEmployees[0] }) => (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div>
              <CardTitle className="text-lg">{employee.name}</CardTitle>
              <CardDescription>{employee.type}</CardDescription>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/employees/${employee.id}`}>
                  <Settings className="mr-2 h-4 w-4" />
                  Configure
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleToggleStatus(employee.id)}>
                {employee.status === 'active' ? (
                  <>
                    <Pause className="mr-2 h-4 w-4" />
                    Pause
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Start
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          {employee.description}
        </p>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <div className="flex items-center space-x-1">
              {getStatusIcon(employee.status)}
              <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(employee.status)}`}>
                {employee.status}
              </span>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Tasks Completed</span>
            <span className="text-sm font-medium">{employee.tasks_completed.toLocaleString()}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Success Rate</span>
            <span className="text-sm font-medium">{employee.success_rate}%</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Last Active</span>
            <span className="text-sm">{employee.last_active}</span>
          </div>
        </div>
        
        <div className="mt-4 pt-4 border-t flex gap-2">
          <Button variant="outline" size="sm" className="flex-1" asChild>
            <Link to={`/employees/${employee.id}`}>
              <Activity className="mr-2 h-4 w-4" />
              View Details
            </Link>
          </Button>
          <Button 
            size="sm" 
            className="flex-1"
            variant={employee.status === 'active' ? 'secondary' : 'default'}
            onClick={() => handleToggleStatus(employee.id)}
          >
            {employee.status === 'active' ? (
              <>
                <Pause className="mr-2 h-4 w-4" />
                Pause
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Start
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Employees</h1>
          <p className="text-muted-foreground">
            Manage and monitor your AI workforce
          </p>
        </div>
        <Button asChild>
          <Link to="/builder">
            <Plus className="mr-2 h-4 w-4" />
            New Employee
          </Link>
        </Button>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search employees..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            size="icon"
            onClick={() => setViewMode('grid')}
          >
            <Grid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="icon"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Employees Grid/List */}
      {viewMode === 'grid' ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredEmployees.map((employee) => (
            <EmployeeCard key={employee.id} employee={employee} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {filteredEmployees.map((employee) => (
                <div key={employee.id} className="p-4 hover:bg-accent/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <Bot className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{employee.name}</p>
                        <p className="text-sm text-muted-foreground">{employee.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm font-medium">{employee.tasks_completed.toLocaleString()} tasks</p>
                        <p className="text-sm text-muted-foreground">{employee.success_rate}% success</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(employee.status)}
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/employees/${employee.id}`}>
                            View
                          </Link>
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {filteredEmployees.length === 0 && (
        <Card className="text-center py-12">
          <CardContent>
            <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No employees found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery ? 'Try adjusting your search query' : 'Get started by creating your first AI employee'}
            </p>
            {!searchQuery && (
              <Button asChild>
                <Link to="/builder">
                  <Plus className="mr-2 h-4 w-4" />
                  Create Employee
                </Link>
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}