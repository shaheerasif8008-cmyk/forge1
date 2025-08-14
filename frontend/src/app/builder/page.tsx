"use client";

import { useState } from "react";

interface EmployeeFormData {
  name: string;
  role: string;
  department: string;
  description: string;
  model: string;
  temperature: number;
  maxTokens: number;
  isActive: boolean;
  skills: string[];
  constraints: string;
  goals: string;
  performanceMetrics: string[];
  personality: string;
  knowledgeBase: string;
  examples: string;
  autoStart: boolean;
  enableMemory: boolean;
  enableTools: boolean;
}
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { CheckCircle, Circle, ArrowRight, ArrowLeft, Save, Play } from "lucide-react";
import { toast } from "react-hot-toast";

const steps = [
  { id: 1, title: "Basic Info", description: "Employee name and role" },
  { id: 2, title: "Configuration", description: "AI model and settings" },
  { id: 3, title: "Personality", description: "Behavior and knowledge" },
  { id: 4, title: "Review", description: "Final review and deploy" },
];

export default function BuilderPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<EmployeeFormData>({
    // Step 1: Basic Info
    name: "",
    role: "",
    department: "",
    description: "",
    
    // Step 2: Configuration
    model: "gpt-4",
    temperature: 0.7,
    maxTokens: 4000,
    enableMemory: true,
    enableTools: false,
    
    // Step 3: Personality
    personality: "",
    knowledgeBase: "",
    constraints: "",
    examples: "",
    goals: "",
    skills: [],
    performanceMetrics: [],
    
    // Step 4: Review
    isActive: true,
    autoStart: false,
  });

  const [isDeploying, setIsDeploying] = useState(false);

  const nextStep = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleInputChange = (field: string, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleDeploy = async () => {
    setIsDeploying(true);
    // TODO: Implement API call to deploy employee
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
    setIsDeploying(false);
    toast.success("AI Employee deployed successfully!");
    // TODO: Redirect to employees page
  };

  const getStepIcon = (stepNumber: number) => {
    if (stepNumber < currentStep) {
      return <CheckCircle className="h-5 w-5 text-green-600" />;
    } else if (stepNumber === currentStep) {
      return <Circle className="h-5 w-5 text-blue-600" />;
    } else {
      return <Circle className="h-5 w-5 text-gray-400" />;
    }
  };

  const progress = (currentStep / steps.length) * 100;

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-semibold">Employee Builder</h1>
          <p className="text-muted-foreground">
            Create and configure your AI employees with our step-by-step wizard
          </p>
        </div>

        {/* Progress Bar */}
        <Card>
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Progress</span>
                <span className="text-sm text-muted-foreground">
                  Step {currentStep} of {steps.length}
                </span>
              </div>
              <Progress value={progress} className="h-2" />
              
              {/* Step Indicators */}
              <div className="flex items-center justify-between">
                {steps.map((step, index) => (
                  <div key={step.id} className="flex items-center space-x-2">
                    <div className="flex items-center space-x-2">
                      {getStepIcon(step.id)}
                      <div className="hidden sm:block">
                        <div className="text-sm font-medium">{step.title}</div>
                        <div className="text-xs text-muted-foreground">{step.description}</div>
                      </div>
                    </div>
                    {index < steps.length - 1 && (
                      <div className="hidden sm:block w-8 h-px bg-gray-300" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step Content */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <span>Step {currentStep}: {steps[currentStep - 1].title}</span>
              <Badge variant="outline">{steps[currentStep - 1].description}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {currentStep === 1 && (
              <BasicInfoStep 
                formData={formData} 
                onInputChange={handleInputChange} 
              />
            )}
            {currentStep === 2 && (
              <ConfigurationStep 
                formData={formData} 
                onInputChange={handleInputChange} 
              />
            )}
            {currentStep === 3 && (
              <PersonalityStep 
                formData={formData} 
                onInputChange={handleInputChange} 
              />
            )}
            {currentStep === 4 && (
              <ReviewStep 
                formData={formData} 
                onInputChange={handleInputChange} 
              />
            )}
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={prevStep}
            disabled={currentStep === 1}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Previous
          </Button>

          <div className="flex items-center space-x-2">
            {currentStep < steps.length ? (
              <Button onClick={nextStep}>
                Next
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Button 
                onClick={handleDeploy} 
                disabled={isDeploying}
                className="bg-green-600 hover:bg-green-700"
              >
                {isDeploying ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                    Deploying...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Deploy Employee
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

function BasicInfoStep({ formData, onInputChange }: { formData: EmployeeFormData; onInputChange: (field: string, value: string | number | boolean) => void }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label htmlFor="name">Employee Name *</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => onInputChange("name", e.target.value)}
            placeholder="e.g., Sales Assistant, Data Analyst"
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="role">Job Role *</Label>
          <Input
            id="role"
            value={formData.role}
            onChange={(e) => onInputChange("role", e.target.value)}
            placeholder="e.g., Customer Support, Data Processing"
            required
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="department">Department</Label>
        <Select value={formData.department} onValueChange={(value) => onInputChange("department", value)}>
          <SelectTrigger>
            <SelectValue placeholder="Select department" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="sales">Sales</SelectItem>
            <SelectItem value="support">Customer Support</SelectItem>
            <SelectItem value="marketing">Marketing</SelectItem>
            <SelectItem value="engineering">Engineering</SelectItem>
            <SelectItem value="hr">Human Resources</SelectItem>
            <SelectItem value="finance">Finance</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Job Description *</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => onInputChange("description", e.target.value)}
          placeholder="Describe the employee's responsibilities, goals, and expected outcomes..."
          rows={4}
          required
        />
      </div>
    </div>
  );
}

function ConfigurationStep({ formData, onInputChange }: { formData: EmployeeFormData; onInputChange: (field: string, value: string | number | boolean) => void }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label htmlFor="model">AI Model *</Label>
          <Select value={formData.model} onValueChange={(value) => onInputChange("model", value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="gpt-4">GPT-4 (Most Capable)</SelectItem>
              <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo (Fast & Cost-effective)</SelectItem>
              <SelectItem value="claude-3">Claude-3 (Analytical)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="temperature">Creativity Level</Label>
          <div className="space-y-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={formData.temperature}
              onChange={(e) => onInputChange("temperature", parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Focused ({formData.temperature})</span>
              <span>Creative</span>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="maxTokens">Max Response Length</Label>
        <Select value={formData.maxTokens.toString()} onValueChange={(value) => onInputChange("maxTokens", parseInt(value))}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1000">Short (1K tokens)</SelectItem>
            <SelectItem value="4000">Medium (4K tokens)</SelectItem>
            <SelectItem value="8000">Long (8K tokens)</SelectItem>
            <SelectItem value="16000">Very Long (16K tokens)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-4">
        <Label>Advanced Features</Label>
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Switch
              id="enableMemory"
              checked={formData.enableMemory}
              onCheckedChange={(checked) => onInputChange("enableMemory", checked)}
            />
            <Label htmlFor="enableMemory">Enable Memory (remembers conversation context)</Label>
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="enableTools"
              checked={formData.enableTools}
              onCheckedChange={(checked) => onInputChange("enableTools", checked)}
            />
            <Label htmlFor="enableTools">Enable Tools (web search, file access, etc.)</Label>
          </div>
        </div>
      </div>
    </div>
  );
}

function PersonalityStep({ formData, onInputChange }: { formData: EmployeeFormData; onInputChange: (field: string, value: string | number | boolean) => void }) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="personality">Personality & Communication Style</Label>
        <Textarea
          id="personality"
          value={formData.personality}
          onChange={(e) => onInputChange("personality", e.target.value)}
          placeholder="Describe how the employee should behave, communicate, and interact with users. For example: 'Professional but friendly, patient with explanations, uses clear language...'"
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="knowledgeBase">Knowledge Base & Expertise</Label>
        <Textarea
          id="knowledgeBase"
          value={formData.knowledgeBase}
          onChange={(e) => onInputChange("knowledgeBase", e.target.value)}
          placeholder="What specific knowledge, skills, or expertise should this employee have? Include industry knowledge, tools, processes, etc."
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="constraints">Constraints & Boundaries</Label>
        <Textarea
          id="constraints"
          value={formData.constraints}
          onChange={(e) => onInputChange("constraints", e.target.value)}
          placeholder="What should this employee NOT do? Any limitations, restrictions, or areas they should avoid?"
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="examples">Example Interactions</Label>
        <Textarea
          id="examples"
          value={formData.examples}
          onChange={(e) => onInputChange("examples", e.target.value)}
          placeholder="Provide a few examples of how this employee should respond to common scenarios or questions..."
          rows={3}
        />
      </div>
    </div>
  );
}

function ReviewStep({ formData, onInputChange }: { formData: EmployeeFormData; onInputChange: (field: string, value: string | number | boolean) => void }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h3 className="font-semibold">Basic Information</h3>
          <div className="space-y-2 text-sm">
            <div><span className="font-medium">Name:</span> {formData.name}</div>
            <div><span className="font-medium">Role:</span> {formData.role}</div>
            <div><span className="font-medium">Department:</span> {formData.department || "Not specified"}</div>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="font-semibold">Configuration</h3>
          <div className="space-y-2 text-sm">
            <div><span className="font-medium">Model:</span> {formData.model}</div>
            <div><span className="font-medium">Creativity:</span> {formData.temperature}</div>
            <div><span className="font-medium">Max Tokens:</span> {formData.maxTokens.toLocaleString()}</div>
          </div>
        </div>
      </div>

      <Separator />

      <div className="space-y-4">
        <h3 className="font-semibold">Personality & Behavior</h3>
        <div className="space-y-2 text-sm">
          <div><span className="font-medium">Communication Style:</span></div>
          <div className="text-muted-foreground pl-4">{formData.personality || "Not specified"}</div>
        </div>
      </div>

      <Separator />

      <div className="space-y-4">
        <h3 className="font-semibold">Deployment Options</h3>
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Switch
              id="isActive"
              checked={formData.isActive}
              onCheckedChange={(checked: boolean) => onInputChange("isActive", checked)}
            />
            <Label htmlFor="isActive">Start employee immediately after deployment</Label>
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="autoStart"
              checked={formData.autoStart}
              onCheckedChange={(checked: boolean) => onInputChange("autoStart", checked)}
            />
            <Label htmlFor="autoStart">Auto-start on system reboot</Label>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg">
        <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">Ready to Deploy!</h4>
        <p className="text-sm text-blue-800 dark:text-blue-200">
          Review the configuration above. Once deployed, your AI employee will be available to handle tasks 
          according to the specifications you&apos;ve defined.
        </p>
      </div>
    </div>
  );
}