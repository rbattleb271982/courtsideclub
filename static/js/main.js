// Tennis Fans App - Main JavaScript

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Mobile navigation toggle
  initMobileNavigation();
  
  // Initialize form validation
  initFormValidation();
  
  // Initialize tournament filters
  initTournamentFilters();
  
  // Initialize date picker if on tournament page
  initDatePicker();
  
  // Initialize raise hand action
  initRaiseHandForm();
  
  // Initialize flash message dismissal
  initFlashMessages();
});

// Mobile navigation toggle
function initMobileNavigation() {
  const navbarToggle = document.querySelector('.navbar-toggle');
  const navbarNav = document.querySelector('.navbar-nav');
  
  if (navbarToggle && navbarNav) {
    navbarToggle.addEventListener('click', function() {
      navbarNav.classList.toggle('show');
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', function(event) {
      if (!event.target.closest('.navbar') && navbarNav.classList.contains('show')) {
        navbarNav.classList.remove('show');
      }
    });
  }
}

// Form validation for login, register, and lanyard forms
function initFormValidation() {
  const forms = document.querySelectorAll('.needs-validation');
  
  Array.from(forms).forEach(form => {
    form.addEventListener('submit', function(event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      
      form.classList.add('was-validated');
    }, false);
  });
}

// Initialize tournament filters
function initTournamentFilters() {
  const tournamentFilter = document.getElementById('tournament-filter');
  if (tournamentFilter) {
    tournamentFilter.addEventListener('change', function() {
      const filterForm = document.getElementById('filter-form');
      if (filterForm) {
        filterForm.submit();
      }
    });
  }
}

// Initialize date picker for tournament filtering
function initDatePicker() {
  const datePicker = document.getElementById('date-filter');
  if (datePicker) {
    // If we had access to a date picker library, we'd initialize it here
    // For now, we'll just use the native date input
    datePicker.addEventListener('change', function() {
      const filterForm = document.getElementById('filter-form');
      if (filterForm) {
        filterForm.submit();
      }
    });
  }
}

// Initialize raise hand form
function initRaiseHandForm() {
  const raiseHandForm = document.getElementById('raise-hand-form');
  const lowerHandBtn = document.getElementById('lower-hand-btn');
  
  if (raiseHandForm) {
    const daySelect = raiseHandForm.querySelector('select[name="day"]');
    const sessionSelect = raiseHandForm.querySelector('select[name="session"]');
    
    if (daySelect) {
      daySelect.addEventListener('change', function() {
        updateSessionOptions(daySelect.value);
      });
    }
    
    // Function to update session options based on selected day
    function updateSessionOptions(day) {
      if (!sessionSelect) return;
      
      // This would typically be populated from a tournaments data object
      // For now, we'll just ensure the field is enabled when a day is selected
      sessionSelect.disabled = !day;
    }
  }
  
  if (lowerHandBtn) {
    lowerHandBtn.addEventListener('click', function(event) {
      event.preventDefault();
      if (raiseHandForm) {
        // Clear all form values
        const daySelect = raiseHandForm.querySelector('select[name="day"]');
        const sessionSelect = raiseHandForm.querySelector('select[name="session"]');
        
        if (daySelect) daySelect.value = '';
        if (sessionSelect) sessionSelect.value = '';
        
        // Submit the form
        raiseHandForm.submit();
      }
    });
  }
}

// Initialize flash messages (auto dismiss after 5 seconds)
function initFlashMessages() {
  const flashMessages = document.querySelectorAll('.alert');
  
  flashMessages.forEach(message => {
    setTimeout(() => {
      message.style.opacity = '0';
      setTimeout(() => {
        message.style.display = 'none';
      }, 500);
    }, 5000);
    
    // Add close button functionality
    const closeBtn = message.querySelector('.close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        message.style.opacity = '0';
        setTimeout(() => {
          message.style.display = 'none';
        }, 500);
      });
    }
  });
}

// Helper function to format dates
function formatDate(dateString) {
  const options = { year: 'numeric', month: 'short', day: 'numeric' };
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, options);
}

// Helper function to show/hide elements
function toggleElement(elementId, show) {
  const element = document.getElementById(elementId);
  if (element) {
    element.style.display = show ? 'block' : 'none';
  }
}

// Helper function to get the first letter of a name (for avatar)
function getInitial(name) {
  return name ? name.charAt(0).toUpperCase() : '?';
}

// Update profile avatar with user's initial
function updateProfileAvatar() {
  const profileAvatar = document.querySelector('.profile-avatar');
  const userName = document.querySelector('.profile-name');
  
  if (profileAvatar && userName && userName.textContent) {
    profileAvatar.textContent = getInitial(userName.textContent.trim());
  }
}

// Call this function if the DOM has profile elements
if (document.querySelector('.profile-avatar')) {
  updateProfileAvatar();
}
