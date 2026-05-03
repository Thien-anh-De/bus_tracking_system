// ================= MAP INIT =================
const map = L.map("map").setView([20.96, 105.76], 12);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap"
}).addTo(map);

// ================= COLORS =================
const COLORS = ["#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#e74c3c"];

// ================= GLOBAL STATE =================
const busMarkers   = {};   // bus_id -> L.Marker
const busState     = {};   // bus_id -> { lat, lon, speed, route_id }
const stopMarkers  = {};   // stop_id -> L.Marker
const ROUTES       = {};   // route_id -> [[lat, lon], ...]
const STOPS        = [];
const STOP_ROUTES  = {};   // stop_id -> [route_id]

// ================= STATUS =================
let statusEl = null;

function updateStatus(msg, type = "info") {
  if (!statusEl) {
    statusEl = document.createElement("div");
    statusEl.id = "stream-status";
    statusEl.style.cssText = `
      position:absolute; bottom:12px; left:12px; z-index:1001;
      padding:6px 12px; border-radius:20px; font-size:12px; font-weight:600;
      font-family:sans-serif; pointer-events:none; transition:opacity 0.4s;
    `;
    document.body.appendChild(statusEl);
  }
  const colors = {
    info:    { bg: "#1976d2", text: "#fff" },
    ok:      { bg: "#2ecc71", text: "#fff" },
    warn:    { bg: "#f39c12", text: "#fff" },
    error:   { bg: "#e74c3c", text: "#fff" }
  };
  const c = colors[type] || colors.info;
  statusEl.style.background = c.bg;
  statusEl.style.color = c.text;
  statusEl.textContent = msg;
}

