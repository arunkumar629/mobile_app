document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5s
    document.querySelectorAll('.alert').forEach(function(a) {
        setTimeout(function() { a.style.opacity = '0'; setTimeout(function() { a.remove(); }, 300); }, 5000);
    });
    // Close sidebar on mobile link click
    document.querySelectorAll('.nav-link').forEach(function(link) {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                document.getElementById('sidebar').classList.remove('open');
            }
        });
    });
});
