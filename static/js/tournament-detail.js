document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('.toggle-btn');
  const statusInput = document.getElementById('status-input');
  const sessionUI = document.getElementById('session-selection');
  const checkboxes = document.querySelectorAll('input[type="checkbox"][name="sessions"]');
  const chipContainer = document.getElementById('selected-session-chips');

  // Handle attendance toggle buttons
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      // Remove selected class from all buttons
      buttons.forEach(b => b.classList.remove('selected'));
      // Add selected class to clicked button
      btn.classList.add('selected');
      
      // Update hidden status input
      const status = btn.dataset.status;
      statusInput.value = status;

      // Show/hide session selection based on status
      if (status === 'attending' || status === 'maybe') {
        sessionUI.style.display = 'block';
      } else {
        sessionUI.style.display = 'none';
      }
    });
  });

  // Handle session checkbox changes - update chips dynamically
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      const selected = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

      // Clear existing chips
      chipContainer.innerHTML = '';
      
      // Add new chips for selected sessions
      selected.forEach(label => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.textContent = label;
        chipContainer.appendChild(chip);
      });
    });
  });
});