import { useState, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { 
  FileSpreadsheet, 
  Download, 
  ArrowLeft, 
  Search, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Maximize2, 
  Minimize2, 
  Copy, 
  Check, 
  Grid, 
  FileQuestion,
  Sparkles
} from "lucide-react";
import { useToast } from "../components/Toast";

function Review() {
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();

  const { gridData, excelUrl, fileName } = location.state || {};

  const [searchQuery, setSearchQuery] = useState("");
  const [zoomLevel, setZoomLevel] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copiedCell, setCopiedCell] = useState(null);

  // Statistics calculation
  const stats = useMemo(() => {
    if (!gridData || !Array.isArray(gridData)) {
      return { totalRows: 0, maxCols: 0, totalCells: 0, mergedCells: 0 };
    }

    const totalRows = gridData.length;
    let maxCols = 0;
    let totalCells = 0;
    let mergedCells = 0;

    gridData.forEach((row) => {
      if (Array.isArray(row)) {
        if (row.length > maxCols) maxCols = row.length;
        row.forEach((cell) => {
          totalCells++;
          if (cell && typeof cell === "object") {
            if ((cell.colSpan && cell.colSpan > 1) || (cell.rowSpan && cell.rowSpan > 1)) {
              mergedCells++;
            }
          }
        });
      }
    });

    return { totalRows, maxCols, totalCells, mergedCells };
  }, [gridData]);

  // Helper to get letter for column index (A, B, C...)
  const getColumnLabel = (index) => {
    let label = "";
    let num = index;
    while (num >= 0) {
      label = String.fromCharCode((num % 26) + 65) + label;
      num = Math.floor(num / 26) - 1;
    }
    return label;
  };

  const copyToClipboard = (text, cellId) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedCell(cellId);
    toast.info("Copied cell text");
    setTimeout(() => setCopiedCell(null), 1500);
  };

  const handleZoom = (delta) => {
    setZoomLevel((prev) => Math.min(150, Math.max(70, prev + delta)));
  };

  if (!gridData || !Array.isArray(gridData) || gridData.length === 0) {
    return (
      <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center p-4">
        <div className="glass-panel max-w-md w-full rounded-3xl p-8 text-center space-y-6 shadow-2xl border border-slate-800">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
            <FileQuestion className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-white font-display">No Rubric Data Loaded</h2>
            <p className="text-sm text-slate-400">
              Please upload a rubric PDF to extract and preview its structural table grid.
            </p>
          </div>

          <button
            onClick={() => navigate("/")}
            className="w-full py-3 px-5 rounded-xl font-semibold text-white bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 shadow-lg shadow-indigo-600/30 transition flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Go to Upload Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`py-6 px-4 sm:px-6 lg:px-8 transition-all ${isFullscreen ? "fixed inset-0 z-50 bg-slate-950 overflow-auto" : "max-w-7xl mx-auto"}`}>
      
      {/* Header & Controls Bar */}
      <div className="glass-panel rounded-2xl p-5 mb-6 border border-slate-800/80 shadow-xl space-y-4">
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium text-indigo-400 mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>EXTRACTED DOCUMENT MATRIX</span>
              {fileName && <span className="text-slate-500">• {fileName}</span>}
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-display">
              Review Extracted Rubric
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Interactive preview representing the generated Excel workbook structure.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => navigate("/")}
              className="px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white border border-slate-700 transition flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Upload Another
            </button>

            {excelUrl && (
              <a
                href={excelUrl}
                download
                className="px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-lg shadow-emerald-600/30 transition flex items-center gap-2 active:scale-95"
              >
                <Download className="w-4 h-4" />
                Download Excel (.xlsx)
              </a>
            )}
          </div>
        </div>

        {/* Toolbar: Stats, Search, View Controls */}
        <div className="pt-4 border-t border-slate-800/80 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
          
          {/* Metadata Badges */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="px-3 py-1 rounded-lg bg-slate-800/80 text-slate-300 border border-slate-700/60 font-mono">
              <strong className="text-white font-bold">{stats.totalRows}</strong> Rows
            </span>
            <span className="px-3 py-1 rounded-lg bg-slate-800/80 text-slate-300 border border-slate-700/60 font-mono">
              <strong className="text-white font-bold">{stats.maxCols}</strong> Columns
            </span>
            <span className="px-3 py-1 rounded-lg bg-indigo-950/60 text-indigo-300 border border-indigo-500/30 font-mono">
              <strong className="text-indigo-200 font-bold">{stats.mergedCells}</strong> Merged Spans
            </span>
          </div>

          {/* Search & Zoom & Fullscreen */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Search filter */}
            <div className="relative flex-1 sm:w-64">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search cell text..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 hover:text-white"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center bg-slate-900 border border-slate-700 rounded-xl p-1 gap-1">
              <button
                onClick={() => handleZoom(-10)}
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[11px] font-mono px-1.5 text-slate-300">
                {zoomLevel}%
              </span>
              <button
                onClick={() => handleZoom(10)}
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setZoomLevel(100)}
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 ml-0.5 border-l border-slate-700"
                title="Reset Zoom"
              >
                <RotateCcw className="w-3 h-3" />
              </button>
            </div>

            {/* Fullscreen toggle */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 transition"
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen View"}
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>

        </div>

      </div>

      {/* Spreadsheet Table View */}
      <div className="glass-panel rounded-2xl border border-slate-800/80 shadow-2xl overflow-hidden bg-slate-950">
        <div className="overflow-x-auto max-h-[70vh] p-2">
          <div 
            style={{ 
              transform: `scale(${zoomLevel / 100})`, 
              transformOrigin: "top left",
              width: zoomLevel !== 100 ? `${(100 / zoomLevel) * 100}%` : "100%"
            }}
            className="transition-transform duration-150 inline-block min-w-full"
          >
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="bg-slate-900/90 sticky top-0 z-20">
                  {/* Corner index */}
                  <th className="w-12 p-2.5 text-center text-[10px] font-mono font-bold text-slate-500 border border-slate-800 bg-slate-900 select-none">
                    #
                  </th>
                  {Array.from({ length: stats.maxCols }).map((_, colIdx) => (
                    <th
                      key={colIdx}
                      className="p-2.5 text-center text-xs font-mono font-bold text-slate-400 border border-slate-800 bg-slate-900/90 select-none min-w-[120px]"
                    >
                      {getColumnLabel(colIdx)}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {gridData.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-indigo-950/20 transition-colors">
                    {/* Row Index Number */}
                    <td className="w-12 p-2.5 text-center text-[10px] font-mono font-bold text-slate-500 border border-slate-800/80 bg-slate-900/60 select-none">
                      {rowIndex + 1}
                    </td>

                    {/* Cells */}
                    {Array.isArray(row) &&
                      row.map((cell, colIndex) => {
                        const cellValue = typeof cell === "object" && cell !== null ? cell.value : cell;
                        const colSpan = (typeof cell === "object" && cell?.colSpan) || 1;
                        const rowSpan = (typeof cell === "object" && cell?.rowSpan) || 1;
                        const cellId = `${rowIndex}-${colIndex}`;

                        // Check search query highlight
                        const isSearchMatch =
                          searchQuery.trim() !== "" &&
                          cellValue &&
                          String(cellValue).toLowerCase().includes(searchQuery.toLowerCase());

                        const isHeaderRow = rowIndex === 0;

                        return (
                          <td
                            key={colIndex}
                            colSpan={colSpan}
                            rowSpan={rowSpan}
                            onClick={() => copyToClipboard(String(cellValue || ""), cellId)}
                            className={`p-3 text-xs leading-relaxed border transition-all cursor-pointer relative group ${
                              isHeaderRow
                                ? "bg-slate-900/90 font-bold text-indigo-200 border-slate-700/80"
                                : "text-slate-200 border-slate-800/80 hover:bg-slate-800/60"
                            } ${isSearchMatch ? "bg-amber-500/20 text-amber-200 ring-1 ring-amber-400/50" : ""}`}
                            style={{ minWidth: "120px" }}
                            title="Click to copy text"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <span className="break-words select-text">{cellValue || ""}</span>
                              
                              <span className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 shrink-0 mt-0.5">
                                {copiedCell === cellId ? (
                                  <Check className="w-3 h-3 text-emerald-400" />
                                ) : (
                                  <Copy className="w-3 h-3 hover:text-white" />
                                )}
                              </span>
                            </div>

                            {/* Colspan/Rowspan pill indicator on hover */}
                            {(colSpan > 1 || rowSpan > 1) && (
                              <span className="absolute bottom-1 right-1 text-[9px] font-mono text-indigo-400/60 bg-indigo-950/40 px-1 rounded pointer-events-none">
                                {colSpan > 1 ? `W:${colSpan}` : ""}{rowSpan > 1 ? ` H:${rowSpan}` : ""}
                              </span>
                            )}
                          </td>
                        );
                      })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer info bar */}
        <div className="p-3 bg-slate-900/80 border-t border-slate-800 text-[11px] text-slate-400 flex flex-wrap items-center justify-between gap-2 px-4">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Interactive Grid: Click any cell to copy text</span>
          </div>
          <span>Showing 100% extracted table matrix</span>
        </div>
      </div>

    </div>
  );
}

export default Review;