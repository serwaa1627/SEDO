document.addEventListener('DOMContentLoaded', function () {

  // Confirm before deleting a ticket
  document.querySelectorAll('.delete-form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm('Are you sure you want to delete this ticket?')) {
        e.preventDefault();
      }
    });
  });

  // Auto-resize description textarea on edit ticket page
  const textarea = document.querySelector('textarea[name="description"]');
  if (textarea) {
    function autoResize(el) {
      el.style.height = 'auto';
      el.style.height = el.scrollHeight + 'px';
    }
    textarea.addEventListener('input', function () { autoResize(this); });
    autoResize(textarea);
  }

});
