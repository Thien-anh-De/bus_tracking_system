from db_reader import get_route_id_by_bus, get_stops_by_route_id

print("Route of bus 01:", get_route_id_by_bus("01"))
print("Stops of route 1:")
for s in get_stops_by_route_id(1):
    print(s)
