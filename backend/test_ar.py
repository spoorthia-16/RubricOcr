import json

def test_heuristic(valid_x, valid_y):
    aspect_ratios = []
    for r in range(len(valid_y) - 1):
        for c in range(len(valid_x) - 1):
            w = valid_x[c+1] - valid_x[c]
            h = valid_y[r+1] - valid_y[r]
            if h > 0:
                aspect_ratios.append(w / h)
    
    aspect_ratios.sort()
    median_ar = aspect_ratios[len(aspect_ratios)//2] if aspect_ratios else 1.0
    print(f"Median Aspect Ratio (W/H): {median_ar:.3f}")
    
    is_transposed = median_ar < 0.8
    print(f"Needs Transpose? {is_transposed}")

# DOC_5 valid_x and valid_y
valid_x = [5, 75, 170, 242, 308, 375, 442, 509, 575, 640, 970, 1035, 1101, 1166, 1232, 1298, 1363, 1428, 1493, 1560, 1624, 1691, 1756, 1822, 1888, 1954, 2020, 2089]
valid_y = [5, 65, 567, 818, 1035, 1253, 1471, 1684, 1901, 2118, 2335, 2613, 2848, 3105, 3388, 3670, 3936, 4203, 4316, 4379]

test_heuristic(valid_x, valid_y)
