import sys
import math
import heapq

import rasterio


NEIGHBORS = [
    (-1, -1),
    (-1,  0),
    (-1,  1),
    ( 0, -1),
    ( 0,  1),
    ( 1, -1),
    ( 1,  0),
    ( 1,  1),
]


def node_id(row, col, width):
    return row * width + col


def row_col(node, width):
    return divmod(node, width)


def heuristic(row, col, goal_row, goal_col, resolution):
    """
    Euclidean lower-bound distance to the goal.
    """
    dr = goal_row - row
    dc = goal_col - col

    return math.sqrt(
        dr * dr + dc * dc
    ) * resolution


def movement_distance(dr, dc, resolution):
    """
    Physical movement distance between neighboring cells.
    """
    if dr != 0 and dc != 0:
        return math.sqrt(2.0) * resolution

    return resolution


def reconstruct_path(came_from, current):
    path = [current]

    while current in came_from:
        current = came_from[current]
        path.append(current)

    path.reverse()

    return path


def find_nearest_valid(cost, row, col, nodata, max_radius=25):
    """
    If a requested start/goal cell is unavailable,
    search nearby for a valid routing cell.
    """

    height, width = cost.shape

    for radius in range(max_radius + 1):

        r_min = max(0, row - radius)
        r_max = min(height - 1, row + radius)

        c_min = max(0, col - radius)
        c_max = min(width - 1, col + radius)

        for r in range(r_min, r_max + 1):

            for c in range(c_min, c_max + 1):

                value = cost[r, c]

                if nodata is not None and value == nodata:
                    continue

                if not math.isfinite(float(value)):
                    continue

                return r, c

    return None


