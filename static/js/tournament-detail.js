document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('.attendance-toggle');
  const statusInput = document.getElementById('attendance-status');
  const sessionUI = document.getElementById('session-selection');
  const checkboxes = document.querySelectorAll('input[type="checkbox"][name="sessions"]');
  const chipList = document.getElementById('selected-session-chips');

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      const status = btn.dataset.status;
      statusInput.value = status;

      if (status === 'attending' || status === 'maybe') {
        sessionUI.style.display = 'block';
      } else {
        sessionUI.style.display = 'none';
      }
    });
  });

  checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      const selected = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

      chipList.innerHTML = '';
      selected.forEach(label => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.textContent = label;
        chipList.appendChild(chip);
      });
    });
  });
});