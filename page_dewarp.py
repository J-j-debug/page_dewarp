import argparse

# Argument parsing setup
parser = argparse.ArgumentParser(description="Dewarp and threshold page images.")
parser.add_argument('images', metavar='IMAGE', type=str, nargs='+', help='Input image file(s)')
parser.add_argument('--page_margin_x', type=int, default=50, help='Reduced px to ignore near L/R edge. Default: 50')
parser.add_argument('--page_margin_y', type=int, default=20, help='Reduced px to ignore near T/B edge. Default: 20')
parser.add_argument('--output_zoom', type=float, default=1.0, help='How much to zoom output relative to original image. Default: 1.0')
parser.add_argument('--output_dpi', type=int, default=300, help='Stated DPI of output PNG. Default: 300')
parser.add_argument('--remap_decimate', type=int, default=16, help='Downscaling factor for remapping image. Default: 16')
parser.add_argument('--adaptive_winsz', type=int, default=55, help='Window size for adaptive threshold in reduced px. Default: 55')
parser.add_argument('--text_min_width', type=int, default=15, help='Min reduced px width of detected text contour. Default: 15')
parser.add_argument('--text_min_height', type=int, default=2, help='Min reduced px height of detected text contour. Default: 2')
parser.add_argument('--text_min_aspect', type=float, default=1.5, help='Filter out text contours below this w/h ratio. Default: 1.5')
parser.add_argument('--text_max_thickness', type=int, default=10, help='Max reduced px thickness of detected text contour. Default: 10')
parser.add_argument('--edge_max_overlap', type=float, default=1.0, help='Max reduced px horiz. overlap of contours in span. Default: 1.0')
parser.add_argument('--edge_max_length', type=float, default=100.0, help='Max reduced px length of edge connecting contours. Default: 100.0')
parser.add_argument('--edge_angle_cost', type=float, default=10.0, help='Cost of angles in edges (tradeoff vs. length). Default: 10.0')
parser.add_argument('--edge_max_angle', type=float, default=7.5, help='Maximum change in angle allowed between contours. Default: 7.5')
parser.add_argument('--span_min_width', type=int, default=30, help='Minimum reduced px width for span. Default: 30')
parser.add_argument('--span_px_per_step', type=int, default=20, help='Reduced px spacing for sampling along spans. Default: 20')
parser.add_argument('--focal_length', type=float, default=1.2, help='Normalized focal length of camera. Default: 1.2')
parser.add_argument('--debug_level', type=int, default=0, choices=[0, 1, 2, 3], help='Debug level (0=none, 1=some, 2=lots, 3=all). Default: 0')
parser.add_argument('--debug_output', type=str, default='file', choices=['file', 'screen', 'both'], help="Debug output destination ('file', 'screen', 'both'). Default: 'file'")

args = None # Placeholder for parsed args
#!/usr/bin/env python
######################################################################
# page_dewarp.py - Proof-of-concept of page-dewarping based on a
# "cubic sheet" model. Requires OpenCV (version 3 or greater),
# PIL/Pillow, and scipy.optimize.
######################################################################
# Author:  Matt Zucker
# Date:    July 2016
# License: MIT License (see LICENSE.txt)
######################################################################

import os
import sys
import datetime
import cv2
from PIL import Image
import numpy as np
import scipy.optimize

# for some reason pylint complains about cv2 members being undefined :(
# pylint: disable=E1101

# PAGE_MARGIN_X = 50 # Replaced by args.page_margin_x
# PAGE_MARGIN_Y = 20 # Replaced by args.page_margin_y

# OUTPUT_ZOOM = 1.0 # Replaced by args.output_zoom
# OUTPUT_DPI = 300 # Replaced by args.output_dpi
# REMAP_DECIMATE = 16 # Replaced by args.remap_decimate

# ADAPTIVE_WINSZ = 55 # Replaced by args.adaptive_winsz

# TEXT_MIN_WIDTH = 15 # Replaced by args.text_min_width
# TEXT_MIN_HEIGHT = 2 # Replaced by args.text_min_height
# TEXT_MIN_ASPECT = 1.5 # Replaced by args.text_min_aspect
# TEXT_MAX_THICKNESS = 10 # Replaced by args.text_max_thickness

