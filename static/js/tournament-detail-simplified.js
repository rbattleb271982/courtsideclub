// Rebuilt tournament detail page JavaScript - simplified session selection

document.addEventListener("DOMContentLoaded", () => {
  // Initialize feather icons if available
  if (typeof feather !== 'undefined') {
    feather.replace();
  }

  const statusInput = document.getElementById("attendance-status");
  const sessionForm = document.getElementById("session-selection-ui");

  const buttons = {
    attending: document.getElementById("attending-btn"),
    maybe: document.getElementById("maybe-btn"),
    not_attending: document.getElementById("not-attending-btn"),
  };

  function updateUI(state) {
    statusInput.value = state;
    sessionForm.style.display = (state === 'attending' || state === 'maybe') ? 'block' : 'none';
    Object.keys(buttons).forEach(key => {
      buttons[key].classList.remove("btn-success");
      if (key === state) {
        buttons[key].classList.add("btn-success");
      }
    });
  }

  Object.entries(buttons).forEach(([key, btn]) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      updateUI(key);
    });
  });

  // Set initial state
  updateUI(statusInput.value || 'not_attending');

  // Keep existing functionality for other features
  if (window.location.hash === '#shared-history') {
    const tournamentList = document.getElementById('tournamentList');
    const chevron = document.getElementById('chevron');
    if (tournamentList && chevron) {
      tournamentList.style.display = 'block';
      tournamentList.classList.remove('collapsed');
      chevron.textContent = '▲';
    }
  }
});

// Keep existing function for tournament history toggle
function togglePreviousTournaments() {
  const tournamentList = document.getElementById('tournamentList');
  const chevron = document.getElementById('chevron');
  
  if (tournamentList && chevron) {
    if (tournamentList.style.display === 'none' || tournamentList.classList.contains('collapsed')) {
      tournamentList.style.display = 'block';
      tournamentList.classList.remove('collapsed');
      chevron.textContent = '▲';
    } else {
      tournamentList.style.display = 'none';
      tournamentList.classList.add('collapsed');
      chevron.textContent = '▼';
    }
  }
}