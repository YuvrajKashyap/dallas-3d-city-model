import numpy as np

from dallas3d.pathfinding import astar


def test_astar_routes_around_obstacles():
    blocked = np.zeros((5, 5), dtype=bool)
    blocked[2, 0:4] = True
    path = astar(blocked, (0, 0), (4, 4))

    assert path[0] == (0, 0)
    assert path[-1] == (4, 4)
    assert all(not blocked[cell] for cell in path)
    assert (2, 4) in path