# EDGE_MAX_OVERLAP = 1.0 # Replaced by args.edge_max_overlap
# EDGE_MAX_LENGTH = 100.0 # Replaced by args.edge_max_length
# EDGE_ANGLE_COST = 10.0 # Replaced by args.edge_angle_cost
# EDGE_MAX_ANGLE = 7.5 # Replaced by args.edge_max_angle

RVEC_IDX = slice(0, 3)   # index of rvec in params vector
# SPAN_MIN_WIDTH will be replaced by args.span_min_width
TVEC_IDX = slice(3, 6)   # index of tvec in params vector
CUBIC_IDX = slice(6, 8)  # index of cubic slopes in params vector

# SPAN_MIN_WIDTH = 30 # Replaced by args.span_min_width
# SPAN_PX_PER_STEP = 20 # Replaced by args.span_px_per_step
# FOCAL_LENGTH = 1.2 # Replaced by args.focal_length

# DEBUG_LEVEL = 0 # Replaced by args.debug_level
# args.debug_output = 'file'    # This line is problematic and redundant, default is handled by argparse

WINDOW_NAME = 'Dewarp'   # Window name for visualization

# nice color palette for visualizing contours, etc.
CCOLORS = [
    (255, 0, 0),
    (255, 63, 0),
    (255, 127, 0),
    (255, 191, 0),
    (255, 255, 0),
    (191, 255, 0),
    (127, 255, 0),
    (63, 255, 0),
    (0, 255, 0),
    (0, 255, 63),
    (0, 255, 127),
    (0, 255, 191),
    (0, 255, 255),
    (0, 191, 255),
    (0, 127, 255),
    (0, 63, 255),
    (0, 0, 255),
    (63, 0, 255),
    (127, 0, 255),
    (191, 0, 255),
    (255, 0, 255),
    (255, 0, 191),
    (255, 0, 127),
    (255, 0, 63),
]

# default intrinsic parameter matrix
# K = np.array([ # Original K matrix, now defined in main() after parsing args
#     [args.focal_length, 0, 0],
#     [0, args.focal_length, 0],
#     [0, 0, 1]], dtype=np.float32)


def debug_show(name, step, text, display):

    if args.debug_output != 'screen':
        filetext = text.replace(' ', '_')
        outfile = name + '_debug_' + str(step) + '_' + filetext + '.png'
        cv2.imwrite(outfile, display)

    if args.debug_output != 'file':

        image = display.copy()
        height = image.shape[0]

        cv2.putText(image, text, (16, height-16),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (0, 0, 0), 3, cv2.LINE_AA)

        cv2.putText(image, text, (16, height-16),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (255, 255, 255), 1, cv2.LINE_AA)

        cv2.imshow(WINDOW_NAME, image)

        while cv2.waitKey(5) < 0:
            pass


def round_nearest_multiple(i, factor):
    i = int(i)
    rem = i % factor
    if not rem:
        return i
    else:
        return i + factor - rem


def pix2norm(shape, pts):
    height, width = shape[:2]
    scl = 2.0/(max(height, width))
    offset = np.array([width, height], dtype=pts.dtype).reshape((-1, 1, 2))*0.5
    return (pts - offset) * scl


def norm2pix(shape, pts, as_integer):
    height, width = shape[:2]
    scl = max(height, width)*0.5
    offset = np.array([0.5*width, 0.5*height],
                      dtype=pts.dtype).reshape((-1, 1, 2))
    rval = pts * scl + offset
    if as_integer:
        return (rval + 0.5).astype(int)
    else:
        return rval


def fltp(point):
    return tuple(point.astype(int).flatten())


def draw_correspondences(img, dstpoints, projpts):

    display = img.copy()
    dstpoints = norm2pix(img.shape, dstpoints, True)
    projpts = norm2pix(img.shape, projpts, True)

    for pts, color in [(projpts, (255, 0, 0)),
                       (dstpoints, (0, 0, 255))]:

        for point in pts:
            cv2.circle(display, fltp(point), 3, color, -1, cv2.LINE_AA)

    for point_a, point_b in zip(projpts, dstpoints):
        cv2.line(display, fltp(point_a), fltp(point_b),
                 (255, 255, 255), 1, cv2.LINE_AA)

    return display


