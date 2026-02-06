const busMarkers = {};
const busLines = {};
const MAX_JUMP_METERS = 500;

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = x => x * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) ** 2;

  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function updateBuses() {
    fetch("/api/buses")
    .then(r => r.json())
    .then(buses => {
      buses.forEach(b => {
        const pos = [b.lat, b.lon];

        if (!busMarkers[b.bus_id]) {
          busMarkers[b.bus_id] = L.marker(pos, { icon: busIcon })
            .addTo(map)
            .bindTooltip(`Bus ${b.bus_id}`, {
              permanent: true,
              direction: "top",
              offset: [0, -18]
            });

          busLines[b.bus_id] = L.polyline([pos], {
            color: "blue",
            weight: 4
          }).addTo(map);
          return;
        }

        const prev = busMarkers[b.bus_id].getLatLng();
        const dist = haversine(prev.lat, prev.lng, b.lat, b.lon);

        if (dist > MAX_JUMP_METERS) {
          busLines[b.bus_id].setLatLngs([pos]);
        } else {
          busLines[b.bus_id].addLatLng(pos);
        }

        busMarkers[b.bus_id].setLatLng(pos);
      });
    })
    .catch(err => console.error("❌ updateBuses", err));
}

setInterval(updateBuses, 2000);
