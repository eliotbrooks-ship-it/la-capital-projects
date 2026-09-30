// Project map. Uses the vendored Leaflet 1.9.4 (reviewed 2026-09-30) and OpenStreetMap tiles,
// following the OSMF tile usage policy: visible attribution, no bulk or offline tile downloads.
(function () {
  var BASE = window.LACP_BASE || '/';
  var TYPES = window.LACP_TYPES || {};
  var COLORS = {
    data_center: '#3b6fd4', lng: '#0f8a7a', chemicals: '#8a4fc4', ammonia_hydrogen: '#2e9e3f',
    steel_metals: '#6b7280', manufacturing: '#c26a16', spaceport_aerospace: '#c2334d',
    power_generation: '#d4a017', infrastructure: '#4b5563', other: '#9ca3af'
  };
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function usd(v) { return v >= 1e9 ? '$' + (+(v / 1e9).toFixed(1)) + 'B' : '$' + Math.round(v / 1e6) + 'M'; }

  function init() {
    var map = L.map('map', { scrollWheelZoom: false }).setView([30.9, -91.9], 7);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    fetch(BASE + 'data/projects.geojson').then(function (r) { return r.json(); }).then(function (gj) {
      var used = {};
      var layer = L.geoJSON(gj, {
        pointToLayer: function (f, latlng) {
          used[f.properties.type] = true;
          return L.circleMarker(latlng, {
            radius: Math.max(6, Math.min(16, Math.log10(f.properties.headline_capex_usd) * 2 - 12)),
            color: '#fff', weight: 1.5, fillColor: COLORS[f.properties.type] || COLORS.other, fillOpacity: 0.9
          });
        },
        onEachFeature: function (f, l) {
          var p = f.properties;
          l.bindPopup('<strong><a href="' + BASE + 'projects/' + esc(p.id) + '/">' + esc(p.name) + '</a></strong><br>' +
            esc(TYPES[p.type] || p.type) + ' · ' + esc(p.parish) + ' Parish<br>' + usd(p.headline_capex_usd) +
            (p.location_precision !== 'exact' ? '<br><em>Approximate location</em>' : ''));
        }
      }).addTo(map);
      if (gj.features.length) map.fitBounds(layer.getBounds().pad(0.2));
      var legend = document.getElementById('legend');
      Object.keys(used).forEach(function (t) {
        var li = document.createElement('li');
        li.innerHTML = '<span class="dot" style="background:' + COLORS[t] + '"></span>' + esc(TYPES[t] || t);
        legend.appendChild(li);
      });
    });
  }
  if (window.L) init(); else window.addEventListener('load', init);
})();
