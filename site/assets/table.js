// Client-side filtering, sorting and CSV export for /projects/. No dependencies.
(function () {
  var form = document.getElementById('filters');
  var table = document.getElementById('projects');
  if (!form || !table) return;
  var tbody = table.tBodies[0];
  var rows = Array.prototype.slice.call(tbody.rows);
  var count = document.getElementById('count');

  function apply() {
    var f = new FormData(form);
    var min = Number(f.get('min') || 0);
    var shown = 0;
    rows.forEach(function (r) {
      var ok = ['type', 'parish', 'status', 'tier', 'confidence'].every(function (k) {
        var v = f.get(k);
        return !v || r.dataset[k] === v;
      }) && Number(r.dataset.capex) >= min;
      r.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = shown;
  }
  form.addEventListener('change', apply);

  var dir = {};
  Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th, i) {
    var key = th.dataset.key;
    if (!key) return;
    th.setAttribute('tabindex', '0');
    th.setAttribute('role', 'button');
    function sort() {
      dir[key] = dir[key] === 1 ? -1 : 1;
      rows.sort(function (a, b) {
        var x = key === 'capex' ? Number(a.dataset.capex) : a.cells[i].innerText.toLowerCase();
        var y = key === 'capex' ? Number(b.dataset.capex) : b.cells[i].innerText.toLowerCase();
        return (x > y ? 1 : x < y ? -1 : 0) * dir[key];
      });
      rows.forEach(function (r) { tbody.appendChild(r); });
    }
    th.addEventListener('click', sort);
    th.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sort(); } });
  });

  document.getElementById('dl-csv').addEventListener('click', function (e) {
    e.preventDefault();
    var head = ['Project', 'Owner', 'Type', 'Parish', 'Status', 'Value (USD)', 'Tier', 'Confidence', 'URL'];
    var lines = [head];
    rows.filter(function (r) { return !r.hidden; }).forEach(function (r) {
      var c = r.cells;
      lines.push([c[0].querySelector('a').innerText, c[0].querySelector('.muted').innerText, c[1].innerText,
        c[2].innerText, c[3].innerText, r.dataset.capex, c[5].innerText, c[6].innerText, c[0].querySelector('a').href]);
    });
    var csv = lines.map(function (l) {
      return l.map(function (v) { return '"' + String(v).replace(/"/g, '""') + '"'; }).join(',');
    }).join('\n');
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = 'la-capital-projects-filtered.csv';
    document.body.appendChild(a); a.click(); a.remove();
  });
})();
