// JavaScript for improving tournament detail page experience with checkbox-based UI

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
  
  // Initialize session save bar
  const sessionSaveBar = document.getElementById('session-save-bar');
  const sessionCountBar = document.getElementById('session-count');
  
  // Get all session checkboxes
  const sessionCheckboxes = document.querySelectorAll('input[name="sessions"]');
  
  // Initial update of session count and save bar visibility
  updateSessionCountDisplay();
  
  // Add event listeners to all session checkboxes
  sessionCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', function() {
      // Visual feedback on the parent label
      const label = this.closest('.session-checkbox');
      if (label) {
        // Trigger animation effect
        label.classList.remove('just-toggled');
        void label.offsetWidth; // Force reflow
        label.classList.add('just-toggled');
      }
      
      // Update display
      updateSessionCountDisplay();
    });
  });
  
  // Add event listener to the meeting toggle
  const meetingToggle = document.getElementById('wants-to-meet-top');
  const wantsToMeetHidden = document.getElementById('wants_to_meet_hidden');
  
  if (meetingToggle && wantsToMeetHidden) {
    meetingToggle.addEventListener('change', function() {
      wantsToMeetHidden.value = this.checked ? 'true' : 'false';
    });
  }
  
  // Function to update the session count display and save bar visibility
  function updateSessionCountDisplay() {
    const checkedSessions = document.querySelectorAll('input[name="sessions"]:checked');
    const sessionCount = checkedSessions.length;
    const sessionCountElement = document.getElementById('sessionCountMessage');
    
    // Update the regular session count message if it exists
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
    
    // Update the session save bar
    if (sessionSaveBar && sessionCountBar) {
      if (sessionCount > 0) {
        // Show the save bar and update the text
        sessionSaveBar.style.bottom = '0';
        sessionCountBar.textContent = `✔️ ${sessionCount} session${sessionCount !== 1 ? 's' : ''} selected`;
      } else {
        // Hide the save bar
        sessionSaveBar.style.bottom = '-100px';
      }
    }
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
}