// JavaScript for tournament detail page - session selection UI

document.addEventListener("DOMContentLoaded", function () {
  // Initialize feather icons if available
  if (typeof feather !== 'undefined') {
    feather.replace();
  }

  const attendingBtn = document.getElementById("attending-btn");
  const maybeBtn = document.getElementById("maybe-btn");
  const notAttendingBtn = document.getElementById("not-attending-btn");
  const sessionForm = document.getElementById("session-selection-ui");
  const attendanceInput = document.getElementById("attendance-status");

  // Set initial state based on current attendance value
  const currentAttendance = attendanceInput ? attendanceInput.value : '';
  if (currentAttendance === 'attending') {
    attendingBtn?.classList.add("btn-success");
    sessionForm.style.display = "block";
  } else if (currentAttendance === 'maybe') {
    maybeBtn?.classList.add("btn-success");
    sessionForm.style.display = "block";
  } else {
    notAttendingBtn?.classList.add("btn-success");
    sessionForm.style.display = "none";
  }

  // Attending button click handler
  attendingBtn?.addEventListener("click", function (e) {
    e.preventDefault();
    attendanceInput.value = "attending";
    sessionForm.style.display = "block";
    attendingBtn.classList.add("btn-success");
    maybeBtn.classList.remove("btn-success");
    notAttendingBtn.classList.remove("btn-success");
  });

  // Maybe button click handler
  maybeBtn?.addEventListener("click", function (e) {
    e.preventDefault();
    attendanceInput.value = "maybe";
    sessionForm.style.display = "block";
    maybeBtn.classList.add("btn-success");
    attendingBtn.classList.remove("btn-success");
    notAttendingBtn.classList.remove("btn-success");
  });

  // Not attending button click handler
  notAttendingBtn?.addEventListener("click", function (e) {
    e.preventDefault();
    attendanceInput.value = "not_attending";
    sessionForm.style.display = "none";
    notAttendingBtn.classList.add("btn-success");
    attendingBtn.classList.remove("btn-success");
    maybeBtn.classList.remove("btn-success");
  });

  // Auto-expand shared history section if accessed via anchor link
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

// Function to toggle the previous tournaments list
function togglePreviousTournaments() {
  const tournamentList = document.getElementById('tournamentList');
  const chevron = document.getElementById('chevron');
  
  if (tournamentList && chevron) {
    if (tournamentList.style.display === 'none' || tournamentList.classList.contains('collapsed')) {
      // Show the list
      tournamentList.style.display = 'block';
      tournamentList.classList.remove('collapsed');
      chevron.textContent = '▲';
    } else {
      // Hide the list
      tournamentList.style.display = 'none';
      tournamentList.classList.add('collapsed');
      chevron.textContent = '▼';
    }
  }
}