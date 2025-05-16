// JavaScript for improving tournament detail page experience

document.addEventListener('DOMContentLoaded', function() {
  // Initialize feather icons
  if (typeof feather !== 'undefined') {
    feather.replace();
  }
  
  // Track selected sessions
  let selectedSessions = [];
  
  // Initialize selected sessions from existing state
  document.querySelectorAll('.session-toggle.selected').forEach(toggle => {
    selectedSessions.push(toggle.dataset.session);
  });
  
  // Update session count display and save button state
  updateSessionCountDisplay();
  updateSaveButtonState();
  
  // Add sticky behavior to save bar on mobile
  if (window.innerWidth < 768) {
    document.body.classList.add('has-sticky-bar');
  }
  
  // Add click handlers for session toggle buttons
  const sessionToggles = document.querySelectorAll('.session-toggle');
  sessionToggles.forEach(toggle => {
    toggle.addEventListener('click', function() {
      const sessionValue = this.dataset.session;
      
      if (this.classList.contains('selected')) {
        // Remove from selected sessions
        this.classList.remove('selected');
        this.classList.add('unselected');
        this.querySelector('.toggle-icon').textContent = '+';
        
        // Remove from array
        const index = selectedSessions.indexOf(sessionValue);
        if (index > -1) {
          selectedSessions.splice(index, 1);
        }
      } else {
        // Add to selected sessions
        this.classList.remove('unselected');
        this.classList.add('selected');
        this.querySelector('.toggle-icon').textContent = '✓';
        
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
});

// Function to toggle meeting button appearance
function toggleMeetingButton(button) {
  const meetingCheckbox = document.getElementById('wants-to-meet-top');
  if (!meetingCheckbox) return;
  
  if (meetingCheckbox.checked) {
    button.classList.remove('btn-outline-success');
    button.classList.add('btn-success');
    button.querySelector('span span:last-child').textContent = "I'm open to meeting other fans";
  } else {
    button.classList.remove('btn-success');
    button.classList.add('btn-outline-success');
    button.querySelector('span span:last-child').textContent = "Meet other fans?";
  }
}