def get_default_params(corners, ycoords, xcoords):

    # page width and height
    page_width = np.linalg.norm(corners[1] - corners[0])
    page_height = np.linalg.norm(corners[-1] - corners[0])
    rough_dims = (page_width, page_height)

    # our initial guess for the cubic has no slope
    cubic_slopes = [0.0, 0.0]

    # object points of flat page in 3D coordinates
    corners_object3d = np.array([
        [0, 0, 0],
        [page_width, 0, 0],
        [page_width, page_height, 0],
        [0, page_height, 0]])

    # estimate rotation and translation from four 2D-to-3D point
    # correspondences
    _, rvec, tvec = cv2.solvePnP(corners_object3d,
                                 corners, K, np.zeros(5))

    span_counts = [len(xc) for xc in xcoords]

    params = np.hstack((np.array(rvec).flatten(),
                        np.array(tvec).flatten(),
                        np.array(cubic_slopes).flatten(),
                        ycoords.flatten()) +
                       tuple(xcoords))

    return rough_dims, span_counts, params


def project_xy(xy_coords, pvec):

    # get cubic polynomial coefficients given
    #
    #  f(0) = 0, f'(0) = alpha
    #  f(1) = 0, f'(1) = beta

    alpha, beta = tuple(pvec[CUBIC_IDX])

    poly = np.array([
        alpha + beta,
        -2*alpha - beta,
        alpha,
        0])

    xy_coords = xy_coords.reshape((-1, 2))
    z_coords = np.polyval(poly, xy_coords[:, 0])

    objpoints = np.hstack((xy_coords, z_coords.reshape((-1, 1))))

    image_points, _ = cv2.projectPoints(objpoints,
                                        pvec[RVEC_IDX],
                                        pvec[TVEC_IDX],
                                        K, np.zeros(5))

    return image_points


def project_keypoints(pvec, keypoint_index):

    xy_coords = pvec[keypoint_index]
    xy_coords[0, :] = 0

    return project_xy(xy_coords, pvec)


def resize_to_screen(src, maxw=1280, maxh=700, copy=False):

    height, width = src.shape[:2]

    scl_x = float(width)/maxw
    scl_y = float(height)/maxh

    scl = int(np.ceil(max(scl_x, scl_y)))

    if scl > 1.0:
        inv_scl = 1.0/scl
        img = cv2.resize(src, (0, 0), None, inv_scl, inv_scl, cv2.INTER_AREA)
    elif copy:
        img = src.copy()
    else:
        img = src

    return img


def box(width, height):
    return np.ones((height, width), dtype=np.uint8)


def get_page_extents(small):

    height, width = small.shape[:2]

    xmin = args.page_margin_x
    ymin = args.page_margin_y
    xmax = width-args.page_margin_x
    ymax = height-args.page_margin_y

    page = np.zeros((height, width), dtype=np.uint8)
    cv2.rectangle(page, (xmin, ymin), (xmax, ymax), (255, 255, 255), -1)

    outline = np.array([
        [xmin, ymin],
        [xmin, ymax],
        [xmax, ymax],
        [xmax, ymin]])

    return page, outline


def get_mask(name, small, pagemask, masktype):

    sgray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)

    if masktype == 'text':

        mask = cv2.adaptiveThreshold(sgray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                     cv2.THRESH_BINARY_INV,
                                     args.adaptive_winsz,
                                     25)

        if args.debug_level >= 3:
            debug_show(name, 0.1, 'thresholded', mask)

        mask = cv2.dilate(mask, box(9, 1))

        if args.debug_level >= 3:
            debug_show(name, 0.2, 'dilated', mask)

        mask = cv2.erode(mask, box(1, 3))

        if args.debug_level >= 3:
            debug_show(name, 0.3, 'eroded', mask)

    else:

        mask = cv2.adaptiveThreshold(sgray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                     cv2.THRESH_BINARY_INV,
                                     args.adaptive_winsz,
                                     7)

        if args.debug_level >= 3:
            debug_show(name, 0.4, 'thresholded', mask)

        mask = cv2.erode(mask, box(3, 1), iterations=3)

        if args.debug_level >= 3:
            debug_show(name, 0.5, 'eroded', mask)

        mask = cv2.dilate(mask, box(8, 2))

        if args.debug_level >= 3:
            debug_show(name, 0.6, 'dilated', mask)

    return np.minimum(mask, pagemask)


