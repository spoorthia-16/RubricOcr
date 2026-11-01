import { useState } from "react";
import { NavLink } from "react-router-dom";
import { 
  FileSpreadsheet, 
  UploadCloud, 
  Eye, 
  LayoutDashboard, 
  Menu, 
  X, 
  Sparkles, 
  Activity 
} from "lucide-react";

function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { name: "Upload", to: "/", icon: UploadCloud },
    { name: "Review", to: "/review", icon: Eye },
    { name: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  ];

  return (
    <nav className="sticky top-0 z-50 backdrop-blur-xl bg-slate-950/80 border-b border-slate-800/80 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-20">

          {/* Logo & Brand */}
          <NavLink to="/" className="flex items-center gap-3.5 group">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-tr from-indigo-600 via-blue-600 to-cyan-400 p-0.5 shadow-lg shadow-indigo-500/25 group-hover:shadow-indigo-500/40 group-hover:scale-105 transition duration-300">
              <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
                <FileSpreadsheet className="w-5 h-5 text-indigo-400 group-hover:text-cyan-300 transition-colors" />
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-cyan-400 rounded-full animate-ping opacity-75" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-cyan-400 rounded-full" />
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl sm:text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-300 font-display">
                  Rubric<span className="text-indigo-400">OCR</span>
                </span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  <Sparkles className="w-2.5 h-2.5 text-indigo-400" />
                  PRO
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block tracking-wide">
                Automated Grid Extraction & Reconstruction
              </p>
            </div>
          </NavLink>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-2">
            <div className="flex items-center bg-slate-900/90 p-1.5 rounded-2xl border border-slate-800/80 shadow-inner">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 ${
                        isActive
                          ? "bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-md shadow-indigo-600/30 scale-100"
                          : "text-slate-300 hover:text-white hover:bg-slate-800/60"
                      }`
                    }
                  >
                    <Icon className="w-4 h-4" />
                    {item.name}
                  </NavLink>
                );
              })}
            </div>

            {/* Engine Status Pill */}
            <div className="ml-3 hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-950/40 border border-emerald-500/20 text-emerald-300 text-xs font-medium">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span>PaddleOCR v6 Online</span>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="flex md:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition focus:outline-none"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

        </div>
      </div>

      {/* Mobile menu dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-950/95 backdrop-blur-2xl px-4 pt-3 pb-5 space-y-2 animate-in slide-in-from-top-2 duration-200">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-xl text-base font-semibold transition ${
                    isActive
                      ? "bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-300 hover:bg-slate-900 hover:text-white"
                  }`
                }
              >
                <Icon className="w-5 h-5" />
                {item.name}
              </NavLink>
            );
          })}

          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 px-2">
            <div className="flex items-center gap-2 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              PaddleOCR Engine Active
            </div>
            <span>v2.0 Pro</span>
          </div>
        </div>
      )}
    </nav>
  );
}

export default Navbar;