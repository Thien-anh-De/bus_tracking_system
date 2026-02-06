// ================= MAP INIT =================
const map = L.map("map").setView([21.0, 105.8], 12);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap"
}).addTo(map);

// ================= ICON =================
const busIcon = L.icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/61/61231.png",
  iconSize: [32, 32],
  iconAnchor: [16, 16]
});

// ================= STATE =================
const busMarkers = {};
const busLines = {};
const lastPos = {};   // để tránh add trùng điểm

// ================= UPDATE =================
function updateBuses() {
  fetch("http://localhost:5050/buses")
    .then(r => r.json())
    .then(buses => {
      buses.forEach(b => {
        const id = b.bus_id;
        const pos = [b.lat, b.lon];

        // ---- MARKER ----
        if (!busMarkers[id]) {
          busMarkers[id] = L.marker(pos, { icon: busIcon })
            .addTo(map)
            .bindTooltip(`Bus ${id}`, {
              permanent: true,
              direction: "top",
              offset: [0, -12]
            });

          // ---- INIT LINE ----
          busLines[id] = L.polyline([pos], {
            color: "blue",
            weight: 4
          }).addTo(map);

          lastPos[id] = pos;
          return;
        }

        // ---- UPDATE MARKER ----
        busMarkers[id].setLatLng(pos);

        // ---- APPEND LINE (KHÔNG RESET) ----
        const prev = lastPos[id];
        if (!prev || prev[0] !== pos[0] || prev[1] !== pos[1]) {
          busLines[id].addLatLng(pos);
          lastPos[id] = pos;
        }
      });
    })
    .catch(err => console.error("❌ updateBuses", err));
}

// ================= LOOP =================
setInterval(updateBuses, 2000);