def interval_measure_overlap(int_a, int_b):
    return min(int_a[1], int_b[1]) - max(int_a[0], int_b[0])


def angle_dist(angle_b, angle_a):

    diff = angle_b - angle_a

    while diff > np.pi:
        diff -= 2*np.pi

    while diff < -np.pi:
        diff += 2*np.pi

    return np.abs(diff)


def blob_mean_and_tangent(contour):

    moments = cv2.moments(contour)

    area = moments['m00']

    mean_x = moments['m10'] / area
    mean_y = moments['m01'] / area

    moments_matrix = np.array([
        [moments['mu20'], moments['mu11']],
        [moments['mu11'], moments['mu02']]
    ]) / area

    _, svd_u, _ = cv2.SVDecomp(moments_matrix)

    center = np.array([mean_x, mean_y])
    tangent = svd_u[:, 0].flatten().copy()

    return center, tangent


class ContourInfo(object):

    def __init__(self, contour, rect, mask):

        self.contour = contour
        self.rect = rect
        self.mask = mask

        self.center, self.tangent = blob_mean_and_tangent(contour)

        self.angle = np.arctan2(self.tangent[1], self.tangent[0])

        clx = [self.proj_x(point) for point in contour]

        lxmin = min(clx)
        lxmax = max(clx)

        self.local_xrng = (lxmin, lxmax)

        self.point0 = self.center + self.tangent * lxmin
        self.point1 = self.center + self.tangent * lxmax

        self.pred = None
        self.succ = None

    def proj_x(self, point):
        return np.dot(self.tangent, point.flatten()-self.center)

    def local_overlap(self, other):
        xmin = self.proj_x(other.point0)
        xmax = self.proj_x(other.point1)
        return interval_measure_overlap(self.local_xrng, (xmin, xmax))


def generate_candidate_edge(cinfo_a, cinfo_b):

    # we want a left of b (so a's successor will be b and b's
    # predecessor will be a) make sure right endpoint of b is to the
    # right of left endpoint of a.
    if cinfo_a.point0[0] > cinfo_b.point1[0]:
        tmp = cinfo_a
        cinfo_a = cinfo_b
        cinfo_b = tmp

    x_overlap_a = cinfo_a.local_overlap(cinfo_b)
    x_overlap_b = cinfo_b.local_overlap(cinfo_a)

    overall_tangent = cinfo_b.center - cinfo_a.center
    overall_angle = np.arctan2(overall_tangent[1], overall_tangent[0])

    delta_angle = max(angle_dist(cinfo_a.angle, overall_angle),
                      angle_dist(cinfo_b.angle, overall_angle)) * 180/np.pi

    # we want the largest overlap in x to be small
    x_overlap = max(x_overlap_a, x_overlap_b)

    dist = np.linalg.norm(cinfo_b.point0 - cinfo_a.point1)

    if (dist > args.edge_max_length or
            x_overlap > args.edge_max_overlap or
            delta_angle > args.edge_max_angle):
        return None
    else:
        score = dist + delta_angle*args.edge_angle_cost
        return (score, cinfo_a, cinfo_b)


def make_tight_mask(contour, xmin, ymin, width, height):

    tight_mask = np.zeros((height, width), dtype=np.uint8)
    tight_contour = contour - np.array((xmin, ymin)).reshape((-1, 1, 2))

    cv2.drawContours(tight_mask, [tight_contour], 0,
                     (1, 1, 1), -1)

    return tight_mask


def get_contours(name, small, pagemask, masktype):

    mask = get_mask(name, small, pagemask, masktype)

    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_NONE)

    contours_out = []

    for contour in contours:

        rect = cv2.boundingRect(contour)
        xmin, ymin, width, height = rect

        if (width < args.text_min_width or
                height < args.text_min_height or
                width < args.text_min_aspect*height):
            continue

        tight_mask = make_tight_mask(contour, xmin, ymin, width, height)

        if tight_mask.sum(axis=0).max() > args.text_max_thickness:
            continue

        contours_out.append(ContourInfo(contour, rect, tight_mask))

    if args.debug_level >= 2:
        visualize_contours(name, small, contours_out)

    return contours_out


