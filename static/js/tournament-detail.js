// JavaScript for improving tournament detail page experience

document.addEventListener('DOMContentLoaded', function() {
  // Initialize feather icons
  if (typeof feather !== 'undefined') {
    feather.replace();
  }
  
  // Add mobile fixed save bar behavior
  if (window.innerWidth < 768) {
    document.body.classList.add('has-fixed-save');
  }
  
  // Initialize UI visibility based on current attendance state
  updateSessionUIVisibility();
  
  // Track selected sessions
  let selectedSessions = [];
  
  // Initialize selected sessions from existing state
  document.querySelectorAll('.session-chip.selected').forEach(chip => {
    selectedSessions.push(chip.dataset.session);
  });
  
  // Update the UI based on initial state and selected sessions
  updateSessionCountDisplay();
  updateSaveButtonState();
  
  // Make sure visibility is correct on page load for desktop 
  // Fix for the desktop issue where session picker gets hidden
  
  // Add click handlers for session chips
  const sessionChips = document.querySelectorAll('.session-chip');
  sessionChips.forEach(chip => {
    chip.addEventListener('click', function() {
      const sessionValue = this.dataset.session;
      
      if (this.classList.contains('selected')) {
        // Remove from selected sessions
        this.classList.remove('selected');
        
        // Remove from array
        const index = selectedSessions.indexOf(sessionValue);
        if (index > -1) {
          selectedSessions.splice(index, 1);
        }
      } else {
        // Add to selected sessions
        this.classList.add('selected');
        
        // Add to array if not already there
        if (!selectedSessions.includes(sessionValue)) {
          selectedSessions.push(sessionValue);
        }
      }
      
      // Update session count display and save button state
      updateSessionCountDisplay();
      updateSaveButtonState();
    });
  });
  
  // Function to update the session count message
  function updateSessionCountDisplay() {
    const sessionCount = selectedSessions.length;
    const sessionCountElement = document.getElementById('sessionCountMessage');
    
    if (sessionCountElement) {
      if (sessionCount > 0) {
        sessionCountElement.innerHTML = `
          <span class="text-success font-weight-bold">
            <i data-feather="check-circle" class="icon-sm"></i>
            You've selected ${sessionCount} session${sessionCount !== 1 ? 's' : ''}
          </span>
        `;
      } else {
        sessionCountElement.innerHTML = `
          <span class="text-muted">
            Select which sessions you'll attend
          </span>
        `;
      }
      
      // Re-initialize feather icons
      if (typeof feather !== 'undefined') {
        feather.replace();
      }
    }
  }
  
  // Function to update save button state
  function updateSaveButtonState() {
    const saveButton = document.getElementById('saveButton');
    const goingBtn = document.getElementById('btn-going');
    const isAttending = goingBtn && goingBtn.classList.contains('btn-success');
    
    if (saveButton) {
      if (selectedSessions.length > 0) {
        // Has sessions, always enable the save button
        saveButton.classList.remove('btn-secondary', 'disabled');
        saveButton.classList.add('btn-success');
        saveButton.disabled = false;
      } else if (isAttending) {
        // No sessions but is attending, disable save button
        saveButton.classList.remove('btn-success');
        saveButton.classList.add('btn-secondary', 'disabled');
        saveButton.disabled = true;
      } else {
        // "Thinking About It" state - enable the save button
        saveButton.classList.remove('btn-secondary', 'disabled');
        saveButton.classList.add('btn-success');
        saveButton.disabled = false;
      }
    }
  }
  
  // Handle save button click
  const saveButton = document.getElementById('saveButton');
  const sessionForm = document.getElementById('sessionForm');
  
  if (saveButton && sessionForm) {
    saveButton.addEventListener('click', function() {
      if (selectedSessions.length === 0) {
        return; // Prevent submission if no sessions selected
      }
      
      // Show loading state
      saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
      saveButton.disabled = true;
      
      // Clear previous hidden inputs
      const hiddenInputsContainer = document.getElementById('hiddenSessionInputs');
      hiddenInputsContainer.innerHTML = '';
      
      // Create hidden inputs for each selected session
      selectedSessions.forEach(session => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'sessions';
        input.value = session;
        hiddenInputsContainer.appendChild(input);
      });
      
      // Also add the wants-to-meet value as a hidden input
      const meetingCheckbox = document.getElementById('wants-to-meet-top');
      if (meetingCheckbox) {
        const meetingInput = document.createElement('input');
        meetingInput.type = 'hidden';
        meetingInput.name = 'open_to_meet';
        meetingInput.value = meetingCheckbox.checked ? 'true' : 'false';
        hiddenInputsContainer.appendChild(meetingInput);
      }
      
      // Submit the form
      sessionForm.submit();
    });
  }
  
  // Handle toggle behavior for "I'm open to meeting" button
  const meetingToggleBtn = document.querySelector('.meeting-toggle-btn');
  const meetingCheckbox = document.getElementById('wants-to-meet-top');
  
  if (meetingToggleBtn && meetingCheckbox) {
    meetingToggleBtn.addEventListener('click', function(e) {
      e.preventDefault(); // Prevent form submission
      meetingCheckbox.checked = !meetingCheckbox.checked;
      
      // Update button styling
      toggleMeetingButton(this);
    });
  }
  
  // Handle attendance button clicks (visual feedback only)
  const attendanceButtons = document.querySelectorAll('.attendance-btn');
  
  // Track which button is currently updating
  let isUpdating = false;
  
  attendanceButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      // Check if any button is currently updating
      if (isUpdating) {
        // Prevent multiple buttons from showing "Updating..." at the same time
        e.preventDefault();
        return false;
      }
      
      // Mark that we're now updating
      isUpdating = true;
      
      // Store the original content and button for potential rollback
      const originalContent = this.innerHTML;
      const clickedButton = this;
      
      // Show loading indicator only on this button
      this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
      this.disabled = true;
      
      // Disable all other buttons during this operation
      attendanceButtons.forEach(otherButton => {
        if (otherButton !== clickedButton) {
          otherButton.disabled = true;
        }
      });
      
      // Set a fallback timeout in case the form submission fails
      const fallbackTimeout = setTimeout(() => {
        // Reset button state
        clickedButton.innerHTML = originalContent;
        clickedButton.disabled = false;
        isUpdating = false;
        
        // Re-enable all buttons
        attendanceButtons.forEach(btn => {
          btn.disabled = false;
        });
        
        // Show error message
        showErrorToast('Update failed. Please try again.');
      }, 10000); // 10 second timeout as a fallback
      
      // The form will submit normally, and the page will reload
      // The fallback timeout will be cleared by page reload if successful
    });
  });
  
  // Function to show error toast
  function showErrorToast(message) {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.style.position = 'fixed';
      toastContainer.style.bottom = '20px';
      toastContainer.style.right = '20px';
      toastContainer.style.zIndex = '9999';
      document.body.appendChild(toastContainer);
    }
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.style.minWidth = '250px';
    toast.style.backgroundColor = '#f8d7da';
    toast.style.color = '#721c24';
    toast.style.padding = '10px 20px';
    toast.style.marginBottom = '10px';
    toast.style.borderRadius = '4px';
    toast.style.boxShadow = '0 0.25rem 0.75rem rgba(0, 0, 0, 0.1)';
    
    toast.innerHTML = `
      <div class="d-flex align-items-center">
        <i data-feather="alert-circle" style="margin-right: 10px;"></i>
        <div>${message}</div>
        <button type="button" class="ml-auto close" style="background: none; border: none; font-size: 1.5rem; line-height: 1; cursor: pointer;">
          &times;
        </button>
      </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Initialize icon if feather is available
    if (typeof feather !== 'undefined') {
      feather.replace();
    }
    
    // Add click handler to close button
    const closeButton = toast.querySelector('.close');
    if (closeButton) {
      closeButton.addEventListener('click', () => {
        toast.remove();
      });
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      toast.remove();
    }, 5000);
  }
});

// Function to toggle the session UI based on attendance state
function updateSessionUIVisibility() {
  // Get attendance buttons
  const goingBtn = document.getElementById('btn-going');
  const thinkingBtn = document.getElementById('btn-thinking');
  const notGoingBtn = document.getElementById('btn-not-going');
  
  // Get UI sections
  const sessionSelectionUI = document.getElementById('session-selection-ui');
  const sessionSelectionCard = document.getElementById('session-selection-card');
  const meetingToggleContainer = document.getElementById('meeting-toggle-container');
  const saveBar = document.getElementById('saveBar');
  const sessionCountMessage = document.getElementById('sessionCountMessage');
  const thinkingMessage = document.getElementById('thinking-message');
  
  // Determine current attendance state
  const isAttending = goingBtn && goingBtn.classList.contains('btn-success');
  const isThinking = thinkingBtn && thinkingBtn.classList.contains('btn-secondary');
  const isNotGoing = notGoingBtn && notGoingBtn.classList.contains('btn-secondary');
  
  // Update UI visibility based on attendance state
  // This function should match server-side logic
  
  if (sessionSelectionCard) {
    sessionSelectionCard.style.display = isNotGoing ? 'none' : 'block';
  }
  
  if (sessionSelectionUI) {
    sessionSelectionUI.style.display = isAttending ? 'block' : 'none';
  }
  
  if (meetingToggleContainer) {
    meetingToggleContainer.style.display = isAttending ? 'block' : 'none';
  }
  
  if (thinkingMessage) {
    thinkingMessage.style.display = (isThinking && !isAttending) ? 'block' : 'none';
  }
  
  if (saveBar) {
    saveBar.style.display = isNotGoing ? 'none' : 'block';
  }
  
  if (sessionCountMessage) {
    sessionCountMessage.style.display = isAttending ? 'block' : 'none';
  }
}

// Function to toggle meeting button appearance
function toggleMeetingButton(button) {
  const meetingCheckbox = document.getElementById('wants-to-meet-top');
  if (!meetingCheckbox) return;
  
  const meetingLabel = button.querySelector('.meeting-label');
  const checkmarkSpan = button.querySelector('.checkmark');
  
  if (meetingCheckbox.checked) {
    button.classList.remove('btn-outline-success');
    button.classList.add('btn-success');
    meetingLabel.textContent = "I'm open to meeting other fans";
    
    // Add checkmark if it doesn't exist
    if (!checkmarkSpan) {
      const checkmark = document.createElement('span');
      checkmark.className = 'ml-1 checkmark';
      checkmark.textContent = '✓';
      button.querySelector('span').appendChild(checkmark);
    }
  } else {
    button.classList.remove('btn-success');
    button.classList.add('btn-outline-success');
    meetingLabel.textContent = "Meet other fans?";
    
    // Remove checkmark if it exists
    if (checkmarkSpan) {
      checkmarkSpan.remove();
    }
  }
}