def run_astar(
    raster_path,
    start_row,
    start_col,
    goal_row,
    goal_col,
    output_path,
):

    print("=" * 60)
    print("MARSWALK A* ROUTE ENGINE")
    print("=" * 60)

    with rasterio.open(raster_path) as src:

        cost = src.read(1)

        height = src.height
        width = src.width
        resolution = src.res[0]
        nodata = src.nodata

        print()
        print("ROUTING SURFACE")
        print("-" * 60)
        print(f"Raster:       {raster_path}")
        print(f"Width:        {width}")
        print(f"Height:       {height}")
        print(f"Resolution:   {resolution} m")
        print(f"NoData:       {nodata}")

        # --------------------------------------------------
        # Validate requested coordinates
        # --------------------------------------------------

        if not (
            0 <= start_row < height
            and 0 <= start_col < width
        ):
            raise ValueError("Start coordinate outside raster.")

        if not (
            0 <= goal_row < height
            and 0 <= goal_col < width
        ):
            raise ValueError("Goal coordinate outside raster.")

        # --------------------------------------------------
        # Find valid start
        # --------------------------------------------------

        start = find_nearest_valid(
            cost,
            start_row,
            start_col,
            nodata,
        )

        if start is None:
            raise RuntimeError(
                "Unable to find valid start location."
            )

        # --------------------------------------------------
        # Find valid goal
        # --------------------------------------------------

        goal = find_nearest_valid(
            cost,
            goal_row,
            goal_col,
            nodata,
        )

        if goal is None:
            raise RuntimeError(
                "Unable to find valid goal location."
            )

        start_row, start_col = start
        goal_row, goal_col = goal

        start_node = node_id(
            start_row,
            start_col,
            width,
        )

        goal_node = node_id(
            goal_row,
            goal_col,
            width,
        )

        print()
        print("START / GOAL")
        print("-" * 60)
        print(
            f"Start requested: "
            f"({start[0]}, {start[1]})"
        )

        print(
            f"Goal requested:  "
            f"({goal[0]}, {goal[1]})"
        )

        # --------------------------------------------------
        # A* initialization
        # --------------------------------------------------

        open_set = []

        heapq.heappush(
            open_set,
            (
                heuristic(
                    start_row,
                    start_col,
                    goal_row,
                    goal_col,
                    resolution,
                ),
                start_node,
            ),
        )

        came_from = {}

        g_score = {
            start_node: 0.0
        }

        closed = set()

        expansions = 0

        print()
        print("SEARCH")
        print("-" * 60)

        while open_set:

            _, current = heapq.heappop(open_set)

            if current in closed:
                continue

            closed.add(current)

            expansions += 1

            current_row, current_col = row_col(
                current,
                width,
            )

            # --------------------------------------------------
            # Goal reached
            # --------------------------------------------------

            if current == goal_node:
                break

            current_cost = float(
                cost[current_row, current_col]
            )

            # --------------------------------------------------
            # Explore neighbours
            # --------------------------------------------------

            for dr, dc in NEIGHBORS:

                nr = current_row + dr
                nc = current_col + dc

                if nr < 0 or nr >= height:
                    continue

                if nc < 0 or nc >= width:
                    continue

                neighbour_value = cost[nr, nc]

                if nodata is not None:
                    if neighbour_value == nodata:
                        continue

                if not math.isfinite(
                    float(neighbour_value)
                ):
                    continue

                neighbour = node_id(
                    nr,
                    nc,
                    width,
                )

                if neighbour in closed:
                    continue

                distance = movement_distance(
                    dr,
                    dc,
                    resolution,
                )

                # Average terrain traversal cost
                terrain_factor = (
                    1.0
                    + 2.0
                    * (
                        current_cost
                        + float(neighbour_value)
                    )
                    / 2.0
                )

                movement_cost = (
                    distance
                    * terrain_factor
                )

                tentative_g = (
                    g_score[current]
                    + movement_cost
                )

                if (
                    neighbour not in g_score
                    or tentative_g
                    < g_score[neighbour]
                ):

                    came_from[neighbour] = current

                    g_score[neighbour] = tentative_g

                    h = heuristic(
                        nr,
                        nc,
                        goal_row,
                        goal_col,
                        resolution,
                    )

                    f = tentative_g + h

                    heapq.heappush(
                        open_set,
                        (
                            f,
                            neighbour,
                        ),
                    )

        # --------------------------------------------------
        # No route
        # --------------------------------------------------

        if goal_node not in g_score:

            print()
            print("NO ROUTE FOUND")
            print("-" * 60)
            print(
                f"Nodes expanded: {expansions:,}"
            )

            raise RuntimeError(
                "A* could not find a route."
            )

        # --------------------------------------------------
        # Reconstruct
        # --------------------------------------------------

        path = reconstruct_path(
            came_from,
            goal_node,
        )

        print(
            f"Nodes expanded: {expansions:,}"
        )

        print(
            f"Path nodes:     {len(path):,}"
        )

        # --------------------------------------------------
        # Calculate route metrics
        # --------------------------------------------------

        total_distance = 0.0
        terrain_cost_sum = 0.0
        terrain_cost_max = 0.0

        route_coordinates = []

        previous = None

        for node in path:

            r, c = row_col(
                node,
                width,
            )

            terrain_value = float(
                cost[r, c]
            )

            terrain_cost_sum += terrain_value

            terrain_cost_max = max(
                terrain_cost_max,
                terrain_value,
            )

            x, y = rasterio.transform.xy(
                src.transform,
                r,
                c,
                offset="center",
            )

            route_coordinates.append(
                (x, y)
            )

            if previous is not None:

                pr, pc = row_col(
                    previous,
                    width,
                )

                dr = r - pr
                dc = c - pc

                total_distance += movement_distance(
                    dr,
                    dc,
                    resolution,
                )

            previous = node

        mean_terrain_cost = (
            terrain_cost_sum / len(path)
        )

        straight_line_distance = math.sqrt(
            (
                goal_row - start_row
            ) ** 2
            +
            (
                goal_col - start_col
            ) ** 2
        ) * resolution

        if total_distance > 0:

            efficiency = (
                straight_line_distance
                / total_distance
            )

        else:

            efficiency = 0.0

        # --------------------------------------------------
        # Output route
        # --------------------------------------------------

        with open(
            output_path,
            "w",
        ) as f:

            f.write(
                "MarsWalk Route\n"
            )

            f.write(
                "x,y\n"
            )

            for x, y in route_coordinates:

                f.write(
                    f"{x:.3f},{y:.3f}\n"
                )

        # --------------------------------------------------
        # Report
        # --------------------------------------------------

        print()
        print("ROUTE RESULT")
        print("-" * 60)

        print(
            f"Distance:             "
            f"{total_distance:.2f} m"
        )

        print(
            f"Distance:             "
            f"{total_distance / 1000:.3f} km"
        )

        print(
            f"Straight-line:        "
            f"{straight_line_distance:.2f} m"
        )

        print(
            f"Route efficiency:     "
            f"{efficiency * 100:.2f}%"
        )

        print(
            f"Mean terrain cost:    "
            f"{mean_terrain_cost:.4f}"
        )

        print(
            f"Maximum terrain cost: "
            f"{terrain_cost_max:.4f}"
        )

        print(
            f"Accumulated A* cost:  "
            f"{g_score[goal_node]:.2f}"
        )

        print(
            f"Route nodes:           "
            f"{len(path):,}"
        )

        print()
        print(
            f"Output: {output_path}"
        )

        print()
        print(
            "A* ROUTE COMPLETE"
        )

        print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 7:

        print(
            "Usage:\n"
            "python astar_route.py "
            "<raster> "
            "<start_row> "
            "<start_col> "
            "<goal_row> "
            "<goal_col> "
            "<output>"
        )

        sys.exit(1)

    run_astar(
        sys.argv[1],
        int(sys.argv[2]),
        int(sys.argv[3]),
        int(sys.argv[4]),
        int(sys.argv[5]),
        sys.argv[6],
    )