def assemble_spans(name, small, pagemask, cinfo_list):

    # sort list
    cinfo_list = sorted(cinfo_list, key=lambda cinfo: cinfo.rect[1])

    # generate all candidate edges
    candidate_edges = []

    for i, cinfo_i in enumerate(cinfo_list):
        for j in range(i):
            # note e is of the form (score, left_cinfo, right_cinfo)
            edge = generate_candidate_edge(cinfo_i, cinfo_list[j])
            if edge is not None:
                candidate_edges.append(edge)

    # sort candidate edges by score (lower is better)
    candidate_edges.sort()

    # for each candidate edge
    for _, cinfo_a, cinfo_b in candidate_edges:
        # if left and right are unassigned, join them
        if cinfo_a.succ is None and cinfo_b.pred is None:
            cinfo_a.succ = cinfo_b
            cinfo_b.pred = cinfo_a

    # generate list of spans as output
    spans = []

    # until we have removed everything from the list
    while cinfo_list:

        # get the first on the list
        cinfo = cinfo_list[0]

        # keep following predecessors until none exists
        while cinfo.pred:
            cinfo = cinfo.pred

        # start a new span
        cur_span = []

        width = 0.0

        # follow successors til end of span
        while cinfo:
            # remove from list (sadly making this loop *also* O(n^2)
            cinfo_list.remove(cinfo)
            # add to span
            cur_span.append(cinfo)
            width += cinfo.local_xrng[1] - cinfo.local_xrng[0]
            # set successor
            cinfo = cinfo.succ

        # add if long enough
        if width > args.span_min_width:
            spans.append(cur_span)

    if args.debug_level >= 2:
        visualize_spans(name, small, pagemask, spans)

    return spans


def sample_spans(shape, spans):

    span_points = []

    for span in spans:

        contour_points = []

        for cinfo in span:

            yvals = np.arange(cinfo.mask.shape[0]).reshape((-1, 1))
            totals = (yvals * cinfo.mask).sum(axis=0)
            means = totals / cinfo.mask.sum(axis=0)

            xmin, ymin = cinfo.rect[:2]

            step = args.span_px_per_step
            start = ((len(means)-1) % step) / 2

            contour_points += [(x+xmin, means[x]+ymin)
                               for x in range(start, len(means), step)]

        contour_points = np.array(contour_points,
                                  dtype=np.float32).reshape((-1, 1, 2))

        contour_points = pix2norm(shape, contour_points)

        span_points.append(contour_points)

    return span_points


def keypoints_from_samples(name, small, pagemask, page_outline,
                           span_points):

    all_evecs = np.array([[0.0, 0.0]])
    all_weights = 0

    for points in span_points:

        _, evec = cv2.PCACompute(points.reshape((-1, 2)),
                                 None, maxComponents=1)

        weight = np.linalg.norm(points[-1] - points[0])

        all_evecs += evec * weight
        all_weights += weight

    evec = all_evecs / all_weights

    x_dir = evec.flatten()

    if x_dir[0] < 0:
        x_dir = -x_dir

    y_dir = np.array([-x_dir[1], x_dir[0]])

    pagecoords = cv2.convexHull(page_outline)
    pagecoords = pix2norm(pagemask.shape, pagecoords.reshape((-1, 1, 2)))
    pagecoords = pagecoords.reshape((-1, 2))

    px_coords = np.dot(pagecoords, x_dir)
    py_coords = np.dot(pagecoords, y_dir)

    px0 = px_coords.min()
    px1 = px_coords.max()

    py0 = py_coords.min()
    py1 = py_coords.max()

    p00 = px0 * x_dir + py0 * y_dir
    p10 = px1 * x_dir + py0 * y_dir
    p11 = px1 * x_dir + py1 * y_dir
    p01 = px0 * x_dir + py1 * y_dir

    corners = np.vstack((p00, p10, p11, p01)).reshape((-1, 1, 2))

    ycoords = []
    xcoords = []

    for points in span_points:
        pts = points.reshape((-1, 2))
        px_coords = np.dot(pts, x_dir)
        py_coords = np.dot(pts, y_dir)
        ycoords.append(py_coords.mean() - py0)
        xcoords.append(px_coords - px0)

    if args.debug_level >= 2:
        visualize_span_points(name, small, span_points, corners)

    return corners, np.array(ycoords), xcoords


