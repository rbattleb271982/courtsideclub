// JavaScript for improving tournament detail page experience

document.addEventListener('DOMContentLoaded', function() {
  // Initialize feather icons
  if (typeof feather !== 'undefined') {
    feather.replace();
  }
  
  // Add click handlers for session checkboxes to improve visual feedback
  const sessionCheckboxes = document.querySelectorAll('.session-checkbox');
  sessionCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', function() {
      const label = this.closest('.form-check').querySelector('.form-check-label span');
      if (this.checked) {
        label.classList.add('font-weight-bold', 'text-success');
        // Add checkmark if it doesn't exist
        if (!label.querySelector('.text-success')) {
          const checkmark = document.createElement('span');
          checkmark.className = 'text-success';
          checkmark.textContent = '✓';
          label.appendChild(document.createTextNode(' '));
          label.appendChild(checkmark);
        }
      } else {
        label.classList.remove('font-weight-bold', 'text-success');
        // Remove checkmark if it exists
        const checkmark = label.querySelector('.text-success');
        if (checkmark) {
          checkmark.remove();
        }
      }
      
      // Update selected session count message
      updateSelectedSessionCount();
    });
  });
  
  // Function to update the session count message
  function updateSelectedSessionCount() {
    const checkedCount = document.querySelectorAll('.session-checkbox:checked').length;
    const countMessage = document.querySelector('.save-preferences p');
    
    if (countMessage) {
      if (checkedCount > 0) {
        countMessage.innerHTML = `
          <span class="text-success font-weight-bold">
            <i data-feather="check-circle" class="icon-sm"></i>
            You've selected ${checkedCount} session${checkedCount !== 1 ? 's' : ''}
          </span>
        `;
      } else {
        countMessage.innerHTML = `
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
  
  // Create sticky save button for mobile
  const savePreferences = document.querySelector('.save-preferences');
  if (savePreferences && window.innerWidth < 768) {
    savePreferences.classList.add('fixed-bottom', 'mb-0', 'rounded-0');
    savePreferences.style.zIndex = '1000';
    document.body.style.paddingBottom = '100px'; // Add padding to prevent content being hidden
  }
});