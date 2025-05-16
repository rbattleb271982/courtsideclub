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
    
    if (saveButton) {
      // Simpler logic: if we have selected sessions, enable the button
      if (selectedSessions.length > 0) {
        // Has sessions, always enable the save button
        saveButton.classList.remove('btn-secondary', 'disabled');
        saveButton.classList.add('btn-success');
        saveButton.disabled = false;
      } else {
        // No sessions selected, disable the save button
        saveButton.classList.remove('btn-success');
        saveButton.classList.add('btn-secondary', 'disabled');
        saveButton.disabled = true;
      }
    }
  }
  
  // Handle form submission
  const saveButton = document.getElementById('saveButton');
  const sessionForm = document.getElementById('sessionForm');
  
  if (sessionForm) {
    // Handle form submission
    sessionForm.addEventListener('submit', function(e) {
      if (selectedSessions.length === 0) {
        e.preventDefault(); // Prevent submission if no sessions selected
        return;
      }
      
      // Show loading state on button if it exists
      if (saveButton) {
        saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
        saveButton.disabled = true;
      }
      
      // Clear previous hidden inputs
      const hiddenInputsContainer = document.getElementById('hiddenSessionInputs');
      if (hiddenInputsContainer) {
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
      }
      
      // Let form submit naturally
    });
  }
  
  // Handle attendance button clicks
  const attendanceButtons = document.querySelectorAll('.attendance-btn');
  
  // Simply let forms submit naturally without visual changes
  // The page will reload with the correct state
  
  // Handle toggle switch for "I'm open to meeting other fans"
  const toggleSwitch = document.getElementById('wants-to-meet-top');
  const meetingForm = document.getElementById('meeting-toggle-form');
  const hiddenInput = document.getElementById('wants-to-meet-hidden');
  
  if (toggleSwitch && meetingForm && hiddenInput) {
    toggleSwitch.addEventListener('change', function() {
      // Update hidden form input value
      hiddenInput.value = this.checked ? 'true' : 'false';
      
      // Submit the form
      meetingForm.submit();
    });
  }
});

// Function to toggle the session UI based on attendance state
function updateSessionUIVisibility() {
  // Get attendance buttons
  const goingBtn = document.getElementById('btn-going');
  const thinkingBtn = document.getElementById('btn-thinking');
  
  // Get UI sections
  const sessionSelectionUI = document.getElementById('session-selection-ui');
  const sessionSelectionCard = document.getElementById('session-selection-card');
  const meetingToggleContainer = document.getElementById('meeting-toggle-container');
  const saveBar = document.getElementById('saveBar');
  const sessionCountMessage = document.getElementById('sessionCountMessage');
  const thinkingMessage = document.getElementById('thinking-message');
  
  // Determine current attendance state
  const isAttending = goingBtn && goingBtn.classList.contains('btn-success');
  const isMaybe = thinkingBtn && thinkingBtn.classList.contains('btn-success');
  const isNotAttending = !isAttending && !isMaybe;
  
  // Update UI visibility based on attendance state
  
  if (sessionSelectionCard) {
    sessionSelectionCard.style.display = isNotAttending ? 'none' : 'block';
  }
  
  if (sessionSelectionUI) {
    sessionSelectionUI.style.display = (isAttending || isMaybe) ? 'block' : 'none';
  }
  
  if (meetingToggleContainer) {
    meetingToggleContainer.style.display = isAttending ? 'block' : 'none';
  }
  
  if (thinkingMessage) {
    thinkingMessage.style.display = isMaybe ? 'block' : 'none';
  }
  
  if (saveBar) {
    saveBar.style.display = isNotAttending ? 'none' : 'block';
  }
  
  if (sessionCountMessage) {
    sessionCountMessage.style.display = (isAttending || isMaybe) ? 'block' : 'none';
  }
}

// The page uses normal form submissions 
// without any special UI manipulation after click