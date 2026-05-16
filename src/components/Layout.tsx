import { Link, useLocation } from "react-router";
import { useState } from "react";
import {
  MessageSquare,
  BarChart3,
  GitFork,
  BookOpen,
  Settings,
  Brain,
  Menu,
  X,
  ChevronRight,
} from "lucide-react";

const navItems = [
  { path: "/", label: "Chat", icon: MessageSquare },
  { path: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { path: "/knowledge-graph", label: "Knowledge Graph", icon: GitFork },
  { path: "/curriculum", label: "Curriculum", icon: BookOpen },
  { path: "/settings", label: "Settings", icon: Settings },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 border-r border-border bg-card/80 backdrop-blur-sm
          transform transition-transform duration-200 ease-in-out lg:transform-none
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
          flex flex-col`}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-border">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/15">
            <Brain className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-foreground">HF-Agent</h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Multi-Agent Tutor</p>
          </div>
          <button
            className="ml-auto lg:hidden p-1 rounded-md hover:bg-accent"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                  ${isActive
                    ? "bg-primary/10 text-primary ring-1 ring-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                  }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-primary" : ""}`} />
                <span>{item.label}</span>
                {isActive && <ChevronRight className="w-3 h-3 ml-auto" />}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border">
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Ollama Connected</span>
          </div>
          <p className="text-[10px] text-muted-foreground/60 mt-1">Danish HF Curriculum v1.0</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile top bar */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-border bg-card/50">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-accent"
          >
            <Menu className="w-5 h-5" />
          </button>
          <span className="text-sm font-semibold">HF-Agent</span>
        </div>

        {/* Page content */}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
