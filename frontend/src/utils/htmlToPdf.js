import html2pdf from 'html2pdf.js';

/**
 * Convert HTML string to PDF and trigger download.
 * Replaces all window.open + document.write + window.print patterns.
 *
 * @param {string} htmlContent - Full HTML string (with <html><head><body>)
 * @param {string} filename - Download filename (without .pdf extension)
 * @param {object} opts - Optional overrides for html2pdf options
 */
export const downloadPdf = (htmlContent, filename = 'document', opts = {}) => {
  const container = document.createElement('div');
  container.style.position = 'absolute';
  container.style.left = '-9999px';
  container.style.top = '0';
  container.style.width = '210mm';

  // Strip <html>, <head>, <body> tags — extract only the body content and styles
  const styleMatch = htmlContent.match(/<style[^>]*>([\s\S]*?)<\/style>/gi);
  const bodyMatch = htmlContent.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  const styles = styleMatch ? styleMatch.join('\n') : '';
  const body = bodyMatch ? bodyMatch[1] : htmlContent;

  container.innerHTML = `${styles}<div class="pdf-content">${body}</div>`;
  document.body.appendChild(container);

  const options = {
    margin: [10, 10, 10, 10],
    filename: `${filename}.pdf`,
    image: { type: 'jpeg', quality: 0.95 },
    html2canvas: { scale: 2, useCORS: true, logging: false },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    ...opts,
  };

  html2pdf()
    .set(options)
    .from(container.querySelector('.pdf-content') || container)
    .save()
    .then(() => {
      document.body.removeChild(container);
    })
    .catch(() => {
      document.body.removeChild(container);
    });
};

/**
 * Shorthand for landscape PDF
 */
export const downloadPdfLandscape = (htmlContent, filename = 'document', opts = {}) => {
  downloadPdf(htmlContent, filename, {
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' },
    ...opts,
  });
};
