import React, { useState, useRef, useEffect } from 'react';
import { downloadPdf } from '../utils/htmlToPdf';
import { Button } from './ui/button';
import { 
  X, Printer, Download, ZoomIn, ZoomOut, Maximize2, Minimize2, 
  ChevronLeft, ChevronRight, RotateCw
} from 'lucide-react';

/**
 * DocumentPreview - Full-page live document preview with zoom, print, and download
 * 
 * Props:
 * - title: Document title for display and print
 * - children: The document content to preview
 * - onClose: Callback when preview is closed
 * - printStyles: Optional custom CSS for print styling
 * - fileName: Optional filename for downloads
 */
const DocumentPreview = ({ 
  title = 'Document Preview', 
  children, 
  onClose, 
  printStyles = '',
  fileName = 'document'
}) => {
  const [zoom, setZoom] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);
  const contentRef = useRef(null);

  // Fullscreen handling
  const enterFullscreen = () => {
    if (containerRef.current?.requestFullscreen) {
      containerRef.current.requestFullscreen();
      setIsFullscreen(true);
    }
  };

  const exitFullscreen = () => {
    if (document.exitFullscreen) {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // Handle escape key to close
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        if (isFullscreen) {
          exitFullscreen();
        } else {
          onClose?.();
        }
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isFullscreen, onClose]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Zoom controls
  const handleZoomIn = () => setZoom(prev => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 25, 50));
  const handleResetZoom = () => setZoom(100);

  // Print functionality
  const handlePrint = () => {
    const printContent = contentRef.current;
    if (!printContent) return;

        if (!printWindow) {
      alert('Please allow popups for printing');
      return;
    }

    const defaultStyles = `
      @page { size: A4; margin: 10mm; }
      @media print { 
        body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } 
        .no-print { display: none !important; }
      }
      * { box-sizing: border-box; }
      body { 
        font-family: Arial, sans-serif; 
        font-size: 11px; 
        padding: 20px; 
        margin: 0;
        color: #333;
      }
    `;

    const _pdfHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${title}</title>
          <style>
            ${defaultStyles}
            ${printStyles}
          </style>
        </head>
        <body>
          ${printContent.innerHTML}
        </body>
      </html>
    `;
    downloadPdf(_pdfHtml, 'Document');
    setTimeout(() => {
      printWindow.close();
    }, 300);
  };

  // Download as PDF (uses print dialog)
  const handleDownload = () => {
    // Trigger print which allows saving as PDF
    handlePrint();
  };

  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 bg-gray-900/95 z-50 flex flex-col"
      data-testid="document-preview"
    >
      {/* Header Toolbar */}
      <header className="bg-gray-800 text-white px-4 py-3 flex items-center justify-between shadow-lg flex-shrink-0">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold truncate max-w-xs sm:max-w-md">{title}</h2>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Zoom Controls */}
          <div className="hidden sm:flex items-center gap-1 bg-gray-700 rounded-lg px-2 py-1">
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-8 w-8 text-white hover:bg-gray-600"
              onClick={handleZoomOut}
              disabled={zoom <= 50}
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <span className="text-sm w-12 text-center">{zoom}%</span>
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-8 w-8 text-white hover:bg-gray-600"
              onClick={handleZoomIn}
              disabled={zoom >= 200}
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-8 w-8 text-white hover:bg-gray-600"
              onClick={handleResetZoom}
              title="Reset Zoom"
            >
              <RotateCw className="w-4 h-4" />
            </Button>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-1">
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-9 w-9 text-white hover:bg-gray-700"
              onClick={isFullscreen ? exitFullscreen : enterFullscreen}
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
            </Button>
            <Button 
              onClick={handleDownload}
              className="bg-green-600 hover:bg-green-700 h-9 px-3"
              title="Download / Save as PDF"
            >
              <Download className="w-4 h-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">Download</span>
            </Button>
            <Button 
              onClick={handlePrint}
              className="bg-blue-600 hover:bg-blue-700 h-9 px-3"
              title="Print Document"
            >
              <Printer className="w-4 h-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">Print</span>
            </Button>
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-9 w-9 text-white hover:bg-red-600"
              onClick={onClose}
              title="Close Preview (Esc)"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Mobile Zoom Controls */}
      <div className="sm:hidden bg-gray-800 px-4 py-2 flex justify-center gap-2 border-t border-gray-700">
        <Button 
          variant="outline" 
          size="sm"
          className="bg-gray-700 text-white border-gray-600"
          onClick={handleZoomOut}
          disabled={zoom <= 50}
        >
          <ZoomOut className="w-4 h-4" />
        </Button>
        <span className="text-white text-sm flex items-center w-14 justify-center">{zoom}%</span>
        <Button 
          variant="outline" 
          size="sm"
          className="bg-gray-700 text-white border-gray-600"
          onClick={handleZoomIn}
          disabled={zoom >= 200}
        >
          <ZoomIn className="w-4 h-4" />
        </Button>
        <Button 
          variant="outline" 
          size="sm"
          className="bg-gray-700 text-white border-gray-600"
          onClick={handleResetZoom}
        >
          <RotateCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Document Content Area */}
      <main className="flex-1 overflow-auto bg-gray-600 p-4 sm:p-8">
        <div 
          className="mx-auto transition-transform duration-200"
          style={{ 
            transform: `scale(${zoom / 100})`,
            transformOrigin: 'top center',
            width: zoom > 100 ? `${10000 / zoom}%` : '100%',
            maxWidth: '850px'
          }}
        >
          {/* Paper-like container */}
          <div 
            ref={contentRef}
            className="bg-white shadow-2xl rounded-sm mx-auto"
            style={{ 
              minHeight: '1100px',
              padding: '40px'
            }}
          >
            {children}
          </div>
        </div>
      </main>

      {/* Footer with keyboard hints */}
      <footer className="bg-gray-800 text-gray-400 text-xs px-4 py-2 flex justify-between items-center flex-shrink-0">
        <span>Press Esc to close • Ctrl+P to print</span>
        <span>Scroll to navigate • Use zoom controls for better view</span>
      </footer>
    </div>
  );
};

export default DocumentPreview;
