import math
import numpy as np


x_min_100 = x_min_102 = -2.5
x_max_100 = x_max_102 = 0.5
x_min_101 = -0.5
x_max_101 = 2.5
y_max = 4
y_min = -3.5
z_min_100 = z_min_102 = -0.35
z_min_101 = -0.15

outlier = -100

# 26度回転
trans_init_100 = np.asarray(
    [
        [2 / math.sqrt(5), -1 / math.sqrt(5), 0],
        [1 / math.sqrt(5), 2 / math.sqrt(5), 0.0],
        [0.0, 0.0, 1.0],
    ]
)

trans_init_101 = np.asarray(
    [
        [2 / math.sqrt(5), 1 / math.sqrt(5), 0],
        [-1 / math.sqrt(5), 2 / math.sqrt(5), 0.0],
        [0.0, 0.0, 1.0],
    ]
)

# 37度回転
trans_init_102 = np.asarray(
    [
        [0.80, -0.60, 0],
        [0.60, 0.80, 0.0],
        [0.0, 0.0, 1.0],
    ]
)