// ================= ICONS =================
function busIcon(color, label) {
  return L.divIcon({
    html: `
      <div style="
        width:24px;height:24px;
        background:${color};
        border-radius:50%;
        border:2px solid white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        display:flex;
        align-items:center;
        justify-content:center;
        color:white;
        font-size:10px;
        font-weight:bold;
      ">${label}</div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
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


// ================= SMOOTH MARKER ANIMATION =================
/**
 * Làm mượt chuyển động marker từ vị trí hiện tại đến (toLat, toLon)
 * trong khoảng thời gian durationMs milliseconds.
 * Sử dụng requestAnimationFrame cho animation 60fps mượt mà.
 */
function animateMarker(marker, toLat, toLon, durationMs = 1400) {
  const from = marker.getLatLng();
  // Nếu khoảng cách quá lớn (teleport/data glitch), không animate, nhảy thẳng
  const distDeg = Math.sqrt(
    Math.pow(toLat - from.lat, 2) + Math.pow(toLon - from.lng, 2)
  );
  if (distDeg > 0.01) {
    marker.setLatLng([toLat, toLon]);
    return;
  }

  const startTime = performance.now();

  function easeInOut(t) {
    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
  }

  function step(now) {
    const elapsed = now - startTime;
    const t = Math.min(elapsed / durationMs, 1);
    const eased = easeInOut(t);

    marker.setLatLng([
      from.lat + (toLat - from.lat) * eased,
      from.lng + (toLon - from.lng) * eased
    ]);

    if (t < 1) {
      requestAnimationFrame(step);
    }
  }

  requestAnimationFrame(step);
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
    console.log("✅ Routes loaded:", Object.keys(ROUTES).length);
  });

// ================= LOAD STOPS =================
fetch("/api/stops")
  .then(r => r.json())
  .then(stopsData => {
    stopsData.forEach(s => {
      STOPS.push(s);
      STOP_ROUTES[s.stop_id] = (s.routes || []).map(x => x.route_id);

      stopMarkers[s.stop_id] = L.marker(
        [s.lat, s.lon],
        { icon: stopIcon }
      )
        .addTo(map)
        .bindTooltip(s.stop_name)
        .on("click", () => showETA(s));
    });
    console.log("✅ Stops loaded:", stopsData.length);
  });


// ================= ETA — GỌI BACKEND =================
/**
 * Khi user click vào bến, gọi API Backend tính ETA.
 * Backend đọc từ Redis + chạy Distance-Along-Route algorithm.
 * Frontend chỉ nhận JSON và render.
 */
function showETA(stop) {
  // Hiển thị loading state ngay lập tức
  stopMarkers[stop.stop_id]
    .unbindPopup()
    .bindPopup(`<b>${stop.stop_name}</b><br><i>Đang tính ETA...</i>`)
    .openPopup();

  fetch(`/api/stops/eta/${stop.stop_id}`)
    .then(r => r.json())
    .then(data => {
      const html =
        `<b>${data.stop_name}</b><br>` +
        (data.buses && data.buses.length
          ? data.buses.map(x =>
              `🚌 Xe <b>${x.bus_id}</b> (tuyến ${x.route_id}): <b>${x.eta_min} phút</b> · ${x.distance_km} km`
            ).join("<br>")
          : "Không có xe sắp tới");

      stopMarkers[stop.stop_id]
        .unbindPopup()
        .bindPopup(html)
        .openPopup();
    })
    .catch(err => {
      stopMarkers[stop.stop_id]
        .unbindPopup()
        .bindPopup(`<b>${stop.stop_name}</b><br><span style="color:red">Lỗi tải ETA</span>`)
        .openPopup();
      console.error("ETA error:", err);
    });
}


// ================= NEXT STOP (vẫn tính ở client) =================
function findNextStop(bus) {
  const routeStops = STOPS.filter(s =>
    (STOP_ROUTES[s.stop_id] || []).includes(bus.route_id)
  );
  if (!routeStops.length || !ROUTES[bus.route_id]) return "—";

  const route = ROUTES[bus.route_id];

  // Tính khoảng cách dọc tuyến đơn giản để tìm bến tiếp theo
  let bestDist = Infinity;
  let bestName = "—";
  const busAcc  = routeDist(route, bus.lat, bus.lon);

  routeStops.forEach(s => {
    const stopAcc = routeDist(route, s.lat, s.lon);
    if (stopAcc > busAcc && stopAcc < bestDist) {
      bestDist = stopAcc;
      bestName = s.stop_name;
    }
  });
  return bestName;
}

function routeDist(route, lat, lon) {
  const R = 6371;
  let acc = 0, best = 0, minErr = Infinity;
  for (let i = 0; i < route.length - 1; i++) {
    const [aLat, aLon] = route[i];
    const [bLat, bLon] = route[i + 1];
    const ab = hv(aLat, aLon, bLat, bLon);
    const ax = hv(aLat, aLon, lat, lon);
    const xb = hv(lat, lon, bLat, bLon);
    const err = Math.abs(ab - (ax + xb));
    if (err < minErr) { minErr = err; best = acc + ax; }
    acc += ab;
  }
  return best;
}

function hv(lat1, lon1, lat2, lon2) {
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


// ================= XỬ LÝ DATA TỪ SSE/FALLBACK =================
let busColorMap = {};

function processBusUpdate(buses) {
  const now = Date.now();
  const panel = document.getElementById("bus-list");
  panel.innerHTML = "";

  buses.forEach((b, i) => {
    if (!busColorMap[b.bus_id]) {
      busColorMap[b.bus_id] = COLORS[Object.keys(busColorMap).length % COLORS.length];
    }
    const color = busColorMap[b.bus_id];
    const updatedAt = new Date(b.updated_at).getTime();
    const online = !isNaN(updatedAt) ? (now - updatedAt < 30000) : true;

    if (!busMarkers[b.bus_id]) {
      // Tạo marker lần đầu
      busMarkers[b.bus_id] = L.marker(
        [b.lat, b.lon],
        { icon: busIcon(color, b.bus_id) }
      ).addTo(map);
    } else {
      // Animate mượt sang vị trí mới
      animateMarker(busMarkers[b.bus_id], b.lat, b.lon, 1400);
    }

    busState[b.bus_id] = {
      id: b.bus_id,
      lat: b.lat,
      lon: b.lon,
      speed: b.speed,
      route_id: b.route_id
    };

    const nextStop = findNextStop(busState[b.bus_id]);
    const statusClass = online ? "status-online" : "status-offline";

    panel.innerHTML += `
      <div class="bus-card">
        <div class="bus-header">
          <span class="bus-id">
            <span class="status-dot ${statusClass}"></span>
            🚌 Xe ${b.bus_id}
          </span>
          <span class="bus-speed">${b.speed} km/h</span>
        </div>
        <div class="bus-next-stop">
          <span class="icon-arrow">→</span>
          Bến tới: <span>${nextStop}</span>
        </div>
      </div>
    `;
  });
}


// ================= SSE CONNECTION =================
/**
 * Kết nối Server-Sent Events.
 * Thay thế hoàn toàn setInterval + fetch.
 * Browser tự động reconnect nếu mất kết nối.
 */
function connectSSE() {
  updateStatus("⚡ Đang kết nối realtime...", "info");

  const evtSource = new EventSource("/api/stream/buses");

  evtSource.onopen = () => {
    console.log("✅ SSE connected");
    updateStatus("✅ Realtime · SSE", "ok");
  };

  evtSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (Array.isArray(data)) {
        processBusUpdate(data);
      }
    } catch (e) {
      console.warn("SSE parse error:", e);
    }
  };

  evtSource.onerror = (err) => {
    console.warn("SSE error, browser will auto-reconnect...", err);
    updateStatus("⚠ Mất kết nối, đang thử lại...", "warn");
  };
}

// Khởi động SSE khi trang load xong
connectSSE();