def visualize_contours(name, small, cinfo_list):

    regions = np.zeros_like(small)

    for j, cinfo in enumerate(cinfo_list):

        cv2.drawContours(regions, [cinfo.contour], 0,
                         CCOLORS[j % len(CCOLORS)], -1)

    mask = (regions.max(axis=2) != 0)

    display = small.copy()
    display[mask] = (display[mask]/2) + (regions[mask]/2)

    for j, cinfo in enumerate(cinfo_list):
        color = CCOLORS[j % len(CCOLORS)]
        color = tuple([c/4 for c in color])

        cv2.circle(display, fltp(cinfo.center), 3,
                   (255, 255, 255), 1, cv2.LINE_AA)

        cv2.line(display, fltp(cinfo.point0), fltp(cinfo.point1),
                 (255, 255, 255), 1, cv2.LINE_AA)

    debug_show(name, 1, 'contours', display)


def visualize_spans(name, small, pagemask, spans):

    regions = np.zeros_like(small)

    for i, span in enumerate(spans):
        contours = [cinfo.contour for cinfo in span]
        cv2.drawContours(regions, contours, -1,
                         CCOLORS[i*3 % len(CCOLORS)], -1)

    mask = (regions.max(axis=2) != 0)

    display = small.copy()
    display[mask] = (display[mask]/2) + (regions[mask]/2)
    display[pagemask == 0] /= 4

    debug_show(name, 2, 'spans', display)


def visualize_span_points(name, small, span_points, corners):

    display = small.copy()

    for i, points in enumerate(span_points):

        points = norm2pix(small.shape, points, False)

        mean, small_evec = cv2.PCACompute(points.reshape((-1, 2)),
                                          None,
                                          maxComponents=1)

        dps = np.dot(points.reshape((-1, 2)), small_evec.reshape((2, 1)))
        dpm = np.dot(mean.flatten(), small_evec.flatten())

        point0 = mean + small_evec * (dps.min()-dpm)
        point1 = mean + small_evec * (dps.max()-dpm)

        for point in points:
            cv2.circle(display, fltp(point), 3,
                       CCOLORS[i % len(CCOLORS)], -1, cv2.LINE_AA)

        cv2.line(display, fltp(point0), fltp(point1),
                 (255, 255, 255), 1, cv2.LINE_AA)

    cv2.polylines(display, [norm2pix(small.shape, corners, True)],
                  True, (255, 255, 255))

    debug_show(name, 3, 'span points', display)


def imgsize(img):
    height, width = img.shape[:2]
    return '{}x{}'.format(width, height)


def make_keypoint_index(span_counts):

    nspans = len(span_counts)
    npts = sum(span_counts)
    keypoint_index = np.zeros((npts+1, 2), dtype=int)
    start = 1

    for i, count in enumerate(span_counts):
        end = start + count
        keypoint_index[start:start+end, 1] = 8+i
        start = end

    keypoint_index[1:, 0] = np.arange(npts) + 8 + nspans

    return keypoint_index


def optimize_params(name, small, dstpoints, span_counts, params):

    keypoint_index = make_keypoint_index(span_counts)

    def objective(pvec):
        ppts = project_keypoints(pvec, keypoint_index)
        return np.sum((dstpoints - ppts)**2)

    print('  initial objective is', objective(params))

    if args.debug_level >= 1:
        projpts = project_keypoints(params, keypoint_index)
        display = draw_correspondences(small, dstpoints, projpts)
        debug_show(name, 4, 'keypoints before', display)

    print('  optimizing', len(params), 'parameters...')
    start = datetime.datetime.now()
    res = scipy.optimize.minimize(objective, params,
                                  method='Powell')
    end = datetime.datetime.now()
    print('  optimization took', round((end-start).total_seconds(), 2), 'sec.')
    print('  final objective is', res.fun)
    params = res.x

    if args.debug_level >= 1:
        projpts = project_keypoints(params, keypoint_index)
        display = draw_correspondences(small, dstpoints, projpts)
        debug_show(name, 5, 'keypoints after', display)

    return params


def get_page_dims(corners, rough_dims, params):

    dst_br = corners[2].flatten()

    dims = np.array(rough_dims)

    def objective(dims):
        proj_br = project_xy(dims, params)
        return np.sum((dst_br - proj_br.flatten())**2)

    res = scipy.optimize.minimize(objective, dims, method='Powell')
    dims = res.x

    print('  got page dims', dims[0], 'x', dims[1])

    return dims


