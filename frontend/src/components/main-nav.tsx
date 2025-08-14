"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";
import { Badge } from "@/components/ui/badge";
import { User, Settings, LogOut, Building2, TestTube, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: BarChart3,
  },
  {
    name: "AI Employees",
    href: "/employees",
    icon: Building2,
  },
  {
    name: "Employee Builder",
    href: "/builder",
    icon: Building2,
  },
  {
    name: "Billing",
    href: "/billing",
    icon: BarChart3,
  },
  {
    name: "Settings",
    href: "/settings",
    icon: Settings,
  },
];

const testingNavigation = [
  {
    name: "Test Suites",
    href: "/testing/suites",
    icon: TestTube,
  },
  {
    name: "Live Monitor",
    href: "/testing/monitor",
    icon: BarChart3,
  },
  {
    name: "Performance",
    href: "/testing/performance",
    icon: BarChart3,
  },
  {
    name: "Reports",
    href: "/testing/reports",
    icon: BarChart3,
  },
];

export function MainNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const isTestingApp = pathname.startsWith("/testing");

  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo and Brand */}
          <div className="flex items-center space-x-4">
            <Link href="/dashboard" className="flex items-center space-x-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">F1</span>
              </div>
              <span className="font-bold text-xl">Forge1</span>
              {isTestingApp && (
                <Badge variant="secondary" className="ml-2">
                  Testing
                </Badge>
              )}
            </Link>
          </div>

          {/* Navigation Menu */}
          <NavigationMenu className="hidden md:flex">
            <NavigationMenuList>
              {isTestingApp ? (
                // Testing App Navigation
                testingNavigation.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavigationMenuItem key={item.name}>
                      <Link href={item.href} legacyBehavior passHref>
                        <NavigationMenuLink
                          className={cn(
                            "group inline-flex h-10 w-max items-center justify-center rounded-md bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground focus:outline-none disabled:pointer-events-none disabled:opacity-50",
                            pathname === item.href
                              ? "bg-accent text-accent-foreground"
                              : ""
                          )}
                        >
                          <Icon className="mr-2 h-4 w-4" />
                          {item.name}
                        </NavigationMenuLink>
                      </Link>
                    </NavigationMenuItem>
                  );
                })
              ) : (
                // Client Portal Navigation
                navigation.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavigationMenuItem key={item.name}>
                      <Link href={item.href} legacyBehavior passHref>
                        <NavigationMenuLink
                          className={cn(
                            "group inline-flex h-10 w-max items-center justify-center rounded-md bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground focus:outline-none disabled:pointer-events-none disabled:opacity-50",
                            pathname === item.href
                              ? "bg-accent text-accent-foreground"
                              : ""
                          )}
                        >
                          <Icon className="mr-2 h-4 w-4" />
                          {item.name}
                        </NavigationMenuLink>
                      </Link>
                    </NavigationMenuItem>
                  );
                })
              )}
            </NavigationMenuList>
          </NavigationMenu>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {/* App Switcher */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  {isTestingApp ? "Testing App" : "Client Portal"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Switch Application</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/dashboard">
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Client Portal
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/testing/suites">
                    <TestTube className="mr-2 h-4 w-4" />
                    Testing App
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* User Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="relative">
                  <User className="mr-2 h-4 w-4" />
                  {user?.email || "User"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {user?.email || "User"}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.tenant_id || "Tenant"}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/settings">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </div>
  );
}