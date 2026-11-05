"""Measure a stationary-camera projection change from two native captures.

Uses the middle scenery region to exclude most HUD and foreground animation.
The fit is evidence only when the camera position/orientation is unchanged.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--aspect", type=float, default=43 / 18)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    frames = [cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) for p in [args.before, args.after]]
    if any(im is None for im in frames):
        parser.error("Could not read both captures")
    before, after = [cv2.resize(im, (1920, 1080)) for im in frames]
    mask = np.zeros_like(before)
    mask[220:800, 250:1750] = 255
    sift = cv2.SIFT_create(nfeatures=5000)
    k1, d1 = sift.detectAndCompute(before, mask)
    k2, d2 = sift.detectAndCompute(after, mask)
    if d1 is None or d2 is None:
        parser.error("No usable scenery features")
    pairs = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    matches = [m for pair in pairs if len(pair) == 2 for m, n in [pair] if m.distance < .65 * n.distance]
    if len(matches) < 8:
        parser.error("Too few scenery matches for a useful affine fit")
    p1 = np.float32([k1[m.queryIdx].pt for m in matches])
    p2 = np.float32([k2[m.trainIdx].pt for m in matches])
    matrix, inliers = cv2.estimateAffine2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=2)
    if matrix is None:
        parser.error("No consistent scenery transform")
    display_x = matrix[0, 0] * args.aspect / (16 / 9)
    display_y = matrix[1, 1]
    result = dict(matches=len(matches), inliers=int(inliers.sum()), affine=matrix.tolist(),
                  expected_x_scale=(16 / 9) / args.aspect, expected_y_scale=1,
                  added_horizontal_percent=(args.aspect / (16 / 9) - 1) * 100,
                  display_normalized_x_scale=float(display_x),
                  display_normalized_y_scale=float(display_y),
                  relative_shape_error_percent=float(abs(display_x / display_y - 1) * 100))
    output = json.dumps(result, indent=2) + "\n"
    print(output, end="")
    if args.output:
        args.output.write_text(output)


if __name__ == "__main__":
    main()
