import { useState, useRef } from "react";
import { UploadCloud, FileText, X, CheckCircle, FileCheck, ArrowUpRight } from "lucide-react";
import { useToast } from "./Toast";

function FileUpload({ selectedFile, setSelectedFile }) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const toast = useToast();

  const handleFiles = (file) => {
    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Please upload a valid PDF document.");
      return;
    }

    if (file.size > 16 * 1024 * 1024) {
      toast.error("File exceeds 16MB limit. Please upload a smaller document.");
      return;
    }

    setSelectedFile(file);
    toast.success(`Loaded: ${file.name}`);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    handleFiles(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    handleFiles(file);
  };

  const removeFile = (e) => {
    e.stopPropagation();
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    toast.info("Document removed.");
  };

  const formatSize = (bytes) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={handleFileChange}
      />

      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`group relative overflow-hidden rounded-3xl border-2 border-dashed p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 ${
            isDragging
              ? "border-indigo-400 bg-indigo-950/40 shadow-2xl shadow-indigo-500/20 scale-[1.01]"
              : "border-slate-700/80 bg-slate-900/60 hover:border-indigo-500/60 hover:bg-slate-900/90 hover:shadow-xl hover:shadow-indigo-500/10"
          }`}
        >
          {/* Ambient background hover flare */}
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

          <div className="relative flex flex-col items-center justify-center">
            {/* Animated Icon Container */}
            <div
              className={`w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300 ${
                isDragging
                  ? "bg-gradient-to-tr from-indigo-500 to-cyan-400 text-white scale-110 shadow-lg shadow-indigo-500/40"
                  : "bg-slate-800/90 text-indigo-400 border border-slate-700 group-hover:bg-indigo-600/20 group-hover:text-indigo-300 group-hover:border-indigo-500/40 group-hover:scale-105"
              }`}
            >
              <UploadCloud className={`w-10 h-10 transition-transform ${isDragging ? "animate-bounce" : "group-hover:-translate-y-1"}`} />
            </div>

            <h3 className="mt-5 text-lg sm:text-xl font-bold text-white tracking-tight font-display">
              {isDragging ? "Drop your Rubric PDF here" : "Choose a rubric file or drag & drop"}
            </h3>

            <p className="mt-2 text-sm text-slate-400 max-w-sm">
              Upload evaluation rubrics, scanned grade sheets, or table matrix documents.
            </p>

            {/* Badges / Specs */}
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs">
              <span className="px-3 py-1 rounded-full bg-slate-800/80 text-slate-300 border border-slate-700/60 font-medium">
                PDF only
              </span>
              <span className="px-3 py-1 rounded-full bg-slate-800/80 text-slate-300 border border-slate-700/60 font-medium">
                Max 16 MB
              </span>
              <span className="px-3 py-1 rounded-full bg-indigo-950/60 text-indigo-300 border border-indigo-500/30 font-medium flex items-center gap-1">
                <FileCheck className="w-3.5 h-3.5" />
                OCR Auto-Grid
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Selected File Card */
        <div className="relative overflow-hidden rounded-2xl border border-indigo-500/30 bg-gradient-to-r from-slate-900/90 via-slate-900/95 to-indigo-950/40 p-5 sm:p-6 shadow-xl shadow-black/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            
            <div className="flex items-center gap-4 min-w-0">
              {/* PDF Icon Badge */}
              <div className="relative shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-rose-500/20 to-rose-600/10 border border-rose-500/30 flex items-center justify-center text-rose-400 shadow-inner">
                <FileText className="w-7 h-7" />
                <span className="absolute -bottom-1 -right-1 text-[9px] font-extrabold uppercase bg-rose-600 text-white px-1.5 py-0.5 rounded-md shadow">
                  PDF
                </span>
              </div>

              {/* File Info */}
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="text-base font-bold text-white truncate max-w-[240px] sm:max-w-sm md:max-w-md">
                    {selectedFile.name}
                  </h4>
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-950/50 border border-emerald-500/30 px-2 py-0.5 rounded-full shrink-0">
                    <CheckCircle className="w-3 h-3" />
                    Ready
                  </span>
                </div>
                
                <div className="mt-1 flex items-center gap-3 text-xs text-slate-400">
                  <span>{formatSize(selectedFile.size)}</span>
                  <span>•</span>
                  <span>Last modified: {new Date(selectedFile.lastModified || Date.now()).toLocaleDateString()}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 self-end sm:self-center">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-slate-200 hover:bg-slate-700 hover:text-white border border-slate-700 transition"
              >
                Change File
              </button>
              
              <button
                type="button"
                onClick={removeFile}
                className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-950/50 border border-transparent hover:border-rose-500/30 transition"
                title="Remove file"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}

export default FileUpload;