def remap_image(name, img, small, page_dims, params):

    height = 0.5 * page_dims[1] * args.output_zoom * img.shape[0]
    height = round_nearest_multiple(height, args.remap_decimate)

    width = round_nearest_multiple(height * page_dims[0] / page_dims[1],
                                   args.remap_decimate)

    print('  output will be {}x{}'.format(width, height))

    height_small = height / args.remap_decimate
    width_small = width / args.remap_decimate

    page_x_range = np.linspace(0, page_dims[0], width_small)
    page_y_range = np.linspace(0, page_dims[1], height_small)

    page_x_coords, page_y_coords = np.meshgrid(page_x_range, page_y_range)

    page_xy_coords = np.hstack((page_x_coords.flatten().reshape((-1, 1)),
                                page_y_coords.flatten().reshape((-1, 1))))

    page_xy_coords = page_xy_coords.astype(np.float32)

    image_points = project_xy(page_xy_coords, params)
    image_points = norm2pix(img.shape, image_points, False)

    image_x_coords = image_points[:, 0, 0].reshape(page_x_coords.shape)
    image_y_coords = image_points[:, 0, 1].reshape(page_y_coords.shape)

    image_x_coords = cv2.resize(image_x_coords, (width, height),
                                interpolation=cv2.INTER_CUBIC)

    image_y_coords = cv2.resize(image_y_coords, (width, height),
                                interpolation=cv2.INTER_CUBIC)

    img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    remapped = cv2.remap(img_gray, image_x_coords, image_y_coords,
                         cv2.INTER_CUBIC,
                         None, cv2.BORDER_REPLICATE)

    thresh = cv2.adaptiveThreshold(remapped, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, args.adaptive_winsz, 25)

    pil_image = Image.fromarray(thresh)
    pil_image = pil_image.convert('1')

    threshfile = name + '_thresh.png'
    pil_image.save(threshfile, dpi=(args.output_dpi, args.output_dpi))

    if args.debug_level >= 1:
        height = small.shape[0]
        width = int(round(height * float(thresh.shape[1])/thresh.shape[0]))
        display = cv2.resize(thresh, (width, height),
                             interpolation=cv2.INTER_AREA)
        debug_show(name, 6, 'output', display)

    return threshfile



def run_dewarp_process(image_paths, params_dict):
    '''
    Processes a list of images using provided parameters.
    image_paths: A list of paths to images.
    params_dict: A dictionary of parameters, similar to what argparse would produce.
    Returns a list of output file paths.
    '''
    global args, K # Need to set the global args and K for the script's functions

    # Create a Namespace object from params_dict to simulate argparse args
    # Need to import argparse if not already available globally in this context
    # For simplicity, assume 'argparse' is imported in the original file.
    # We need the ArgumentParser instance to set defaults for missing params.
    # This is tricky. A better way is to ensure params_dict has ALL required values with defaults.
    # temp_parser = argparse.ArgumentParser() # Temporary parser to get defaults
    args = argparse.Namespace(**params_dict)

    # Update K matrix (copied from original main() setup)
    K = np.array([
        [args.focal_length, 0, 0],
        [0, args.focal_length, 0],
        [0, 0, 1]], dtype=np.float32)

    if args.debug_level > 0 and args.debug_output != 'file':
        if not cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE):
             cv2.namedWindow(WINDOW_NAME)

    outfiles = []
    # The core processing loop, adapted from main()
    for imgfile_path in image_paths:
        img = cv2.imread(imgfile_path)
        if img is None:
            print(f"Warning: Could not read image {imgfile_path}. Skipping.")
            continue
        small = resize_to_screen(img) # resize_to_screen needs to be available
        basename = os.path.basename(imgfile_path)
        name, ext = os.path.splitext(basename)

        print(f"loaded {basename} with size {imgsize(img)}") # imgsize needs to be available
        print(f"and resized to {imgsize(small)}")

        if args.debug_level >= 3:
            debug_show(name, 0.0, 'original', small) # debug_show needs to be available

        pagemask, page_outline = get_page_extents(small) # get_page_extents needs to be available

        cinfo_list = get_contours(name, small, pagemask, 'text') # get_contours needs to be available
        spans = assemble_spans(name, small, pagemask, cinfo_list) # assemble_spans needs to be available

        if len(spans) < 3:
            print(f"  detecting lines because only {len(spans)} text spans")
            cinfo_list = get_contours(name, small, pagemask, 'line')
            spans2 = assemble_spans(name, small, pagemask, cinfo_list)
            if len(spans2) > len(spans):
                spans = spans2

        if not spans:
            print(f"skipping {name} because only {len(spans)} spans")
            continue

        span_points = sample_spans(small.shape, spans) # sample_spans needs to be available

        print(f"  got {len(spans)} spans with {sum([len(pts) for pts in span_points])} points.")

        corners, ycoords, xcoords = keypoints_from_samples(name, small, pagemask, page_outline, span_points) # keypoints_from_samples needs to be available

        rough_dims, span_counts, current_params = get_default_params(corners, ycoords, xcoords) # get_default_params needs to be available

        dstpoints = np.vstack((corners[0].reshape((1, 1, 2)),) + tuple(span_points))

        optimized_params = optimize_params(name, small, dstpoints, span_counts, current_params) # optimize_params needs to be available

        page_dims = get_page_dims(corners, rough_dims, optimized_params) # get_page_dims needs to be available

        # output_dir must be handled by remap_image or by prefixing 'name'
        # For now, assume remap_image saves to current dir, or one specified by its 'name' prefix.
        # The 'name' in remap_image is used for the output file. We might need to prefix it.
        # Let's assume the output from remap_image is basename_thresh.png in the current directory
        outfile_leaf = remap_image(name, img, small, page_dims, optimized_params) # remap_image needs to be available

        outfiles.append(outfile_leaf) # Collect leaf names
        print(f"  wrote {outfile_leaf}")
        print()

    return outfiles

