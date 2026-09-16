from window_ui import adjacent_positions, group_positions
# Right, left fallback, room on neither side, and a monitor left of the primary.
for main,work in [((500,100,430,535),(0,0,1920,1040)),
                  ((1450,100,430,535),(0,0,1920,1040)),
                  ((285,100,430,535),(0,0,1000,1000)),
                  ((-600,100,430,535),(-1920,0,0,1040))]:
    (x,y),(cx,cy)=adjacent_positions(main,(430,535),work)
    assert y==cy
    assert cx==x+436 or cx+436==x
    assert work[0]<=x and x+430<=work[2]
    assert work[0]<=cx and cx+430<=work[2]
assert adjacent_positions((1450,100,430,535),(430,535),(0,0,1920,1040))[1][0]==1014
print('PLACEMENT_OK: adjacent without overlap, right/left fallback, cramped work area, negative monitor')

for main,work,count in [((500,100,430,535),(0,0,1920,1040),2),
                        ((1400,100,430,535),(0,0,1920,1040),3),
                        ((-1000,100,430,535),(-1920,0,0,1040),3),
                        ((500,100,430,535),(0,0,1920,2160),7)]:
    origin,children=group_positions(main,(430,535),work,count)
    rectangles=[(*origin,430,535),*((x,y,430,535) for x,y in children)]
    assert all(x>=origin[0]+436 for x,y in children) or all(x+436<=origin[0] for x,y in children)
    for index,(x,y,w,h) in enumerate(rectangles):
        assert work[0]<=x and x+w<=work[2] and work[1]<=y and y+h<=work[3]
        for xx,yy,ww,hh in rectangles[:index]:
            assert x+w+6<=xx or xx+ww+6<=x or y+h+6<=yy or yy+hh+6<=y
try:group_positions((500,100,430,535),(430,535),(0,0,1920,1040),4)
except ValueError:pass
else:raise AssertionError('Overflow must not overlap or hide a draft off screen')
print('GROUP_PLACEMENT_OK: two/three composers, same side, rows, negative coordinates, capacity limit')
