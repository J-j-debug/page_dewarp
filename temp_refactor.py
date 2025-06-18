import sys

def get_param_names():
    # These are the names as they appear in argparse setup in page_dewarp.py
    # and will be keys in the params_dict
    return [
        'page_margin_x', 'page_margin_y', 'output_zoom', 'output_dpi',
        'remap_decimate', 'adaptive_winsz', 'text_min_width', 'text_min_height',
        'text_min_aspect', 'text_max_thickness', 'edge_max_overlap', 'edge_max_length',
        'edge_angle_cost', 'edge_max_angle', 'span_min_width', 'span_px_per_step',
        'focal_length', 'debug_level', 'debug_output'
    ]

def refactor_page_dewarp(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    new_lines = []
    in_main_loop_body = False
    main_loop_body_lines = []
    main_func_signature_found = False
    argparse_lines_done = False
    global_args_K_lines = [] # To store `global args, K` and K redefinition

    # Identify lines related to argparse and global K, args setup in main
    # These will be needed for the new dewarp_single_image function or kept in main
    argparse_setup_lines = []
    main_prefix_lines = [] # Lines in main before the loop (args parsing, K setup)

    collecting_argparse = True
    collecting_main_prefix = False

    for i, line in enumerate(lines):
        if "parser = argparse.ArgumentParser" in line:
            collecting_argparse = True
        if line.strip().startswith("args = None"): # End of initial argparse setup
             argparse_setup_lines.append(line)
             collecting_argparse = False
             continue # Skip this line, args will be a parameter

        if collecting_argparse:
            argparse_setup_lines.append(line)
            continue

        if "def main():" in line:
            main_func_signature_found = True
            collecting_main_prefix = True
            # Keep the original main signature for now
            new_lines.append(line)
            continue

        if collecting_main_prefix:
            if "for imgfile in args.images:" in line:
                collecting_main_prefix = False
                # The loop line itself is not part of the prefix or the body we extract
            else:
                if "global args, K" in line or "K = np.array([" in line or "args.focal_length" in line or "args = parser.parse_args()" in line :
                    main_prefix_lines.append(line) # These setup K and parse args
                else: # Other lines before the loop in main
                    new_lines.append(line)
                continue


        if "for imgfile in args.images:" in line:
            in_main_loop_body = True
            # The loop setup will be part of the modified main()
            continue

        if in_main_loop_body:
            # Heuristic to find end of loop: less indentation or specific known lines after loop
            if (line.strip() == "" and lines[i+1].strip().startswith("print(")) or "print('to convert to PDF" in line : # End of loop processing
                in_main_loop_body = False
                # This line is outside the loop body, add it to new_lines after processing loop body
                new_lines.append(line)
                continue
            main_loop_body_lines.append(line)
        else:
            new_lines.append(line)

    # Now construct the new function
    dewarp_func_lines = []
    dewarp_func_lines.append("\n")
    dewarp_func_lines.append("def dewarp_single_image(img_path_or_data, params, output_dir='.'):\n")
    dewarp_func_lines.append("    # This function encapsulates the core dewarping logic for one image.\n")
    dewarp_func_lines.append("    # img_path_or_data: path to image or loaded image data (e.g., numpy array)\n")
    dewarp_func_lines.append("    # params: a dictionary containing all necessary parameters.\n")
    dewarp_func_lines.append("    # output_dir: directory to save processed files.\n")
    dewarp_func_lines.append("\n")

    # Add K matrix re-construction based on params['focal_length']
    dewarp_func_lines.append("    # Setup K matrix based on focal_length from params\n")
    dewarp_func_lines.append("    K_matrix = np.array([\n")
    dewarp_func_lines.append("        [params['focal_length'], 0, 0],\n")
    dewarp_func_lines.append("        [0, params['focal_length'], 0],\n")
    dewarp_func_lines.append("        [0, 0, 1]], dtype=np.float32)\n")
    dewarp_func_lines.append("\n")

    # Replace 'args.param_name' with 'params['param_name']'
    # Replace 'K' (global) with 'K_matrix' (local to function)
    # Replace 'imgfile' with a new variable, e.g., 'current_image_path'
    # Handle 'basename' and 'name' derivation if img_path_or_data is a path

    dewarp_func_lines.append("    if isinstance(img_path_or_data, str):\n")
    dewarp_func_lines.append("        current_image_path = img_path_or_data\n")
    dewarp_func_lines.append("        img = cv2.imread(current_image_path)\n")
    dewarp_func_lines.append("        basename = os.path.basename(current_image_path)\n")
    dewarp_func_lines.append("        name, _ = os.path.splitext(basename)\n")
    dewarp_func_lines.append("    else:\n") # Assuming it's a numpy array (OpenCV image)
        # For GUI, we might pass image data directly.
        # Need to decide how 'name' and 'basename' are handled for non-file inputs.
        # For now, let's create a placeholder name.
    dewarp_func_lines.append("        img = img_path_or_data\n")
    dewarp_func_lines.append("        name = f\"processed_image_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}\"\n")
    dewarp_func_lines.append("        basename = name + '.png' # Placeholder, as no original filename\n")
    dewarp_func_lines.append("\n")

    dewarp_func_lines.append("    # Ensure output directory for debug files and final output exists\n")
    dewarp_func_lines.append("    if params.get('debug_level', 0) > 0 and params.get('debug_output') == 'file':\n")
    dewarp_func_lines.append("        if not os.path.exists(output_dir):\n")
    dewarp_func_lines.append("            os.makedirs(output_dir, exist_ok=True)\n")
    dewarp_func_lines.append("\n")

    # Prepend output_dir to filenames for debug_show and remap_image output
    # This is a bit tricky. We need to modify calls to debug_show and the final save path in remap_image.
    # Let's assume 'name' in debug_show and remap_image will be prefixed.
    # The 'name' variable in the loop body is derived from imgfile.
    # We'll pass output_dir to functions that write files if possible, or prefix 'name'.

    for body_line in main_loop_body_lines:
        # Parameter replacement
        for p_name in get_param_names():
            body_line = body_line.replace(f"args.{p_name}", f"params['{p_name}']")

        # K matrix replacement
        body_line = body_line.replace(" K", " K_matrix") # Space before K to avoid replacing in KeYpoints etc.
        body_line = body_line.replace("(K,", "(K_matrix,")
        body_line = body_line.replace(", K,", ", K_matrix,")


        # Handle file output paths for debug_show and remap_image
        # `debug_show(name, ...)` name becomes `os.path.join(output_dir, name)`
        # `remap_image(name, ...)` name becomes `os.path.join(output_dir, name)`
        # This is a simplification; debug_show itself constructs filenames.
        # A better way would be to pass output_dir into debug_show and remap_image.

        if "debug_show(" in body_line:
             # debug_show(name, step, text, display)
             # name should be prefixed with output_dir if debug_output is 'file'
             body_line = body_line.replace("debug_show(name,", "debug_show(os.path.join(output_dir, name),")

        if "remap_image(" in body_line:
            # outfile = remap_image(name, img, small, page_dims, params_for_remap)
            # The 'name' in remap_image is used to construct 'threshfile'.
            # We need remap_image to respect output_dir.
            # Let's modify remap_image to take output_dir.
            # For now, the call will be: remap_image(os.path.join(output_dir, name), ...)
             body_line = body_line.replace("remap_image(name,", "remap_image(name,") # Keep name as is for now, remap_image will be modified later
                                                                                    # to accept output_dir

        dewarp_func_lines.append(body_line)

    dewarp_func_lines.append("    return name + '_thresh.png' # Assuming remap_image still saves with this suffix\n") # Placeholder for actual return

    # Modify remap_image to accept output_dir and use it
    # Modify debug_show to accept output_dir and use it (if debug_output is file)

    final_script_lines = []
    added_dewarp_func = False

    # Find where to insert the new function (e.g., before main())
    # And where to insert argparse setup

    temp_new_lines = []
    # First, add all lines that are not the old argparse setup or main
    for line in lines:
        is_old_argparse = False
        for ap_line in argparse_setup_lines:
            if line.strip() == ap_line.strip():
                is_old_argparse = True
                break
        if is_old_argparse:
            continue

        # Remove old main prefix lines as they are handled differently now
        is_main_prefix = False
        for mp_line in main_prefix_lines:
            if line.strip() == mp_line.strip():
                 is_main_prefix = True
                 break
        if is_main_prefix:
            continue

        if "def main():" in line: # Marker for where old main was
            # Insert the new dewarp_single_image function definition
            temp_new_lines.extend(dewarp_func_lines)
            added_dewarp_func = True
            # Add the modified main function
            temp_new_lines.append("\n# Original main function, adapted to use dewarp_single_image and argparse\n")
            temp_new_lines.append("def main():\n")
            temp_new_lines.append("    parser = argparse.ArgumentParser(description=\"Dewarp and threshold page images.\")\n")
            temp_new_lines.append("    parser.add_argument('images', metavar='IMAGE', type=str, nargs='+', help='Input image file(s)')\n")
            # Add all the parser.add_argument calls from argparse_setup_lines
            for ap_line in argparse_setup_lines:
                if "parser.add_argument" in ap_line:
                    temp_new_lines.append(ap_line)
            temp_new_lines.append("    args = parser.parse_args()\n\n")
            temp_new_lines.append("    # Convert Namespace to dict for params\n")
            temp_new_lines.append("    params_dict = vars(args)\n\n")
            temp_new_lines.append("    if args.debug_level > 0 and args.debug_output != 'file':\n")
            temp_new_lines.append("        cv2.namedWindow(WINDOW_NAME)\n\n")
            temp_new_lines.append("    outfiles = []\n")
            temp_new_lines.append("    for imgfile_path in args.images:\n")
            temp_new_lines.append("        # Output processed files to current dir or a specified one for CLI\n")
            temp_new_lines.append("        output_directory = '.' \n")
            temp_new_lines.append("        # We might want an --output-dir for CLI too eventually\n")
            temp_new_lines.append("        processed_file_name = dewarp_single_image(imgfile_path, params_dict, output_directory)\n")
            temp_new_lines.append("        if processed_file_name:\n")
            # The actual output path is now constructed inside dewarp_single_image if it writes a file
            # or it returns image data. For now, assume it returns the 'name_thresh.png' part.
            temp_new_lines.append("            outfile_path = os.path.join(output_directory, processed_file_name)\n")
            temp_new_lines.append("            outfiles.append(outfile_path)\n")
            temp_new_lines.append("            print(f\"  wrote {outfile_path}\")\n")
            temp_new_lines.append("        print()\n\n")

            temp_new_lines.append("    if outfiles:\n")
            temp_new_lines.append("        print('to convert to PDF (requires ImageMagick):')\n")
            temp_new_lines.append("        print(f\"  convert -compress Group4 {' '.join(outfiles)} output.pdf\")\n")

            # Continue with the rest of the original file (after main loop body)
            # This part is tricky, need to ensure correct lines are appended.
            # The previous loop already added lines after the main_loop_body.
            # The new_lines list should contain the structure, let's try to rebuild it.

            # This simplified script structure is likely insufficient.
            # The goal is to take existing lines, insert the new function, and modify main.
            # The current new_lines from the first pass is a base.

            # Let's try a different approach for final assembly:
            # 1. Original lines up to where main() was.
            # 2. New function definition.
            # 3. New main() definition.
            # 4. Original lines from after main() (if any, like `if __name__ == '__main__':`)

            # This part of script is getting too complex for a simple subtask.
            # A more robust approach would be to use Python's AST module.
            # For now, I will try to manually construct the output based on the logic.
            # This script will likely fail or produce incorrect Python.
            print("Error: This refactoring strategy is too complex for a simple text processing script.", file=sys.stderr)
            print("Python's AST module or more careful line-by-line reconstruction is needed.", file=sys.stderr)
            print("Aborting this refactoring attempt.", file=sys.stderr)
            sys.exit(1) # Signal failure

    with open(filepath + ".refactored", 'w') as f:
        f.writelines(final_script_lines)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        refactor_page_dewarp(sys.argv[1])
    else:
        print("Usage: python temp_refactor.py <path_to_page_dewarp.py>", file=sys.stderr)
