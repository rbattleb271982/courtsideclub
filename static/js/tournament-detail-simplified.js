// Rebuilt tournament detail page JavaScript - simplified session selection

document.addEventListener("DOMContentLoaded", () => {
  console.log("Tournament detail JS loaded");
  
  // Initialize feather icons if available
  if (typeof feather !== 'undefined') {
    feather.replace();
  }

  const statusInput = document.getElementById("attendance-status");
  const sessionForm = document.getElementById("session-selection-ui");
  
  console.log("Elements found:", {
    statusInput: !!statusInput,
    sessionForm: !!sessionForm
  });

  const buttons = {
    attending: document.getElementById("attending-btn"),
    maybe: document.getElementById("maybe-btn"),
    not_attending: document.getElementById("not-attending-btn"),
  };

  function updateUI(state) {
    console.log("updateUI called with state:", state);
    statusInput.value = state;
    
    const shouldShow = (state === 'attending' || state === 'maybe');
    console.log("Should show session form:", shouldShow);
    
    if (sessionForm) {
      sessionForm.style.display = shouldShow ? 'block' : 'none';
      console.log("Session form display set to:", sessionForm.style.display);
    }
    
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