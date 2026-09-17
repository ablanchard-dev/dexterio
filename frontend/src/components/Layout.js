import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Target, TrendingUp, BookOpen, BarChart3, Shield, PlayCircle, Menu, X, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { backendBaseUrl, BACKEND_STATUS_EVENT } from '@/apiClient';

const Layout = ({ children }) => {
  const location = useLocation();
  const [backendDown, setBackendDown] = useState(false);
  useEffect(() => {
    const onStatus = (e) => setBackendDown(!e.detail.reachable);
    window.addEventListener(BACKEND_STATUS_EVENT, onStatus);
    return () => window.removeEventListener(BACKEND_STATUS_EVENT, onStatus);
  }, []);
  // Open by default on wide screens only: on a phone the panel covers the content.
  const [sidebarOpen, setSidebarOpen] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches
  );

  const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Setups', href: '/setups', icon: Target },
    { name: 'Performance', href: '/performance', icon: TrendingUp },
    { name: 'Trade Journal', href: '/journal', icon: BookOpen },
    { name: 'Market Analysis', href: '/market', icon: BarChart3 },
    { name: 'Risk Management', href: '/risk', icon: Shield },
    { name: 'Backtests', href: '/backtests', icon: PlayCircle },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 border-r border-gray-800 transform transition-transform duration-200 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-gray-800">
            <h1 className="text-xl font-bold">DexterioBOT</h1>
            <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(false)} className="lg:hidden">
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-800">
            <div className="text-xs text-gray-500">
              DexterioBOT v1.4
              <br />
              Paper Trading Mode
            </div>
          </div>
        </div>
      </div>

      {/* Mobile sidebar toggle */}
      {!sidebarOpen && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSidebarOpen(true)}
          className="fixed top-4 left-4 z-40 lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>
      )}

      {/* Main content */}
      <div className={`transition-all duration-200 ${sidebarOpen ? 'lg:pl-64' : ''}`}>
        <main className="min-h-screen pt-12 lg:pt-0">
          {backendDown && (
            <div role="alert" className="m-6 mb-0 flex items-start gap-3 rounded-lg border border-red-500 bg-red-900/20 p-4 text-sm">
              <AlertTriangle className="h-5 w-5 shrink-0 text-red-500" />
              <div>
                <div className="font-semibold text-red-400">Backend unreachable at {backendBaseUrl}</div>
                <div className="text-gray-400 mt-1">
                  Start it from <code>backend/</code> with <code>uvicorn server:app --port 8001</code>, or set{' '}
                  <code>REACT_APP_BACKEND_URL</code>. The page will fill in on its own once it answers.
                </div>
              </div>
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
