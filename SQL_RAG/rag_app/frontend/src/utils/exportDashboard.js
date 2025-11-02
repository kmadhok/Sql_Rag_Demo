/**
 * Dashboard Export Utilities
 *
 * Export dashboard to various formats: PNG, PDF, JSON
 */

import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

/**
 * Export dashboard as PNG image
 * @param {HTMLElement} element - Dashboard container element
 * @param {string} filename - Output filename (without extension)
 */
export async function exportAsPNG(element, filename = 'dashboard') {
  try {
    const canvas = await html2canvas(element, {
      backgroundColor: '#020617', // Match dark theme background
      scale: 2, // Higher quality
      logging: false,
      useCORS: true,
    });

    // Convert canvas to blob
    canvas.toBlob((blob) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${filename}.png`;
      link.click();
      URL.revokeObjectURL(url);
    }, 'image/png');

    return { success: true };
  } catch (error) {
    console.error('Failed to export as PNG:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Export dashboard as PDF document
 * @param {HTMLElement} element - Dashboard container element
 * @param {string} filename - Output filename (without extension)
 * @param {string} orientation - 'portrait' or 'landscape'
 */
export async function exportAsPDF(element, filename = 'dashboard', orientation = 'landscape') {
  try {
    const canvas = await html2canvas(element, {
      backgroundColor: '#020617',
      scale: 2,
      logging: false,
      useCORS: true,
    });

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF({
      orientation: orientation,
      unit: 'mm',
      format: 'a4',
    });

    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();

    // Calculate image dimensions to fit PDF
    const imgWidth = pdfWidth;
    const imgHeight = (canvas.height * pdfWidth) / canvas.width;

    if (imgHeight <= pdfHeight) {
      // Fits on one page
      pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight);
    } else {
      // Split across multiple pages
      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pdfHeight;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pdfHeight;
      }
    }

    pdf.save(`${filename}.pdf`);
    return { success: true };
  } catch (error) {
    console.error('Failed to export as PDF:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Export dashboard configuration as JSON
 * @param {Object} dashboardData - Dashboard data to export
 * @param {string} filename - Output filename (without extension)
 */
export function exportAsJSON(dashboardData, filename = 'dashboard') {
  try {
    const jsonString = JSON.stringify(dashboardData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.json`;
    link.click();
    URL.revokeObjectURL(url);

    return { success: true };
  } catch (error) {
    console.error('Failed to export as JSON:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Import dashboard configuration from JSON file
 * @param {File} file - JSON file to import
 * @returns {Promise<Object>} Dashboard data
 */
export async function importFromJSON(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        resolve({ success: true, data });
      } catch (error) {
        reject({ success: false, error: 'Invalid JSON file' });
      }
    };

    reader.onerror = () => {
      reject({ success: false, error: 'Failed to read file' });
    };

    reader.readAsText(file);
  });
}
