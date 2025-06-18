page_dewarp
===========

Page dewarping and thresholding using a "cubic sheet" model - see full writeup at <https://mzucker.github.io/2016/08/15/page-dewarping.html>

Requirements:

 - scipy
 - OpenCV 3.0 or greater
 - Image module from PIL or Pillow
 
Usage:

    page_dewarp.py IMAGE1 [IMAGE2 ...]
### Command-line Arguments

The `page_dewarp.py` script accepts several command-line arguments to customize its behavior:

-   `IMAGE1 [IMAGE2 ...]` : (Positional) One or more input image file(s).

**Page Layout & Margins:**
-   `--page_margin_x MARGIN_X`: Reduced pixels to ignore near Left/Right edges. Default: 50.
-   `--page_margin_y MARGIN_Y`: Reduced pixels to ignore near Top/Bottom edges. Default: 20.

**Output Control:**
-   `--output_zoom ZOOM`: Zoom factor for the output image relative to the original. Default: 1.0.
-   `--output_dpi DPI`: Dots Per Inch for the output PNG image. Default: 300.
-   `--remap_decimate DECIMATE`: Downscaling factor for remapping image (higher improves speed, lower improves quality). Default: 16.

**Thresholding & Text Detection:**
-   `--adaptive_winsz WIN_SIZE`: Window size for adaptive thresholding. Default: 55.
-   `--text_min_width MIN_WIDTH`: Minimum width (in reduced pixels) for a contour to be considered text. Default: 15.
-   `--text_min_height MIN_HEIGHT`: Minimum height (in reduced pixels) for a contour to be considered text. Default: 2.
-   `--text_min_aspect ASPECT_RATIO`: Minimum aspect ratio (width/height) for text contours. Default: 1.5.
-   `--text_max_thickness MAX_THICKNESS`: Maximum thickness (in reduced pixels) for text contours. Default: 10.

**Edge & Span Detection (for line construction):**
-   `--edge_max_overlap OVERLAP`: Maximum horizontal overlap (in reduced pixels) allowed between contours in a span. Default: 1.0.
-   `--edge_max_length MAX_LENGTH`: Maximum length (in reduced pixels) of an edge connecting contours. Default: 100.0.
-   `--edge_angle_cost ANGLE_COST`: Cost factor for angles in edges (balances against edge length). Default: 10.0.
-   `--edge_max_angle MAX_ANGLE`: Maximum change in angle (degrees) allowed between connected contours. Default: 7.5.
-   `--span_min_width MIN_SPAN_WIDTH`: Minimum width (in reduced pixels) for a valid text/line span. Default: 30.
-   `--span_px_per_step STEP_SIZE`: Spacing (in reduced pixels) for sampling points along detected spans. Default: 20.

**Camera & Model Parameters:**
-   `--focal_length FL`: Normalized focal length of the camera model. Default: 1.2.

**Debugging:**
-   `--debug_level LEVEL`: Debugging verbosity (0: none, 1: some, 2: lots, 3: all). Default: 0.
-   `--debug_output DEST`: Destination for debug images ('file', 'screen', 'both'). Default: 'file'.

Example:
`python page_dewarp.py --output_zoom 1.5 --debug_level 1 example_input/boston_cooking_a.jpg`
