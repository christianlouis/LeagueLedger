/**
 * LeagueLedger Main JavaScript
 * Version: 1.0.0
 * Date: April 13, 2025
 */

// Initialize all components when document is ready
document.addEventListener('DOMContentLoaded', () => {
  initializeQrScanner();
  setupModalHandlers();
  initializeTooltips();
  initializeDropdowns();
});

/**
 * QR Code Scanner initialization
 */
function initializeQrScanner() {
  const scannerContainer = document.getElementById('qr-reader');
  
  if (!scannerContainer) return; // Exit if scanner container doesn't exist
  
  // Check if camera access is available
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    // QR Scanner library configuration
    const html5QrCode = new Html5Qrcode("qr-reader");
    const config = { fps: 10, qrbox: 250 };
    
    // Remove overlay once scanner is ready
    const overlay = document.getElementById('scanner-overlay');
    if (overlay) {
      overlay.style.display = 'none';
    }
    
    // Start scanner
    html5QrCode.start(
      { facingMode: "environment" }, // Use rear camera
      config,
      onScanSuccess,
      onScanFailure
    );
    
    // Save scanner instance for later use
    window.qrScanner = html5QrCode;
  } else {
    // Camera unavailable, show manual entry form
    const manualEntry = document.getElementById('manual-entry-container');
    if (manualEntry) {
      manualEntry.style.display = 'block';
    }
    
    const scannerElement = document.getElementById('scanner-container');
    if (scannerElement) {
      scannerElement.style.display = 'none';
    }
    
    console.warn("Camera access not available");
  }
}

/**
 * Handle successful QR code scan
 */
function onScanSuccess(decodedText) {
  // Stop scanner once code is detected
  if (window.qrScanner) {
    window.qrScanner.stop();
  }
  
  // Extract code from URL if present
  let code = decodedText;
  if (decodedText.includes('/redeem/')) {
    code = decodedText.split('/redeem/').pop();
  }
  
  // Redirect to redemption page
  window.location.href = '/redeem/' + code;
}

/**
 * Handle QR scan errors
 */
function onScanFailure(error) {
  // We don't need to show errors for normal operation
  console.debug("QR scan error: " + error);
}

/**
 * Initialize modal handlers
 */
function setupModalHandlers() {
  // Find all elements meant to open modals
  const modalOpeners = document.querySelectorAll('[data-modal-target]');
  const modalClosers = document.querySelectorAll('[data-modal-close]');
  
  modalOpeners.forEach(opener => {
    opener.addEventListener('click', (e) => {
      e.preventDefault();
      const modalId = opener.getAttribute('data-modal-target');
      const modal = document.getElementById(modalId);
      
      if (modal) {
        modal.classList.remove('hidden');
      }
    });
  });
  
  modalClosers.forEach(closer => {
    closer.addEventListener('click', (e) => {
      e.preventDefault();
      const modal = closer.closest('.modal');
      
      if (modal) {
        modal.classList.add('hidden');
      }
    });
  });
  
  // Close modal when clicking outside
  document.addEventListener('click', (e) => {
    const modals = document.querySelectorAll('.modal:not(.hidden)');
    modals.forEach(modal => {
      if (e.target === modal) {
        modal.classList.add('hidden');
      }
    });
  });
}

/**
 * Initialize tooltips
 */
function initializeTooltips() {
  const tooltips = document.querySelectorAll('[data-tooltip]');
  
  tooltips.forEach(tooltip => {
    tooltip.addEventListener('mouseenter', (e) => {
      const text = tooltip.getAttribute('data-tooltip');
      
      // Create tooltip element
      const tooltipEl = document.createElement('div');
      tooltipEl.classList.add('tooltip');
      tooltipEl.textContent = text;
      
      // Position the tooltip
      const rect = tooltip.getBoundingClientRect();
      tooltipEl.style.top = (rect.top - 30) + 'px';
      tooltipEl.style.left = (rect.left + rect.width/2) + 'px';
      
      // Add to DOM
      document.body.appendChild(tooltipEl);
      
      // Save reference to remove it later
      tooltip._tooltipElement = tooltipEl;
    });
    
    tooltip.addEventListener('mouseleave', () => {
      if (tooltip._tooltipElement) {
        tooltip._tooltipElement.remove();
        tooltip._tooltipElement = null;
      }
    });
  });
}

/**
 * Initialize dropdown menus
 */
function initializeDropdowns() {
  const dropdowns = document.querySelectorAll('.dropdown-toggle');
  
  dropdowns.forEach(dropdown => {
    dropdown.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      const menu = dropdown.nextElementSibling;
      if (menu && menu.classList.contains('dropdown-menu')) {
        menu.classList.toggle('hidden');
      }
    });
  });
  
  // Close dropdowns when clicking elsewhere
  document.addEventListener('click', () => {
    const openDropdowns = document.querySelectorAll('.dropdown-menu:not(.hidden)');
    openDropdowns.forEach(menu => {
      menu.classList.add('hidden');
    });
  });
}