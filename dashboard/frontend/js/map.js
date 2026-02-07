// ================= MAP INIT =================
const map = L.map("map").setView([21.0, 105.8], 12);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19
}).addTo(map);

// ================= COLOR PALETTE =================
const COLORS = [
  "#e74c3c", // đỏ
  "#3498db", // xanh dương
  "#2ecc71", // xanh lá
  "#f39c12", // cam
  "#9b59b6", // tím
  "#1abc9c",
  "#e67e22"
];

function colorForBus(busId) {
  const idx = parseInt(busId.replace(/\D/g, "")) || 0;
  return COLORS[idx % COLORS.length];
}

// ================= ICON FACTORY =================
function createBusIcon(color) {
  return L.divIcon({
    className: "",
    html: `
      <div style="
        width: 26px;
        height: 26px;
        background: ${color};
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 0 6px rgba(0,0,0,0.5);
      "></div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13]
  });
}

// ================= STATE =================
const busMarkers = {};   // bus_id -> marker
const busState   = {};   // bus_id -> { cur, target }
const ROUTES     = {};   // route_id -> [[lat, lon]]

// ================= LOAD ROUTES =================
fetch("/routes.json")
  .then(r => r.json())
  .then(data => {
    data.forEach(r => {
      ROUTES[r.route_id] = r.points;

      // 🔵 VẼ TUYẾN CHUẨN (KHÔNG LIÊN QUAN XE)
      L.polyline(r.points, {
        color: "#1e90ff",
        weight: 5,
        opacity: 0.9
      }).addTo(map);
    });

    console.log("✅ Routes loaded");
  });

// ================= HELPER =================
function lerp(a, b, t) {
  return a + (b - a) * t;
}

// ================= SMOOTH ANIMATION LOOP =================
function animate() {
  Object.values(busState).forEach(s => {
    if (!s.cur || !s.target) return;

    s.cur[0] = lerp(s.cur[0], s.target[0], 0.12);
    s.cur[1] = lerp(s.cur[1], s.target[1], 0.12);

    busMarkers[s.id].setLatLng(s.cur);
  });

  requestAnimationFrame(animate);
}
animate();

// ================= UPDATE BUSES =================
function updateBuses() {
  fetch("/api/buses")
    .then(r => r.json())
    .then(buses => {
      buses.forEach(b => {
        const id = b.bus_id;
        const pos = [b.lat, b.lon];

        // ===== INIT =====
        if (!busMarkers[id]) {
          const color = colorForBus(id);

          busMarkers[id] = L.marker(pos, {
            icon: createBusIcon(color)
          })
            .addTo(map)
            .bindTooltip(
              `<div class="bus-label" style="background:${color}">
                Xe ${id}
              </div>`,
              {
                permanent: true,
                direction: "top",
                offset: [0, -14]
              }
            );

          busState[id] = {
            id,
            cur: [...pos],
            target: [...pos]
          };
          return;
        }

        // ===== UPDATE TARGET ONLY =====
        busState[id].target = pos;
      });
    })
    .catch(err => console.error("❌ updateBuses error", err));
}

setInterval(updateBuses, 2000);
