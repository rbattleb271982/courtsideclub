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
        // Remove from selected sessions with visual feedback
        this.classList.remove('selected');
        
        // Add a brief transition effect for visual feedback
        this.style.transition = 'all 0.2s ease-out';
        
        // Remove from array
        const index = selectedSessions.indexOf(sessionValue);
        if (index > -1) {
          selectedSessions.splice(index, 1);
        }
      } else {
        // Add to selected sessions with visual feedback
        this.classList.add('selected');
        
        // Add a brief transition effect for visual feedback
        this.style.transition = 'all 0.2s ease-in';
        
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
    const selectedButtons = document.querySelectorAll('.session-chip.selected');
    
    if (saveButton) {
      if (selectedButtons.length > 0) {
        // Has sessions, use solid green button
        saveButton.classList.remove('btn-outline-success');
        saveButton.classList.add('btn-success');
      } else {
        // No sessions selected, use outline button
        saveButton.classList.remove('btn-success');
        saveButton.classList.add('btn-outline-success');
      }
      
      // Always enable the save button
      saveButton.classList.remove('disabled', 'btn-secondary');
      saveButton.disabled = false;
      
      // Update selectedSessions array based on actual DOM state
      selectedSessions = [];
      selectedButtons.forEach(button => {
        selectedSessions.push(button.dataset.session);
      });
    }
  }
  
  // Handle form submission
  const saveButton = document.getElementById('saveButton');
  const sessionForm = document.getElementById('sessionForm');
  
  if (sessionForm) {
    // Handle form submission
    sessionForm.addEventListener('submit', function(e) {
      // Allow submission even if no sessions selected
      
      // Show loading state on button if it exists
      if (saveButton) {
        saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
        saveButton.disabled = true;
      }
      
      // Clear previous hidden inputs and rebuild
      const hiddenInputsContainer = document.getElementById('hiddenSessionInputs');
      if (hiddenInputsContainer) {
        // Clear only dynamically added ones, not the preselected ones from server
        const existingInputs = hiddenInputsContainer.querySelectorAll('input[name="sessions"]');
        existingInputs.forEach(input => input.remove());
        
        // Create hidden inputs for each selected session
        selectedSessions.forEach(session => {
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = 'sessions';
          input.value = session;
          hiddenInputsContainer.appendChild(input);
        });
        
        // Set the wants_to_meet hidden input value from checkbox
        const meetingCheckbox = document.getElementById('wants-to-meet-top');
        const wantsToMeetHidden = document.getElementById('wants_to_meet_hidden');
        if (meetingCheckbox && wantsToMeetHidden) {
          wantsToMeetHidden.value = meetingCheckbox.checked ? 'true' : 'false';
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
  const lanyardButton = document.querySelector('.lanyard-button');
  
  // Determine current attendance state
  const isAttending = goingBtn && goingBtn.classList.contains('btn-success');
  const isMaybe = thinkingBtn && thinkingBtn.classList.contains('btn-success');
  const isNotAttending = !isAttending && !isMaybe;
  
  // Check if we have selected sessions
  const selectedSessionCount = document.querySelectorAll('.session-chip.selected').length;
  const hasSelectedSessions = selectedSessionCount > 0;
  
  // Update UI visibility based on attendance state
  if (sessionSelectionCard) {
    sessionSelectionCard.style.display = isNotAttending ? 'none' : 'block';
  }
  
  if (sessionSelectionUI) {
    // Show session UI for both attending and maybe attending users
    sessionSelectionUI.style.display = (isAttending || isMaybe) ? 'block' : 'none';
  }
  
  if (meetingToggleContainer) {
    // Show meeting toggle for both attending and maybe attending users
    meetingToggleContainer.style.display = (isAttending || isMaybe) ? 'block' : 'none';
  }
  
  if (thinkingMessage) {
    // Hide thinking message - we always show session selection UI now
    thinkingMessage.style.display = 'none';
  }
  
  if (saveBar) {
    saveBar.style.display = isNotAttending ? 'none' : 'block';
  }
  
  if (sessionCountMessage) {
    sessionCountMessage.style.display = (isAttending || isMaybe) ? 'block' : 'none';
  }
  
  // Update save button state based on selected sessions
  updateSaveButtonState();
}

// The page uses normal form submissions 
// without any special UI manipulation after click