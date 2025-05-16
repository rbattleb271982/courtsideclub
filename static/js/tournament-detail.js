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
  
  // Update session count display
  updateSessionCountDisplay();
  
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
      
      // Update session count display
      updateSessionCountDisplay();
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
  
  // Handle save button click
  const saveButton = document.getElementById('saveButton');
  const sessionForm = document.getElementById('sessionForm');
  
  if (saveButton && sessionForm) {
    saveButton.addEventListener('click', function() {
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
      
      // Submit the form
      sessionForm.submit();
    });
  }
  
  // Handle toggle behavior for "I'm open to meeting" button
  const meetingToggleBtn = document.querySelector('.meeting-toggle button');
  const meetingCheckbox = document.getElementById('wants-to-meet-top');
  
  if (meetingToggleBtn && meetingCheckbox) {
    meetingToggleBtn.addEventListener('click', function(e) {
      e.preventDefault(); // Prevent form submission
      meetingCheckbox.checked = !meetingCheckbox.checked;
      
      // Update button styling
      if (meetingCheckbox.checked) {
        this.classList.remove('btn-outline-info');
        this.classList.add('btn-info');
        this.querySelector('span span:last-child').textContent = "I'm open to meeting other fans";
      } else {
        this.classList.remove('btn-info');
        this.classList.add('btn-outline-info');
        this.querySelector('span span:last-child').textContent = "Meet other fans?";
      }
    });
  }
});