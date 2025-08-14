"use client";

import { useState } from "react";
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { CreditCard, Download, Calendar, TrendingUp, AlertCircle, CheckCircle } from "lucide-react";
import { toast } from "react-hot-toast";

// Mock data - replace with real API calls
const mockSubscription = {
  plan: "Professional",
  status: "active",
  nextBilling: "2024-02-15",
  amount: 299,
  currency: "USD",
  interval: "monthly",
  features: [
    "Up to 50 AI Employees",
    "Advanced Analytics",
    "Priority Support",
    "Custom Integrations",
    "API Access",
  ],
  usage: {
    employees: 12,
    maxEmployees: 50,
    tokensThisMonth: 1250000,
    projectedCost: 450,
  },
};

const mockInvoices = [
  {
    id: "inv_001",
    date: "2024-01-15",
    amount: 299,
    status: "paid",
    description: "Professional Plan - January 2024",
  },
  {
    id: "inv_002",
    date: "2023-12-15",
    amount: 299,
    status: "paid",
    description: "Professional Plan - December 2023",
  },
  {
    id: "inv_003",
    date: "2023-11-15",
    amount: 299,
    status: "paid",
    description: "Professional Plan - November 2023",
  },
];

const plans = [
  {
    name: "Starter",
    price: 99,
    interval: "monthly",
    features: [
      "Up to 10 AI Employees",
      "Basic Analytics",
      "Email Support",
      "Standard Integrations",
    ],
    popular: false,
  },
  {
    name: "Professional",
    price: 299,
    interval: "monthly",
    features: [
      "Up to 50 AI Employees",
      "Advanced Analytics",
      "Priority Support",
      "Custom Integrations",
      "API Access",
    ],
    popular: true,
  },
  {
    name: "Enterprise",
    price: 999,
    interval: "monthly",
    features: [
      "Unlimited AI Employees",
      "Enterprise Analytics",
      "24/7 Support",
      "Custom Development",
      "Dedicated Account Manager",
      "SLA Guarantees",
    ],
    popular: false,
  },
];

export default function BillingPage() {
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [isUpgrading, setIsUpgrading] = useState(false);

  const handleUpgrade = async (planName: string) => {
    setIsUpgrading(true);
    // TODO: Implement Stripe checkout
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
    setIsUpgrading(false);
    toast.success(`Successfully upgraded to ${planName} plan!`);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Active</Badge>;
      case 'past_due':
        return <Badge variant="warning">Past Due</Badge>;
      case 'canceled':
        return <Badge variant="destructive">Canceled</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getInvoiceStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'pending':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-semibold">Billing & Subscription</h1>
          <p className="text-muted-foreground">
            Manage your subscription, view usage, and update payment methods
          </p>
        </div>

        {/* Current Plan */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <CreditCard className="h-5 w-5" />
              <span>Current Plan</span>
            </CardTitle>
            <CardDescription>
              You are currently on the {mockSubscription.plan} plan
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <div className="text-sm font-medium text-muted-foreground">Plan</div>
                <div className="text-2xl font-semibold">{mockSubscription.plan}</div>
                <div className="text-sm text-muted-foreground">
                  ${mockSubscription.amount}/{mockSubscription.interval}
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium text-muted-foreground">Status</div>
                <div>{getStatusBadge(mockSubscription.status)}</div>
                <div className="text-sm text-muted-foreground">
                  Next billing: {mockSubscription.nextBilling}
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-sm font-medium text-muted-foreground">Usage</div>
                <div className="text-2xl font-semibold">
                  {mockSubscription.usage.employees}/{mockSubscription.usage.maxEmployees}
                </div>
                <div className="text-sm text-muted-foreground">AI Employees</div>
              </div>
            </div>

            <Separator className="my-6" />

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Plan Features</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {mockSubscription.features.map((feature, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Usage & Costs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5" />
                <span>Usage This Month</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>AI Employees</span>
                  <span>{mockSubscription.usage.employees}/{mockSubscription.usage.maxEmployees}</span>
                </div>
                <Progress 
                  value={(mockSubscription.usage.employees / mockSubscription.usage.maxEmployees) * 100} 
                  className="h-2" 
                />
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Tokens Used</span>
                  <span>{mockSubscription.usage.tokensThisMonth.toLocaleString()}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  Estimated cost: ${mockSubscription.usage.projectedCost}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Calendar className="h-5 w-5" />
                <span>Billing History</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockInvoices.slice(0, 3).map((invoice) => (
                  <div key={invoice.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      {getInvoiceStatusIcon(invoice.status)}
                      <div>
                        <div className="text-sm font-medium">{invoice.description}</div>
                        <div className="text-xs text-muted-foreground">{invoice.date}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">${invoice.amount}</span>
                      <Button variant="ghost" size="sm">
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              <Button variant="outline" className="w-full mt-4">
                View All Invoices
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Plan Comparison */}
        <Card>
          <CardHeader>
            <CardTitle>Available Plans</CardTitle>
            <CardDescription>
              Choose the plan that best fits your needs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {plans.map((plan) => (
                <div
                  key={plan.name}
                  className={`relative p-6 border rounded-lg ${
                    plan.popular ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' : 'border-border'
                  }`}
                >
                  {plan.popular && (
                    <Badge className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      Most Popular
                    </Badge>
                  )}
                  
                  <div className="text-center space-y-4">
                    <div>
                      <h3 className="text-xl font-semibold">{plan.name}</h3>
                      <div className="text-3xl font-bold">
                        ${plan.price}
                        <span className="text-sm font-normal text-muted-foreground">/{plan.interval}</span>
                      </div>
                    </div>

                    <div className="space-y-2 text-left">
                      {plan.features.map((feature, index) => (
                        <div key={index} className="flex items-center space-x-2">
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <span className="text-sm">{feature}</span>
                        </div>
                      ))}
                    </div>

                    <Button
                      className={`w-full ${
                        plan.name === mockSubscription.plan
                          ? 'bg-gray-500 cursor-not-allowed'
                          : ''
                      }`}
                      disabled={plan.name === mockSubscription.plan || isUpgrading}
                      onClick={() => handleUpgrade(plan.name)}
                    >
                      {plan.name === mockSubscription.plan
                        ? 'Current Plan'
                        : isUpgrading
                        ? 'Upgrading...'
                        : 'Upgrade'}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Payment Methods */}
        <Card>
          <CardHeader>
            <CardTitle>Payment Methods</CardTitle>
            <CardDescription>
              Manage your payment methods and billing information
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center space-x-3">
                  <CreditCard className="h-5 w-5" />
                  <div>
                    <div className="font-medium">•••• •••• •••• 4242</div>
                    <div className="text-sm text-muted-foreground">Expires 12/25</div>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Edit
                </Button>
              </div>
              
              <Button variant="outline">
                <CreditCard className="mr-2 h-4 w-4" />
                Add Payment Method
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AuthenticatedLayout>
  );
}