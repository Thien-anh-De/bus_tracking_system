// ================= MAP INIT =================
const map = L.map("map").setView([20.96, 105.76], 12);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap"
}).addTo(map);

// ================= COLORS =================
const COLORS = ["#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#e74c3c"];

// ================= GLOBAL STATE =================
const busMarkers = {};
const busState = {};
const stopMarkers = {};
const ROUTES = {};
const STOPS = [];
const STOP_ROUTES = {};   // stop_id -> [route_id]

// ================= ICONS =================
function busIcon(color, label) {
  return L.divIcon({
    html: `
      <div style="
        width:22px;height:22px;
        background:${color};
        border-radius:50%;
        border:2px solid white;
        display:flex;
        align-items:center;
        justify-content:center;
        color:white;
        font-size:10px;
        font-weight:bold;
      ">${label}</div>
    `,
    iconSize: [22, 22],
    iconAnchor: [11, 11]
  });
}

const stopIcon = L.divIcon({
  html: `
    <div style="
      width:14px;
      height:14px;
      background:#1e88e5;
      border:3px solid white;
      border-radius:50%;
      box-shadow:0 0 4px rgba(0,0,0,.4);
    "></div>
  `,
  iconSize: [14, 14],
  iconAnchor: [7, 7]
});


// ================= HELPERS =================
function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat/2)**2 +
    Math.cos(lat1*Math.PI/180) *
    Math.cos(lat2*Math.PI/180) *
    Math.sin(dLon/2)**2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// khoảng cách dọc theo tuyến
function distanceAlongRoute(route, lat, lon) {
  let acc = 0;
  let best = 0;
  let minErr = Infinity;

  for (let i = 0; i < route.length - 1; i++) {
    const [aLat, aLon] = route[i];
    const [bLat, bLon] = route[i + 1];

    const ab = haversine(aLat, aLon, bLat, bLon);
    const ax = haversine(aLat, aLon, lat, lon);
    const xb = haversine(lat, lon, bLat, bLon);

    const err = Math.abs(ab - (ax + xb));
    if (err < minErr) {
      minErr = err;
      best = acc + ax;
    }
    acc += ab;
  }
  return best;
}

// ================= LOAD ROUTES =================
fetch("/routes.json")
  .then(r => r.json())
  .then(data => {
    data.forEach(r => {
      ROUTES[r.route_id] = r.points;
      L.polyline(r.points, {
        color: "#1976d2",
        weight: 5,
        opacity: 0.85
      }).addTo(map);
    });
    console.log("✅ routes loaded");
  });

// ================= LOAD STOPS (FIX ĐÚNG ROUTE) =================
fetch("/api/stops")
  .then(r => r.json())
  .then(stops => {
    stops.forEach(s => {
      STOPS.push(s);

      // ✅ FIX LỖI GỐC: backend trả "routes", không phải "route_ids"
      STOP_ROUTES[s.stop_id] = (s.routes || []).map(x => x.route_id);

      stopMarkers[s.stop_id] = L.marker(
        [s.lat, s.lon],
        { icon: stopIcon }
      )
        .addTo(map)
        .bindTooltip(s.stop_name)
        .on("click", () => showETA(s));
    });

    console.log("✅ stops loaded", STOP_ROUTES);
  });

// ================= ETA (CHỈ XE ĐÚNG TUYẾN) =================
function showETA(stop) {
  const list = [];
  const validRoutes = STOP_ROUTES[stop.stop_id] || [];

  Object.values(busState).forEach(b => {
    if (!validRoutes.includes(b.route_id)) return;
    if (!b.speed || b.speed <= 0) return;

    const route = ROUTES[b.route_id];
    if (!route) return;

    const busD  = distanceAlongRoute(route, b.lat, b.lon);
    const stopD = distanceAlongRoute(route, stop.lat, stop.lon);

    if (busD >= stopD) return;

    const eta = ((stopD - busD) / b.speed) * 60;
    if (eta < 30) list.push({ id: b.id, route: b.route_id, eta });
  });

  list.sort((a,b)=>a.eta-b.eta);

  const html =
    `<b>${stop.stop_name}</b><br>` +
    (list.length
      ? list.map(x =>
          `🚌 Xe ${x.id} (tuyến ${x.route}): <b>${x.eta.toFixed(1)} phút</b>`
        ).join("<br>")
      : "Không có xe sắp tới");

  stopMarkers[stop.stop_id]
    .unbindPopup()
    .bindPopup(html)
    .openPopup();
}

// ================= NEXT STOP =================
function findNextStop(bus) {
  const routeStops = STOPS.filter(s =>
    (STOP_ROUTES[s.stop_id] || []).includes(bus.route_id)
  );

  if (!routeStops.length) return "—";

  const route = ROUTES[bus.route_id];
  if (!route) return "—";

  const busD = distanceAlongRoute(route, bus.lat, bus.lon);

  let best = null;
  let bestDist = Infinity;

  routeStops.forEach(s => {
    const d = distanceAlongRoute(route, s.lat, s.lon);
    if (d > busD && d < bestDist) {
      bestDist = d;
      best = s;
    }
  });

  return best ? best.stop_name : "—";
}

// ================= UPDATE BUSES + PANEL =================
function updateBuses() {
  fetch("/api/buses")
    .then(r => r.json())
    .then(buses => {
      const now = Date.now();
      const panel = document.getElementById("bus-list");
      panel.innerHTML = "";

      buses.forEach((b, i) => {
        const color = COLORS[i % COLORS.length];
        const updatedAt = new Date(b.updated_at).getTime();
        const online = now - updatedAt < 30000;

        if (!busMarkers[b.bus_id]) {
          busMarkers[b.bus_id] = L.marker(
            [b.lat, b.lon],
            { icon: busIcon(color, b.bus_id) }
          ).addTo(map);
        }

        busMarkers[b.bus_id].setLatLng([b.lat, b.lon]);

        busState[b.bus_id] = {
          id: b.bus_id,
          lat: b.lat,
          lon: b.lon,
          speed: b.speed,
          route_id: b.route_id
        };

        panel.innerHTML += `
          <div class="bus-row">
            🚌 <b>${b.bus_id}</b> |
            ${b.speed} km/h |
            ➡️ Bến tới: <b>${findNextStop(busState[b.bus_id])}</b>
          </div>
        `;
      });
    })
    .catch(err => console.error(err));
}

setInterval(updateBuses, 2000);
