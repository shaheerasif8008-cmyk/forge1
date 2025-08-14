import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import {
  LayoutDashboard,
  Users,
  CreditCard,
  Settings,
  TestTube,
  Activity,
  FileText,
  LogOut,
  X,
  Bot,
  ChevronLeft,
} from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { Button } from '../ui/button';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  isTestingApp?: boolean;
}

export default function Sidebar({ isOpen, onToggle, isTestingApp = false }: SidebarProps) {
  const location = useLocation();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);

  const clientPortalLinks = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/employees', label: 'AI Employees', icon: Bot },
    { href: '/builder', label: 'Employee Builder', icon: Users },
    { href: '/billing', label: 'Billing', icon: CreditCard },
    { href: '/settings', label: 'Settings', icon: Settings },
  ];

  const testingAppLinks = [
    { href: '/testing', label: 'Test Suites', icon: TestTube },
    { href: '/testing/monitor', label: 'Live Monitor', icon: Activity },
    { href: '/testing/performance', label: 'Performance', icon: Activity },
    { href: '/testing/reports', label: 'Reports', icon: FileText },
  ];

  const links = isTestingApp ? testingAppLinks : clientPortalLinks;

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-50 h-full bg-card border-r transition-all duration-300",
          isOpen ? "w-64" : "w-16",
          "lg:relative lg:z-30"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b">
            <Link
              to="/"
              className={cn(
                "flex items-center space-x-2 font-bold text-xl",
                !isOpen && "lg:justify-center"
              )}
            >
              {isOpen ? (
                <>
                  <Bot className="h-6 w-6 text-primary" />
                  <span>{isTestingApp ? 'Forge1 Testing' : 'Forge1'}</span>
                </>
              ) : (
                <Bot className="h-6 w-6 text-primary" />
              )}
            </Link>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="lg:hidden"
            >
              <X className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="hidden lg:flex"
            >
              <ChevronLeft className={cn("h-4 w-4 transition-transform", !isOpen && "rotate-180")} />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4">
            <ul className="space-y-2">
              {links.map((link) => {
                const Icon = link.icon;
                const isActive = location.pathname === link.href;
                return (
                  <li key={link.href}>
                    <Link
                      to={link.href}
                      className={cn(
                        "flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-accent",
                        !isOpen && "lg:justify-center"
                      )}
                    >
                      <Icon className="h-5 w-5 flex-shrink-0" />
                      {isOpen && <span>{link.label}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>

            {/* Switch between apps */}
            {isOpen && (
              <div className="mt-8 pt-8 border-t">
                <Link
                  to={isTestingApp ? '/dashboard' : '/testing'}
                  className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-accent"
                >
                  {isTestingApp ? (
                    <>
                      <LayoutDashboard className="h-5 w-5" />
                      <span>Client Portal</span>
                    </>
                  ) : (
                    <>
                      <TestTube className="h-5 w-5" />
                      <span>Testing App</span>
                    </>
                  )}
                </Link>
              </div>
            )}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t">
            {isOpen && user && (
              <div className="mb-4">
                <p className="text-sm font-medium truncate">{user.full_name}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
            )}
            <Button
              variant="ghost"
              className={cn("w-full", !isOpen && "lg:px-0")}
              onClick={() => logout()}
            >
              <LogOut className="h-5 w-5" />
              {isOpen && <span className="ml-3">Logout</span>}
            </Button>
          </div>
        </div>
      </aside>
    </>
  );
}