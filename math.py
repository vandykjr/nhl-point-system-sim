probs = [(.56, .22, .22), (.65, .15, .20), (.70, .15, .15),
         (.65, .20, .15), (.70, .15, .15), (.75, .15, .10), 
         (.7, .10, .15), (.75, .10, .15), (.80, .10, .10)]
REG_WIN = 2
OT_WIN = 2
OT_LOSS = 0
TIE = 1
REG_LOSS = 0
expected_points = []
for p in probs:
    exp_pts = p[0] * TIE + p[1] * REG_WIN + p[2] * REG_LOSS
    expected_points.append(exp_pts)
print(expected_points)