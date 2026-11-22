"""engine.entities.pathfinding — A* over walkable blocks."""
from __future__ import annotations
import heapq
from engine.core import BlockPos

WALKABLE_IDS = {0, 31, 32, 38, 39, 40, 50, 51, 59, 78, 81, 83, 106, 111, 141, 142, 175, 207}


class PathNode:
    __slots__ = ('pos', 'g', 'h', 'f', 'parent', 'closed')
    def __init__(self, pos, g, h, parent=None):
        self.pos = pos; self.g = g; self.h = h; self.f = g + h
        self.parent = parent; self.closed = False
    def __lt__(self, other):
        return self.f < other.f


class PathFinder:
    def __init__(self, max_nodes=3000, max_distance=64):
        self.max_nodes = max_nodes
        self.max_distance = max_distance

    def can_stand(self, world, pos):
        below = world.get_block_state_id(BlockPos(pos.x, pos.y - 1, pos.z))
        at = world.get_block_state_id(pos)
        above = world.get_block_state_id(BlockPos(pos.x, pos.y + 1, pos.z))
        if below == 0:
            return False
        if at != 0 and at not in WALKABLE_IDS:
            return False
        if above != 0 and above not in WALKABLE_IDS:
            return False
        return True

    def heuristic(self, a, b):
        return abs(a.x-b.x) + abs(a.z-b.z) + abs(a.y-b.y) * 1.5

    def find_path(self, world, start, goal):
        if not self.can_stand(world, start): return None
        if not self.can_stand(world, goal): return None
        open_heap = []
        start_node = PathNode(start, 0, self.heuristic(start, goal))
        heapq.heappush(open_heap, start_node)
        open_map = {start: start_node}
        visited = 0
        while open_heap and visited < self.max_nodes:
            cur = heapq.heappop(open_heap)
            if cur.closed: continue
            cur.closed = True; visited += 1
            if cur.pos == goal:
                path = []
                n = cur
                while n is not None:
                    path.append(n.pos); n = n.parent
                return list(reversed(path))
            if self.heuristic(cur.pos, start) > self.max_distance:
                continue
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dz == 0: continue
                    if dx != 0 and dz != 0: continue
                    # Only allow one-block step up; no 2-block jumps.
                    for dy in (-1, 0, 1):
                        npos = BlockPos(cur.pos.x + dx, cur.pos.y + dy, cur.pos.z + dz)
                        if not self.can_stand(world, npos): continue
                        if dy == 1:
                            # jump up: require that the head position is also clear
                            if world.get_block_state_id(BlockPos(npos.x, npos.y + 2, npos.z)) != 0:
                                continue
                        step = 1.0 + (0.5 if dy != 0 else 0.0)
                        g = cur.g + step
                        old = open_map.get(npos)
                        if old is not None and g >= old.g: continue
                        nd = PathNode(npos, g, self.heuristic(npos, goal), cur)
                        open_map[npos] = nd
                        heapq.heappush(open_heap, nd)
        return None
