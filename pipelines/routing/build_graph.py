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


def build_graph(raster_path, output_path):

    print("=" * 60)
    print("MARSWALK ROUTING GRAPH")
    print("=" * 60)

    with rasterio.open(raster_path) as src:

        cost = src.read(1)
        height = src.height
        width = src.width
        nodata = src.nodata

        print()
        print("INPUT")
        print("-" * 60)
        print(f"Raster:      {raster_path}")
        print(f"Width:       {width}")
        print(f"Height:      {height}")
        print(f"Resolution:  {src.res}")

        edges = []

        valid_nodes = 0

        for row in range(height):

            for col in range(width):

                current = cost[row, col]

                if nodata is not None and current == nodata:
                    continue

                if not math.isfinite(float(current)):
                    continue

                valid_nodes += 1

                current_id = node_id(row, col, width)

                for dr, dc in NEIGHBORS:

                    nr = row + dr
                    nc = col + dc

                    if nr < 0 or nr >= height:
                        continue

                    if nc < 0 or nc >= width:
                        continue

                    neighbour = cost[nr, nc]

                    if nodata is not None and neighbour == nodata:
                        continue

                    if not math.isfinite(float(neighbour)):
                        continue

                    neighbour_id = node_id(nr, nc, width)

                    # Physical movement distance
                    if dr != 0 and dc != 0:
                        distance = math.sqrt(2) * src.res[0]
                    else:
                        distance = src.res[0]

                    # Average terrain cost along the movement
                    terrain_factor = (
                        1.0 +
                        2.0 * (
                            float(current) +
                            float(neighbour)
                        ) / 2.0
                    )

                    movement_cost = distance * terrain_factor

                    edges.append(
                        (
                            current_id,
                            neighbour_id,
                            movement_cost
                        )
                    )

            if row % 20 == 0 or row == height - 1:
                progress = 100 * (row + 1) / height
                print(f"Progress: {progress:6.2f}%")

        print()
        print("GRAPH")
        print("-" * 60)
        print(f"Valid nodes: {valid_nodes:,}")
        print(f"Directed edges: {len(edges):,}")

        with open(output_path, "w") as f:

            f.write("# MarsWalk routing graph\n")
            f.write(f"# width={width}\n")
            f.write(f"# height={height}\n")
            f.write(f"# resolution={src.res[0]}\n")
            f.write("# columns=source,target,cost\n")

            for source, target, edge_cost in edges:

                f.write(
                    f"{source},{target},{edge_cost:.8f}\n"
                )

    print()
    print(f"Output: {output_path}")
    print()
    print("ROUTING GRAPH COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "Usage:\n"
            "python build_graph.py "
            "<input_raster> <output_graph>"
        )

        sys.exit(1)

    build_graph(
        sys.argv[1],
        sys.argv[2]
    )