# SPDX-License-Identifier: 0BSD
import re
def parse_route_element(value):
    match=re.fullmatch(r"LC_X(\d+)_Y(\d+)_N(\d+)",value)
    if match is None:return None
    x,y,n=map(int,match.groups())
    return {"family":"LC","x":x,"y":y,"n":n}
