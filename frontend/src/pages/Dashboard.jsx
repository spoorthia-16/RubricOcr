import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { 
  FileSpreadsheet, 
  Download, 
  Trash2, 
  RefreshCw, 
  Search, 
  ArrowUpDown, 
  Plus, 
  HardDrive, 
  Activity, 
  Calendar, 
  FileText,
  AlertTriangle,
  X,
  Sparkles
} from "lucide-react";
import API from "../services/api";
import { useToast } from "../components/Toast";

function Dashboard() {
  const navigate = useNavigate();
  const toast = useToast();

  const [data, setData] = useState({ total_processed: 0, files: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("newest"); // "newest", "oldest", "largest", "smallest"
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [deleteModalFile, setDeleteModalFile] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setIsRefreshing(true);
      const response = await API.get("/dashboard");
      if (response.data.success) {
        setData(response.data);
        setError("");
      } else {
        setError(response.data.message || "Failed to load dashboard data");
      }
    } catch (err) {
      setError("Unable to connect to the backend server.");
      console.error(err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteModalFile) return;

    try {
      const response = await API.delete(`/delete/${deleteModalFile}`);
      if (response.data.success) {
        toast.success(`Deleted: ${deleteModalFile}`);
        fetchDashboardData();
      } else {
        toast.error("Failed to delete file: " + response.data.message);
      }
    } catch (err) {
      console.error(err);
      toast.error("Error deleting file.");
    } finally {
      setDeleteModalFile(null);
    }
  };

  const formatSize = (bytes) => {
    if (!bytes || bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  // Filter and sort files
  const filteredFiles = useMemo(() => {
    let files = [...(data.files || [])];

    if (searchQuery.trim() !== "") {
      const query = searchQuery.toLowerCase();
      files = files.filter((f) => f.filename.toLowerCase().includes(query));
    }

    files.sort((a, b) => {
      if (sortBy === "newest") {
        return new Date(b.created_at) - new Date(a.created_at);
      }
      if (sortBy === "oldest") {
        return new Date(a.created_at) - new Date(b.created_at);
      }
      if (sortBy === "largest") {
        return (b.size || 0) - (a.size || 0);
      }
      if (sortBy === "smallest") {
        return (a.size || 0) - (b.size || 0);
      }
      return 0;
    });

    return files;
  }, [data.files, searchQuery, sortBy]);

  // Total size sum
  const totalStorageBytes = useMemo(() => {
    return (data.files || []).reduce((acc, curr) => acc + (curr.size || 0), 0);
  }, [data.files]);

  return (
    <div className="relative min-h-[calc(100vh-5rem)] py-8 sm:py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
      
      {/* Background ambient lighting */}
      <div className="absolute top-10 right-1/4 w-80 h-80 bg-indigo-600/10 blur-[130px] rounded-full pointer-events-none" />

      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>RUBRIC HISTORY & EXPORTS</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-white font-display">
            Processing Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage your generated Excel workbooks and document conversion logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchDashboardData}
            disabled={isRefreshing}
            className="p-2.5 sm:px-4 sm:py-2.5 rounded-xl text-xs sm:text-sm font-semibold bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition flex items-center gap-2"
            title="Refresh history"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-indigo-400" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          <button
            onClick={() => navigate("/")}
            className="px-4 py-2.5 rounded-xl text-xs sm:text-sm font-bold text-white bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 shadow-lg shadow-indigo-600/30 transition flex items-center gap-2 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Process New Rubric</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        
        {/* Total Processed */}
        <div className="glass-card rounded-2xl p-6 border border-slate-800/80 shadow-xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Total Rubrics
            </span>
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-4xl font-extrabold text-white font-display tracking-tight">
              {loading ? "-" : data.total_processed}
            </span>
            <p className="text-xs text-indigo-300/80 mt-1 font-medium">
              Successfully serialized workbooks
            </p>
          </div>
        </div>

        {/* Storage footprint */}
        <div className="glass-card rounded-2xl p-6 border border-slate-800/80 shadow-xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Storage Consumed
            </span>
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
              <HardDrive className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-4xl font-extrabold text-white font-display tracking-tight">
              {loading ? "-" : formatSize(totalStorageBytes)}
            </span>
            <p className="text-xs text-cyan-300/80 mt-1 font-medium">
              Excel (.xlsx) exports archive
            </p>
          </div>
        </div>

        {/* OCR Engine Status */}
        <div className="glass-card rounded-2xl p-6 border border-slate-800/80 shadow-xl relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              OCR Engine
            </span>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white font-display">
              PaddleOCR v6
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/50 border border-emerald-500/30 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Online
            </span>
          </div>
          <p className="text-xs text-emerald-300/80 mt-1 font-medium">
            Sub-pixel bounding box inference
          </p>
        </div>

      </div>

      {/* Main Table Section */}
      <div className="glass-panel rounded-3xl border border-slate-800/80 shadow-2xl overflow-hidden">
        
        {/* Search & Sort Controls Header */}
        <div className="p-5 sm:p-6 border-b border-slate-800/80 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white font-display">
              Exported Excel Workbooks
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing {filteredFiles.length} of {data.total_processed} files
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Filter by filename..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Sort Selector */}
            <div className="flex items-center bg-slate-900 border border-slate-700 rounded-xl px-2.5 py-1.5 gap-2">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer"
              >
                <option value="newest" className="bg-slate-900 text-white">Newest First</option>
                <option value="oldest" className="bg-slate-900 text-white">Oldest First</option>
                <option value="largest" className="bg-slate-900 text-white">Largest Size</option>
                <option value="smallest" className="bg-slate-900 text-white">Smallest Size</option>
              </select>
            </div>
          </div>
        </div>

        {/* Content body */}
        {loading ? (
          <div className="p-16 text-center space-y-3">
            <div className="w-8 h-8 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin mx-auto" />
            <p className="text-sm text-slate-400">Loading export history...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center text-rose-400 space-y-2">
            <AlertTriangle className="w-8 h-8 mx-auto" />
            <p className="text-sm font-semibold">{error}</p>
          </div>
        ) : filteredFiles.length === 0 ? (
          <div className="p-16 text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-slate-800 border border-slate-700 text-slate-500 flex items-center justify-center mx-auto">
              <FileSpreadsheet className="w-7 h-7" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-white font-display">
                {searchQuery ? "No matching rubrics found" : "No rubrics processed yet"}
              </h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                {searchQuery
                  ? "Try adjusting your search query or clear the filter."
                  : "Upload your first rubric PDF to extract tables and generate structured Excel sheets."}
              </p>
            </div>
            {!searchQuery && (
              <button
                onClick={() => navigate("/")}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 transition"
              >
                Upload Rubric
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/60 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-6">File Name</th>
                  <th className="py-3.5 px-6">Date Processed</th>
                  <th className="py-3.5 px-6">Size</th>
                  <th className="py-3.5 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-sm">
                {filteredFiles.map((file, index) => (
                  <tr
                    key={index}
                    className="hover:bg-slate-800/40 transition-colors group"
                  >
                    {/* Filename & Excel Badge */}
                    <td className="py-4 px-6 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0 shadow-sm">
                          <FileSpreadsheet className="w-4 h-4" />
                        </div>
                        <div>
                          <a
                            href={file.url}
                            download
                            className="font-semibold text-white hover:text-indigo-300 transition block max-w-xs sm:max-w-md truncate"
                            title={file.filename}
                          >
                            {file.filename}
                          </a>
                          <span className="text-[11px] text-slate-500">
                            Excel Workbook (.xlsx)
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Date */}
                    <td className="py-4 px-6 whitespace-nowrap text-xs text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        <span>{formatDate(file.created_at)}</span>
                      </div>
                    </td>

                    {/* Size */}
                    <td className="py-4 px-6 whitespace-nowrap text-xs">
                      <span className="px-2.5 py-1 rounded-md bg-slate-800/80 text-slate-300 border border-slate-700/60 font-mono">
                        {formatSize(file.size)}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-4 px-6 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-2">
                        <a
                          href={file.url}
                          download
                          className="px-3 py-1.5 rounded-xl text-xs font-semibold text-emerald-300 bg-emerald-950/50 hover:bg-emerald-900/60 border border-emerald-500/30 transition flex items-center gap-1.5 shadow-sm"
                          title="Download Excel"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download</span>
                        </a>

                        <button
                          onClick={() => setDeleteModalFile(file.filename)}
                          className="p-1.5 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-950/50 border border-transparent hover:border-rose-500/30 transition"
                          title="Delete file"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      </div>

      {/* Delete Confirmation Modal */}
      {deleteModalFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="glass-panel max-w-sm w-full rounded-2xl p-6 shadow-2xl border border-slate-700 space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-rose-950/60 border border-rose-500/30 text-rose-400 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <button
                onClick={() => setDeleteModalFile(null)}
                className="text-slate-400 hover:text-white p-1 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-white font-display">Delete Excel Export?</h3>
              <p className="text-xs text-slate-400 break-all leading-relaxed">
                Are you sure you want to delete <span className="text-slate-200 font-semibold">{deleteModalFile}</span>? This action cannot be undone.
              </p>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => setDeleteModalFile(null)}
                className="flex-1 py-2.5 rounded-xl text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 py-2.5 rounded-xl text-xs font-bold text-white bg-rose-600 hover:bg-rose-500 transition shadow-lg shadow-rose-600/30"
              >
                Delete File
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default Dashboard;