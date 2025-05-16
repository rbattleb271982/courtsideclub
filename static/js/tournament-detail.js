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
  
  // Update session count display and save button state
  updateSessionCountDisplay();
  updateSaveButtonState();
  
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
      if (selectedSessions.length > 0) {
        saveButton.classList.remove('btn-secondary', 'disabled');
        saveButton.classList.add('btn-success');
        saveButton.disabled = false;
      } else {
        saveButton.classList.remove('btn-success');
        saveButton.classList.add('btn-secondary', 'disabled');
        saveButton.disabled = true;
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
  attendanceButtons.forEach(button => {
    button.addEventListener('click', function() {
      // Show loading indicator on button
      const originalContent = this.innerHTML;
      this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
      this.disabled = true;
      
      // The actual state change happens via form submission, this is just for UI feedback
      // Visual updates already happen in template with page reload, but we disable temporarily
      
      // Also update UI visibility based on which button was clicked
      const attendanceType = this.dataset.attendance;
      if (attendanceType === 'attending') {
        // Going button clicked - prepare to show session UI
        document.getElementById('session-selection-ui').style.display = 'block';
        document.getElementById('meeting-toggle-container').style.display = 'block';
        document.getElementById('thinking-message').style.display = 'none';
      } else if (attendanceType === 'maybe') {
        // Thinking button clicked - hide sessions, show thinking message
        document.getElementById('session-selection-ui').style.display = 'none';
        document.getElementById('meeting-toggle-container').style.display = 'none';
        document.getElementById('thinking-message').style.display = 'block';
      } else if (attendanceType === 'not-attending') {
        // Not attending button clicked - hide everything
        document.getElementById('session-selection-card').style.display = 'none';
      }
    });
  });
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
  const isGoing = goingBtn && goingBtn.classList.contains('btn-success');
  const isThinking = thinkingBtn && thinkingBtn.classList.contains('btn-secondary');
  const isNotGoing = notGoingBtn && notGoingBtn.classList.contains('btn-secondary');
  
  // Update UI visibility based on attendance state
  if (sessionSelectionCard) {
    sessionSelectionCard.style.display = isNotGoing ? 'none' : 'block';
  }
  
  if (sessionSelectionUI) {
    sessionSelectionUI.style.display = isGoing ? 'block' : 'none';
  }
  
  if (meetingToggleContainer) {
    meetingToggleContainer.style.display = isGoing ? 'block' : 'none';
  }
  
  if (thinkingMessage) {
    thinkingMessage.style.display = isThinking ? 'block' : 'none';
  }
  
  if (saveBar) {
    saveBar.style.display = isNotGoing ? 'none' : 'block';
  }
  
  if (sessionCountMessage) {
    sessionCountMessage.style.display = isGoing ? 'block' : 'none';
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