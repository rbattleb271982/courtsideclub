// Simplified JavaScript for tournament detail page

document.addEventListener('DOMContentLoaded', function() {
  // Initialize feather icons if available
  if (typeof feather !== 'undefined') {
    feather.replace();
  }
  
  // Initialize UI visibility based on attendance state
  updateSessionUIVisibility();
  
  // Add event listener to the meeting toggle
  const meetingToggle = document.getElementById('wants-to-meet-top');
  const wantsToMeetHidden = document.getElementById('wants_to_meet_hidden');
  
  if (meetingToggle && wantsToMeetHidden) {
    meetingToggle.addEventListener('change', function() {
      wantsToMeetHidden.value = this.checked ? 'true' : 'false';
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
}