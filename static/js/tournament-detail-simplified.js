// Simplified JavaScript for tournament detail page

document.addEventListener('DOMContentLoaded', function() {
  // Initialize feather icons if available
  if (typeof feather !== 'undefined') {
    feather.replace();
  }
  
  // Initialize session toggles
  initializeSessionToggles();
  
  // Initialize UI visibility based on attendance state
  updateSessionUIVisibility();
  
  // Add event listener to the meeting toggle
  const meetingToggle = document.getElementById('wants_to_meet');
  
  if (meetingToggle) {
    meetingToggle.addEventListener('change', function() {
      // Visual feedback when toggled
      const label = this.closest('.meeting-toggle-container');
      if (label) {
        if (this.checked) {
          label.classList.add('active');
        } else {
          label.classList.remove('active');
        }
      }
    });
  }
});

// Initialize session toggle buttons
function initializeSessionToggles() {
  // Get all session checkboxes
  const sessionCheckboxes = document.querySelectorAll('.session-checkbox input[type="checkbox"]');
  
  // Add click event to each session checkbox
  sessionCheckboxes.forEach(checkbox => {
    // Initialize classes based on checked state
    updateCheckboxLabel(checkbox);
    
    // Add change event listener
    checkbox.addEventListener('change', function() {
      updateCheckboxLabel(this);
    });
  });
}

// Update the styling of the checkbox label based on checked state
function updateCheckboxLabel(checkbox) {
  const label = checkbox.closest('.session-checkbox');
  if (label) {
    if (checkbox.checked) {
      label.classList.add('active');
      label.style.backgroundColor = '#4CAF50';
      label.style.color = 'white';
      label.style.borderColor = '#4CAF50';
    } else {
      label.classList.remove('active');
      label.style.backgroundColor = 'white';
      label.style.color = '#555';
      label.style.borderColor = '#e9ecef';
    }
  }
}

// Function to toggle the session UI based on attendance state
function updateSessionUIVisibility() {
  // Get attendance buttons - using the new class names
  const attendingBtn = document.querySelector('.btn-attending');
  const maybeBtn = document.querySelector('.btn-maybe');
  
  // Get UI sections
  const sessionSelector = document.querySelector('.session-selector');
  const meetingToggleContainer = document.querySelector('.wants-to-meet-container');
  
  // Determine current attendance state
  const isAttending = attendingBtn && attendingBtn.classList.contains('active');
  const isMaybe = maybeBtn && maybeBtn.classList.contains('active');
  const isNotAttending = !isAttending && !isMaybe;
  
  // Show session selection for both attending and maybe attending users
  if (sessionSelector) {
    sessionSelector.style.display = isNotAttending ? 'none' : 'block';
  }
  
  if (meetingToggleContainer) {
    meetingToggleContainer.style.display = isNotAttending ? 'none' : 'block';
  }
}