#%
import os
import numpy as np

os.environ["simultaneous_svg_exports_limit"] = "1"

import main
import diplomacy.persistence.manager as manager
from diplomacy.adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.utils import get_svg_element
x = manager.Manager()
x.total_delete(1)
x.create_game(1, "impdipfow.json")

def dist(x1, y1, x2, y2, x3, y3): # x3,y3 is the point
    px = x2-x1
    py = y2-y1

    norm = px*px + py*py

    u =  ((x3 - x1) * px + (y3 - y1) * py) / float(norm)

    if u > 1:
        u = 1
    elif u < 0:
        u = 0

    x = x1 + u * px
    y = y1 + u * py

    dx = x - x3
    dy = y - y3

    dist = (dx*dx + dy*dy)**.5

    return dist

#%
b = x.get_board(1)
count = 0
checked = []
for p1 in b.provinces:
    for p2 in p1.adjacent:
        for p3 in p2.adjacent:
            b = False
            for check in checked:
                if {p1, p2, p3}.issubset(check):
                    b = True
            if b:
                continue
            if p1 == p3:
                continue
            msg = f"Note: Line segment {p1.name} to {p3.name} passes too close to {p2.name}"
            l1 = np.array(p1.primary_unit_coordinate)
            l2 = np.array(p2.primary_unit_coordinate)
            l3 = np.array(p3.primary_unit_coordinate)
            if dist(*l1, *l3, *l2) < 1:
                print(msg)
                count += 1
                checked.append({p1, p2, p3})


print(f"detected {count} colinearities")