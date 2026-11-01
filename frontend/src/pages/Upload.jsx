import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Sparkles, 
  ArrowRight, 
  FileSpreadsheet, 
  Cpu, 
  ScanLine, 
  Layers, 
  CheckCircle2, 
  ShieldCheck, 
  AlertCircle,
  Clock,
  HelpCircle
} from "lucide-react";
import FileUpload from "../components/FileUpload";
import API from "../services/api";
import { useToast } from "../components/Toast";

function Upload() {
  const navigate = useNavigate();
  const toast = useToast();

  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeStep, setActiveStep] = useState(0);

  const pipelineSteps = [
    { title: "Document Ingestion", desc: "Validating PDF & checking orientation" },
    { title: "Deep OCR Analysis", desc: "Running PaddleOCR text & coordinate extraction" },
    { title: "Grid Reconstruction", desc: "Detecting rows, columns & merged cells" },
    { title: "Excel Compilation", desc: "Building formatted .xlsx spreadsheet" },
  ];

  // Simulated progress steps while backend processes
  useEffect(() => {
    let interval;
    if (isProcessing) {
      setActiveStep(0);
      interval = setInterval(() => {
        setActiveStep((prev) => (prev < 3 ? prev + 1 : prev));
      }, 3500);
    } else {
      setActiveStep(0);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  const uploadPDF = async () => {
    if (!selectedFile) {
      toast.error("Please choose a PDF document first.");
      return;
    }

    setIsProcessing(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await API.post("/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      if (response.data.success) {
        toast.success("Rubric processed successfully!");
        navigate("/review", {
          state: {
            gridData: response.data.grid_data,
            excelUrl: response.data.excel_url,
            fileName: selectedFile.name,
          },
        });
      } else {
        toast.error(response.data.reason || "Error processing the rubric.");
      }
    } catch (error) {
      console.error(error);
      const errorMsg =
        error.response?.data?.reason ||
        error.response?.data?.message ||
        "Pipeline failed to extract table from PDF. Please check server logs.";
      toast.error(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-5rem)] py-8 sm:py-12 px-4 sm:px-6 lg:px-8">
      {/* Background Glows */}
      <div className="absolute top-10 left-1/2 -translate-x-1/2 w-96 h-96 bg-indigo-600/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute top-40 right-10 w-72 h-72 bg-blue-600/10 blur-[100px] rounded-full pointer-events-none" />

      <div className="relative max-w-4xl mx-auto space-y-10">

        {/* Hero Section */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold tracking-wide">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-spin" style={{ animationDuration: '6s' }} />
            <span>AI-POWERED RUBRIC CONVERSION</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white font-display">
            Transform Rubrics into <br className="hidden sm:inline" />
            <span className="text-gradient-primary">Formatted Spreadsheets</span>
          </h1>

          <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-400 leading-relaxed">
            Extract tabular grids, multi-span criteria, and grading scales from scanned or digital PDFs directly into clean Excel (.xlsx) workbooks.
          </p>
        </div>

        {/* Upload Card */}
        <div className="glass-panel rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden border border-slate-800/80">
          
          <FileUpload
            selectedFile={selectedFile}
            setSelectedFile={setSelectedFile}
          />

          {/* Processing Progress State */}
          {isProcessing && (
            <div className="mt-8 p-6 rounded-2xl bg-slate-900/90 border border-indigo-500/30 animate-in fade-in duration-300">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-4 h-4 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
                  <span className="text-sm font-bold text-white">
                    Processing Rubric Document...
                  </span>
                </div>
                <span className="text-xs text-indigo-300 font-mono">
                  Stage {activeStep + 1} of 4
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden mb-6">
                <div
                  className="bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-400 h-2 rounded-full transition-all duration-700 ease-out"
                  style={{ width: `${((activeStep + 1) / 4) * 100}%` }}
                />
              </div>

              {/* Multi-Step Pipeline List */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {pipelineSteps.map((step, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border transition-all ${
                      idx === activeStep
                        ? "bg-indigo-950/40 border-indigo-500/50 text-indigo-200"
                        : idx < activeStep
                        ? "bg-slate-800/30 border-slate-700/50 text-slate-400"
                        : "bg-slate-900/20 border-slate-800 text-slate-500"
                    }`}
                  >
                    <div className="flex items-center gap-2 font-semibold">
                      {idx < activeStep ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : idx === activeStep ? (
                        <div className="w-3.5 h-3.5 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin shrink-0" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-slate-600 shrink-0" />
                      )}
                      <span>{step.title}</span>
                    </div>
                    <p className="mt-1 pl-5.5 text-[11px] text-slate-400">{step.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Button */}
          <div className="mt-6">
            <button
              onClick={uploadPDF}
              disabled={isProcessing || !selectedFile}
              className={`w-full relative group overflow-hidden py-4 px-6 rounded-2xl font-bold text-base sm:text-lg flex items-center justify-center gap-3 transition-all duration-300 shadow-xl ${
                isProcessing
                  ? "bg-slate-800 text-slate-400 cursor-not-allowed border border-slate-700"
                  : !selectedFile
                  ? "bg-slate-800/60 text-slate-500 cursor-not-allowed border border-slate-800"
                  : "bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-700 hover:from-indigo-500 hover:to-blue-500 text-white shadow-indigo-600/30 hover:shadow-indigo-600/50 active:scale-[0.99] border border-indigo-500/30"
              }`}
            >
              {isProcessing ? (
                <>
                  <div className="w-5 h-5 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                  <span>Extracting Rubric Table & Merges...</span>
                </>
              ) : (
                <>
                  <FileSpreadsheet className="w-5 h-5 transition-transform group-hover:scale-110" />
                  <span>Process Rubric Document</span>
                  <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </button>
          </div>

        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="glass-card glass-card-hover rounded-2xl p-6">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4">
              <ScanLine className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-white mb-2 font-display">
              Sub-Pixel PaddleOCR
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Detects oriented text bounding boxes, noisy background artifacts, and complex matrix headers with high fidelity.
            </p>
          </div>

          <div className="glass-card glass-card-hover rounded-2xl p-6">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mb-4">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-white mb-2 font-display">
              Smart Span Reconstruction
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Reconstructs multi-row and multi-column merged headers so criteria rows accurately align with performance levels.
            </p>
          </div>

          <div className="glass-card glass-card-hover rounded-2xl p-6">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mb-4">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-white mb-2 font-display">
              Native Excel (.xlsx)
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Exports true Excel workbooks with column auto-width, cell borders, text wrapping, and clean formatting.
            </p>
          </div>
        </div>

        {/* Pro Tips / Notice */}
        <div className="p-4 sm:p-5 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex items-start gap-3.5 text-xs text-slate-400">
          <HelpCircle className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-slate-200">Recommended for optimal results:</span>
            <p className="leading-relaxed">
              Use clean, unskewed PDF scans (300 DPI recommended). If your document contains multiple pages or tables, each detected grid is serialized with intact layout boundaries.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}

export default Upload;