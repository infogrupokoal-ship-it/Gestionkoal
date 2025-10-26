document.addEventListener('DOMContentLoaded', function() {
  try {
    var token = window.csrf_token || (typeof CSRF_TOKEN !== 'undefined' ? CSRF_TOKEN : null);
    if (!token) {
      // Intentar leer desde una meta tag opcional si existiera
      var meta = document.querySelector('meta[name="csrf-token"]');
      if (meta) token = meta.getAttribute('content');
    }
    if (!token) return;
    document.querySelectorAll('form[method="post"]').forEach(function(f){
      if (f.querySelector('input[name="csrf_token"]')) return;
      var i = document.createElement('input');
      i.type = 'hidden'; i.name = 'csrf_token'; i.value = token;
      f.appendChild(i);
    });
  } catch(e) { /* noop */ }
});

