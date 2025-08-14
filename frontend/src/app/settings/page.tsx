"use client";

import { useState } from "react";
import { AuthenticatedLayout } from "@/components/authenticated-layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { User, Bell, Shield, Palette, Globe, Database, Key } from "lucide-react";
import { toast } from "react-hot-toast";
import { useAuth } from "@/lib/auth";

export default function SettingsPage() {
  const { user } = useAuth();
  const [isSaving, setIsSaving] = useState(false);

  const [profileData, setProfileData] = useState({
    firstName: "John",
    lastName: "Doe",
    email: user?.email || "john.doe@example.com",
    company: "Acme Corp",
    phone: "+1 (555) 123-4567",
    timezone: "America/New_York",
    language: "en",
  });

  const [notificationSettings, setNotificationSettings] = useState({
    emailNotifications: true,
    pushNotifications: false,
    employeeAlerts: true,
    billingAlerts: true,
    securityAlerts: true,
    weeklyReports: false,
    dailyDigest: true,
  });

  const [securitySettings, setSecuritySettings] = useState({
    twoFactorAuth: false,
    sessionTimeout: 30,
    passwordExpiry: 90,
    loginNotifications: true,
    suspiciousActivityAlerts: true,
  });

  const [appSettings, setAppSettings] = useState({
    theme: "system",
    compactMode: false,
    autoRefresh: true,
    refreshInterval: 30,
    showTutorials: true,
    enableAnalytics: true,
  });

  const handleSave = async (section: string) => {
    setIsSaving(true);
    // TODO: Implement API call to save settings
    await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
    setIsSaving(false);
    toast.success(`${section} settings saved successfully!`);
  };

  const handleInputChange = (section: string, field: string, value: string | number | boolean) => {
    switch (section) {
      case 'profile':
        setProfileData(prev => ({ ...prev, [field]: value }));
        break;
      case 'notifications':
        setNotificationSettings(prev => ({ ...prev, [field]: value }));
        break;
      case 'security':
        setSecuritySettings(prev => ({ ...prev, [field]: value }));
        break;
      case 'app':
        setAppSettings(prev => ({ ...prev, [field]: value }));
        break;
    }
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-semibold">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account settings and preferences
          </p>
        </div>

        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="profile" className="flex items-center space-x-2">
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">Profile</span>
            </TabsTrigger>
            <TabsTrigger value="notifications" className="flex items-center space-x-2">
              <Bell className="h-4 w-4" />
              <span className="hidden sm:inline">Notifications</span>
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center space-x-2">
              <Shield className="h-4 w-4" />
              <span className="hidden sm:inline">Security</span>
            </TabsTrigger>
            <TabsTrigger value="app" className="flex items-center space-x-2">
              <Palette className="h-4 w-4" />
              <span className="hidden sm:inline">App</span>
            </TabsTrigger>
          </TabsList>

          {/* Profile Settings */}
          <TabsContent value="profile">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <User className="h-5 w-5" />
                  <span>Profile Information</span>
                </CardTitle>
                <CardDescription>
                  Update your personal information and contact details
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First Name</Label>
                    <Input
                      id="firstName"
                      value={profileData.firstName}
                      onChange={(e) => handleInputChange("profile", "firstName", e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input
                      id="lastName"
                      value={profileData.lastName}
                      onChange={(e) => handleInputChange("profile", "lastName", e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={profileData.email}
                      onChange={(e) => handleInputChange("profile", "email", e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="company">Company</Label>
                    <Input
                      id="company"
                      value={profileData.company}
                      onChange={(e) => handleInputChange("profile", "company", e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone Number</Label>
                    <Input
                      id="phone"
                      value={profileData.phone}
                      onChange={(e) => handleInputChange("profile", "phone", e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="timezone">Timezone</Label>
                    <Select value={profileData.timezone} onValueChange={(value) => handleInputChange("profile", "timezone", value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="America/New_York">Eastern Time (ET)</SelectItem>
                        <SelectItem value="America/Chicago">Central Time (CT)</SelectItem>
                        <SelectItem value="America/Denver">Mountain Time (MT)</SelectItem>
                        <SelectItem value="America/Los_Angeles">Pacific Time (PT)</SelectItem>
                        <SelectItem value="Europe/London">London (GMT)</SelectItem>
                        <SelectItem value="Europe/Paris">Paris (CET)</SelectItem>
                        <SelectItem value="Asia/Tokyo">Tokyo (JST)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="language">Language</Label>
                  <Select value={profileData.language} onValueChange={(value) => handleInputChange("profile", "language", value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="es">Spanish</SelectItem>
                      <SelectItem value="fr">French</SelectItem>
                      <SelectItem value="de">German</SelectItem>
                      <SelectItem value="ja">Japanese</SelectItem>
                      <SelectItem value="zh">Chinese</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                <div className="flex justify-end">
                  <Button 
                    onClick={() => handleSave("Profile")}
                    disabled={isSaving}
                  >
                    {isSaving ? "Saving..." : "Save Changes"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notification Settings */}
          <TabsContent value="notifications">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Bell className="h-5 w-5" />
                  <span>Notification Preferences</span>
                </CardTitle>
                <CardDescription>
                  Configure how and when you receive notifications
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <h3 className="font-medium">Email Notifications</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="emailNotifications">Email Notifications</Label>
                        <p className="text-sm text-muted-foreground">Receive notifications via email</p>
                      </div>
                                  <Switch
              id="emailNotifications"
              checked={notificationSettings.emailNotifications}
              onCheckedChange={(checked: boolean) => handleInputChange("notifications", "emailNotifications", checked)}
            />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="employeeAlerts">Employee Alerts</Label>
                        <p className="text-sm text-muted-foreground">Get notified about employee status changes</p>
                      </div>
                                  <Switch
              id="employeeAlerts"
              checked={notificationSettings.employeeAlerts}
              onCheckedChange={(checked: boolean) => handleInputChange("notifications", "employeeAlerts", checked)}
            />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="billingAlerts">Billing Alerts</Label>
                        <p className="text-sm text-muted-foreground">Receive billing and payment notifications</p>
                      </div>
                                  <Switch
              id="billingAlerts"
              checked={notificationSettings.billingAlerts}
              onCheckedChange={(checked: boolean) => handleInputChange("notifications", "billingAlerts", checked)}
            />
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="font-medium">Security & Reports</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="securityAlerts">Security Alerts</Label>
                        <p className="text-sm text-muted-foreground">Get notified about security events</p>
                      </div>
                                  <Switch
              id="securityAlerts"
              checked={notificationSettings.securityAlerts}
              onCheckedChange={(checked: boolean) => handleInputChange("notifications", "securityAlerts", checked)}
            />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="weeklyReports">Weekly Reports</Label>
                        <p className="text-sm text-muted-foreground">Receive weekly performance summaries</p>
                      </div>
                                  <Switch
              id="weeklyReports"
              checked={notificationSettings.weeklyReports}
              onCheckedChange={(checked: boolean) => handleInputChange("notifications", "weeklyReports", checked)}
            />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="dailyDigest">Daily Digest</Label>
                        <p className="text-sm text-muted-foreground">Get a daily summary of activities</p>
                      </div>
                                  <Switch
              id="dailyDigest"
              checked={notificationSettings.dailyDigest}
              onCheckedChange={(checked: boolean) => handleInputChange("notifications", "dailyDigest", checked)}
            />
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="flex justify-end">
                  <Button 
                    onClick={() => handleSave("Notification")}
                    disabled={isSaving}
                  >
                    {isSaving ? "Saving..." : "Save Changes"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Settings */}
          <TabsContent value="security">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="h-5 w-5" />
                  <span>Security Settings</span>
                </CardTitle>
                <CardDescription>
                  Manage your account security and authentication preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <h3 className="font-medium">Authentication</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="twoFactorAuth">Two-Factor Authentication</Label>
                        <p className="text-sm text-muted-foreground">Add an extra layer of security to your account</p>
                      </div>
                                  <Switch
              id="twoFactorAuth"
              checked={securitySettings.twoFactorAuth}
              onCheckedChange={(checked: boolean) => handleInputChange("security", "twoFactorAuth", checked)}
            />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="sessionTimeout">Session Timeout (minutes)</Label>
                      <Select value={securitySettings.sessionTimeout.toString()} onValueChange={(value) => handleInputChange("security", "sessionTimeout", parseInt(value))}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="15">15 minutes</SelectItem>
                          <SelectItem value="30">30 minutes</SelectItem>
                          <SelectItem value="60">1 hour</SelectItem>
                          <SelectItem value="120">2 hours</SelectItem>
                          <SelectItem value="480">8 hours</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="font-medium">Alerts & Monitoring</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="loginNotifications">Login Notifications</Label>
                        <p className="text-sm text-muted-foreground">Get notified about new login attempts</p>
                      </div>
                                  <Switch
              id="loginNotifications"
              checked={securitySettings.loginNotifications}
              onCheckedChange={(checked: boolean) => handleInputChange("security", "loginNotifications", checked)}
            />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="suspiciousActivityAlerts">Suspicious Activity Alerts</Label>
                        <p className="text-sm text-muted-foreground">Receive alerts about unusual account activity</p>
                      </div>
                                  <Switch
              id="suspiciousActivityAlerts"
              checked={securitySettings.suspiciousActivityAlerts}
              onCheckedChange={(checked: boolean) => handleInputChange("security", "suspiciousActivityAlerts", checked)}
            />
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="flex justify-end">
                  <Button 
                    onClick={() => handleSave("Security")}
                    disabled={isSaving}
                  >
                    {isSaving ? "Saving..." : "Save Changes"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* App Settings */}
          <TabsContent value="app">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Palette className="h-5 w-5" />
                  <span>Application Preferences</span>
                </CardTitle>
                <CardDescription>
                  Customize your Forge1 experience and interface
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <h3 className="font-medium">Appearance</h3>
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor="theme">Theme</Label>
                      <Select value={appSettings.theme} onValueChange={(value) => handleInputChange("app", "theme", value)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="light">Light</SelectItem>
                          <SelectItem value="dark">Dark</SelectItem>
                          <SelectItem value="system">System</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="compactMode">Compact Mode</Label>
                        <p className="text-sm text-muted-foreground">Use a more compact interface layout</p>
                      </div>
                                  <Switch
              id="compactMode"
              checked={appSettings.compactMode}
              onCheckedChange={(checked: boolean) => handleInputChange("app", "compactMode", checked)}
            />
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="font-medium">Data & Updates</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="autoRefresh">Auto-refresh Data</Label>
                        <p className="text-sm text-muted-foreground">Automatically refresh dashboard data</p>
                      </div>
                                  <Switch
              id="autoRefresh"
              checked={appSettings.autoRefresh}
              onCheckedChange={(checked: boolean) => handleInputChange("app", "autoRefresh", checked)}
            />
                    </div>
                    {appSettings.autoRefresh && (
                      <div className="space-y-2">
                        <Label htmlFor="refreshInterval">Refresh Interval (seconds)</Label>
                        <Select value={appSettings.refreshInterval.toString()} onValueChange={(value) => handleInputChange("app", "refreshInterval", parseInt(value))}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="15">15 seconds</SelectItem>
                            <SelectItem value="30">30 seconds</SelectItem>
                            <SelectItem value="60">1 minute</SelectItem>
                            <SelectItem value="300">5 minutes</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="showTutorials">Show Tutorials</Label>
                        <p className="text-sm text-muted-foreground">Display helpful tips and tutorials</p>
                      </div>
                                  <Switch
              id="showTutorials"
              checked={appSettings.showTutorials}
              onCheckedChange={(checked: boolean) => handleInputChange("app", "showTutorials", checked)}
            />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="enableAnalytics">Enable Analytics</Label>
                        <p className="text-sm text-muted-foreground">Help improve Forge1 with usage analytics</p>
                      </div>
                                  <Switch
              id="enableAnalytics"
              checked={appSettings.enableAnalytics}
              onCheckedChange={(checked: boolean) => handleInputChange("app", "enableAnalytics", checked)}
            />
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="flex justify-end">
                  <Button 
                    onClick={() => handleSave("Application")}
                    disabled={isSaving}
                  >
                    {isSaving ? "Saving..." : "Save Changes"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AuthenticatedLayout>
  );
}