def main():
    global args, K # Declare K as global to modify it
    args = parser.parse_args()

    # Update K matrix with focal_length from command line arguments
    K = np.array([
        [args.focal_length, 0, 0],
        [0, args.focal_length, 0],
        [0, 0, 1]], dtype=np.float32)

    # Check if images are provided (handled by argparse nargs='+')
    # if len(sys.argv) < 2:
    #     print('usage:', sys.argv[0], 'IMAGE1 [IMAGE2 ...]')
    #     sys.exit(0) # Argparse handles missing arguments / usage print

    if args.debug_level > 0 and args.debug_output != 'file':
        cv2.namedWindow(WINDOW_NAME)

    outfiles = []

    for imgfile in args.images:

        img = cv2.imread(imgfile)
        small = resize_to_screen(img)
        basename = os.path.basename(imgfile)
        name, _ = os.path.splitext(basename)

        print('loaded', basename, 'with size', imgsize(img), end=' ')
        print('and resized to', imgsize(small))

        if args.debug_level >= 3:
            debug_show(name, 0.0, 'original', small)

        pagemask, page_outline = get_page_extents(small)

        cinfo_list = get_contours(name, small, pagemask, 'text')
        spans = assemble_spans(name, small, pagemask, cinfo_list)

        if len(spans) < 3:
            print('  detecting lines because only', len(spans), 'text spans')
            cinfo_list = get_contours(name, small, pagemask, 'line')
            spans2 = assemble_spans(name, small, pagemask, cinfo_list)
            if len(spans2) > len(spans):
                spans = spans2

        if len(spans) < 1:
            print('skipping', name, 'because only', len(spans), 'spans')
            continue

        span_points = sample_spans(small.shape, spans)

        print('  got', len(spans), 'spans', end=' ')
        print('with', sum([len(pts) for pts in span_points]), 'points.')

        corners, ycoords, xcoords = keypoints_from_samples(name, small,
                                                           pagemask,
                                                           page_outline,
                                                           span_points)

        rough_dims, span_counts, params = get_default_params(corners,
                                                             ycoords, xcoords)

        dstpoints = np.vstack((corners[0].reshape((1, 1, 2)),) +
                              tuple(span_points))

        params = optimize_params(name, small,
                                 dstpoints,
                                 span_counts, params)

        page_dims = get_page_dims(corners, rough_dims, params)

        outfile = remap_image(name, img, small, page_dims, params)

        outfiles.append(outfile)

        print('  wrote', outfile)
        print()

    print('to convert to PDF (requires ImageMagick):')
    print('  convert -compress Group4 ' + ' '.join(outfiles) + ' output.pdf')


if __name__ == '__main__':
    main()
