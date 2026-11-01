import { Routes, Route, useNavigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import Upload from "./pages/Upload";
import Review from "./pages/Review";
import Dashboard from "./pages/Dashboard";
import { ToastProvider } from "./components/Toast";
import { ArrowLeft, FileQuestion } from "lucide-react";

function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center p-4">
      <div className="glass-panel max-w-md w-full rounded-3xl p-8 text-center space-y-6 shadow-2xl border border-slate-800">
        <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
          <FileQuestion className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h1 className="text-5xl font-extrabold text-white font-display">404</h1>
          <h2 className="text-xl font-bold text-slate-200">Page Not Found</h2>
          <p className="text-sm text-slate-400">
            The page or view you are looking for does not exist in the Rubric OCR system.
          </p>
        </div>

        <button
          onClick={() => navigate("/")}
          className="w-full py-3 px-5 rounded-xl font-semibold text-white bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 shadow-lg shadow-indigo-600/30 transition flex items-center justify-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </button>
      </div>
    </div>
  );
}

function App() {
  return (
    <ToastProvider>
      <div className="min-h-screen flex flex-col bg-[#090d16] text-slate-100">
        <Navbar />

        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/review" element={<Review />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </ToastProvider>
  );
}

export default App;