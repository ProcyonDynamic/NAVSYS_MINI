from navwarn_mini.route_distance import load_jrc_route_csv, min_distance_vertices_to_route_waypoints

route = load_jrc_route_csv(r"D:\NAVSYS_USB\ROUTE\route.csv")
print("Loaded waypoints:", len(route))

warning_vertices = [
    (24.3645666667, -94.9659333333),
    (24.5774666667, -93.7174500000),
]

d = min_distance_vertices_to_route_waypoints(warning_vertices, route)
print("Min route distance NM:", d)