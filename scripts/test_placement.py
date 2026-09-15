from window_ui import adjacent_positions
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
