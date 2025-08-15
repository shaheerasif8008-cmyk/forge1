import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { 
  Bot, 
  ChevronRight, 
  ChevronLeft,
  Check,
  Sparkles,
  Code,
  Database,
  MessageSquare,
  TrendingUp,
  Shield
} from 'lucide-react';
import { toast } from 'react-hot-toast';

const employeeTypes = [
  { id: 'sales', name: 'Sales Assistant', icon: TrendingUp, description: 'Automate outreach and lead generation' },
  { id: 'support', name: 'Customer Support', icon: MessageSquare, description: 'Handle customer inquiries 24/7' },
  { id: 'data', name: 'Data Analyst', icon: Database, description: 'Process and analyze business data' },
  { id: 'developer', name: 'Code Assistant', icon: Code, description: 'Help with development tasks' },
  { id: 'security', name: 'Security Monitor', icon: Shield, description: 'Monitor and respond to security events' },
  { id: 'custom', name: 'Custom AI', icon: Sparkles, description: 'Build your own specialized AI employee' },
];

export default function EmployeeBuilderPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    type: '',
    name: '',
    description: '',
    capabilities: [] as string[],
    integrations: [] as string[],
    schedule: 'always_on',
    maxTasks: 100,
    notificationPreferences: {
      email: true,
      slack: false,
      webhook: false,
    }
  });

  const steps = [
    { number: 1, title: 'Choose Type', description: 'Select employee type' },
    { number: 2, title: 'Basic Info', description: 'Name and description' },
    { number: 3, title: 'Capabilities', description: 'Configure abilities' },
    { number: 4, title: 'Integrations', description: 'Connect tools' },
    { number: 5, title: 'Review', description: 'Confirm settings' },
  ];

  const handleNext = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    try {
      // API call would go here
      toast.success('AI Employee created successfully!');
      navigate('/employees');
    } catch (error) {
      toast.error('Failed to create employee');
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {employeeTypes.map((type) => {
                const Icon = type.icon;
                return (
                  <Card
                    key={type.id}
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      formData.type === type.id ? 'ring-2 ring-primary' : ''
                    }`}
                    onClick={() => setFormData({ ...formData, type: type.id })}
                  >
                    <CardHeader>
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                          <Icon className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{type.name}</CardTitle>
                          <CardDescription>{type.description}</CardDescription>
                        </div>
                      </div>
                    </CardHeader>
                  </Card>
                );
              })}
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Employee Name</Label>
              <Input
                id="name"
                placeholder="e.g., Sales Assistant Pro"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <textarea
                id="description"
                className="w-full min-h-[100px] px-3 py-2 text-sm rounded-md border border-input bg-background"
                placeholder="Describe what this AI employee will do..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxTasks">Max Tasks per Day</Label>
              <Input
                id="maxTasks"
                type="number"
                value={formData.maxTasks}
                onChange={(e) => setFormData({ ...formData, maxTasks: parseInt(e.target.value) })}
              />
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Select the capabilities for your AI employee
            </p>
            <div className="space-y-2">
              {[
                'Email Communication',
                'Data Analysis',
                'Report Generation',
                'Task Automation',
                'Customer Interaction',
                'Content Creation',
                'Code Generation',
                'Monitoring & Alerts'
              ].map((capability) => (
                <label key={capability} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300"
                    checked={formData.capabilities.includes(capability)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFormData({
                          ...formData,
                          capabilities: [...formData.capabilities, capability]
                        });
                      } else {
                        setFormData({
                          ...formData,
                          capabilities: formData.capabilities.filter(c => c !== capability)
                        });
                      }
                    }}
                  />
                  <span className="text-sm">{capability}</span>
                </label>
              ))}
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Connect your AI employee to external tools
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {[
                { name: 'Slack', connected: false },
                { name: 'Microsoft Teams', connected: false },
                { name: 'Gmail', connected: true },
                { name: 'Salesforce', connected: false },
                { name: 'HubSpot', connected: false },
                { name: 'Jira', connected: false },
                { name: 'GitHub', connected: false },
                { name: 'Zapier', connected: false },
              ].map((integration) => (
                <Card key={integration.name} className="p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{integration.name}</span>
                    <Button
                      size="sm"
                      variant={integration.connected ? 'secondary' : 'outline'}
                    >
                      {integration.connected ? 'Connected' : 'Connect'}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        );

      case 5:
        return (
          <div className="space-y-4">
            <div className="bg-muted p-4 rounded-lg space-y-3">
              <h3 className="font-semibold">Review Your AI Employee</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Type:</span>
                  <span className="font-medium">
                    {employeeTypes.find(t => t.id === formData.type)?.name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Name:</span>
                  <span className="font-medium">{formData.name || 'Not set'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Tasks/Day:</span>
                  <span className="font-medium">{formData.maxTasks}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Capabilities:</span>
                  <span className="font-medium">{formData.capabilities.length} selected</span>
                </div>
              </div>
            </div>
            <div className="bg-primary/10 p-4 rounded-lg">
              <p className="text-sm">
                <strong>Note:</strong> Your AI employee will be created in paused state. 
                You can start it from the employees page after reviewing the configuration.
              </p>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create AI Employee</h1>
        <p className="text-muted-foreground">
          Build and configure your new AI workforce member
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between mb-8">
        {steps.map((step, index) => (
          <div key={step.number} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                  currentStep > step.number
                    ? 'bg-primary border-primary text-primary-foreground'
                    : currentStep === step.number
                    ? 'border-primary text-primary'
                    : 'border-gray-300 text-gray-500'
                }`}
              >
                {currentStep > step.number ? (
                  <Check className="h-5 w-5" />
                ) : (
                  step.number
                )}
              </div>
              <div className="mt-2 text-center">
                <p className="text-xs font-medium">{step.title}</p>
                <p className="text-xs text-muted-foreground hidden sm:block">
                  {step.description}
                </p>
              </div>
            </div>
            {index < steps.length - 1 && (
              <div
                className={`h-0.5 w-12 lg:w-24 mx-2 ${
                  currentStep > step.number ? 'bg-primary' : 'bg-gray-300'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <Card>
        <CardHeader>
          <CardTitle>{steps[currentStep - 1].title}</CardTitle>
          <CardDescription>{steps[currentStep - 1].description}</CardDescription>
        </CardHeader>
        <CardContent>{renderStepContent()}</CardContent>
      </Card>

      {/* Navigation Buttons */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={handleBack}
          disabled={currentStep === 1}
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        {currentStep === steps.length ? (
          <Button onClick={handleSubmit}>
            <Bot className="mr-2 h-4 w-4" />
            Create Employee
          </Button>
        ) : (
          <Button 
            onClick={handleNext}
            disabled={currentStep === 1 && !formData.type}
          >
            Next
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
