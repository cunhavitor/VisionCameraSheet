import cv2
import numpy as np
import time

def _apply_morphological_ops(mask, kernel_size, iterations):
    """
    Applies morphological opening and closing to a binary mask.

    Args:
        mask (np.array): The input binary mask.
        kernel_size (int): The size of the square kernel.
        iterations (int): The number of iterations for each operation.

    Returns:
        np.array: The cleaned binary mask.
    """
    # Ensure kernel size is odd and positive
    effective_kernel_size = kernel_size
    if effective_kernel_size % 2 == 0:
        effective_kernel_size += 1
    effective_kernel_size = max(1, effective_kernel_size)
    kernel = np.ones((effective_kernel_size, effective_kernel_size), np.uint8)

    # Perform opening to remove small noise and detach objects
    clean_mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)

    # Perform closing to fill small holes and connect close objects
    clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel, iterations=iterations)

    return clean_mask

def detect_defects(tpl, aligned, mask,
                   dark_threshold, bright_threshold,
                   dark_morph_kernel_size, dark_morph_iterations,
                   bright_morph_kernel_size, bright_morph_iterations,
                   min_defect_area,
                   dark_gradient_threshold,
                   blue_threshold, red_threshold):
    """
    Detects defects by comparing a template image with an aligned current image using
    grayscale and color difference methods.

    Args:
        tpl (np.array): The template image (BGR).
        aligned (np.array): The current image, already aligned to the template (BGR).
        mask (np.array): A grayscale mask defining the region of interest.
        dark_threshold (int): Threshold for detecting darker-than-template defects.
        bright_threshold (int): Threshold for detecting brighter/yellow defects.
        dark_morph_kernel_size (int): Kernel size for morphological ops on dark defects.
        dark_morph_iterations (int): Iterations for morphological ops on dark defects.
        bright_morph_kernel_size (int): Kernel size for morphological ops on bright/color defects.
        bright_morph_iterations (int): Iterations for morphological ops on bright/color defects.
        min_defect_area (int): Minimum pixel area for a contour to be considered a defect.
        dark_gradient_threshold (int): Minimum gradient magnitude for a dark pixel to be considered a defect,
                                     used to filter out shadows.
        blue_threshold (int): Threshold for detecting bluer-than-template defects.
        red_threshold (int): Threshold for detecting redder-than-template defects.

    Returns:
        tuple: A tuple containing:
            - final_defect_mask (np.array): The binary mask showing detected defects.
            - filtered_contours (list): A list of contours representing detected defects.
            - darker_mask_filtered (np.array): The intermediate mask for darker defects (for debugging/info).
            - brighter_mask (np.array): The intermediate mask for brighter/yellow defects (for debugging/info).
            - blue_mask (np.array): The intermediate mask for blue defects (for debugging/info).
            - red_mask (np.array): The intermediate mask for red defects (for debugging/info).
    """
    start_time = time.time()

    # --- 1. Grayscale Preprocessing ---
    # Convert to grayscale
    t_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian Blur to reduce noise
    t_gray_blur = cv2.GaussianBlur(t_gray, (3, 3), 0)
    a_gray_blur = cv2.GaussianBlur(a_gray, (3, 3), 0)

    # Use CLAHE for adaptive histogram equalization to improve contrast in different lighting conditions
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    t_gray_eq = clahe.apply(t_gray_blur)
    a_gray_eq = clahe.apply(a_gray_blur)

    # --- 2. Grayscale Difference for Darker Defects ---
    # Subtract the aligned image from the template. Positive values indicate areas
    # in the aligned image that are darker than the template.
    diff_dark_raw = cv2.subtract(t_gray_eq, a_gray_eq)
    darker_mask = cv2.threshold(diff_dark_raw, dark_threshold, 255, cv2.THRESH_BINARY)[1]

    # --- Shadow Avoidance: Gradient-based filtering for Dark Defects ---
    # Use morphological gradient to find regions with strong local intensity changes
    # This helps to differentiate defects (sharp changes) from smooth shadows.
    morph_grad = cv2.morphologyEx(a_gray_eq, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
    _, gradient_mask_dark = cv2.threshold(morph_grad, dark_gradient_threshold, 255, cv2.THRESH_BINARY)
    darker_mask_filtered = cv2.bitwise_and(darker_mask, gradient_mask_dark)

    # --- 3. Color Differences using LAB Space ---
    # Convert to LAB space for robust color comparison.
    # L channel for lightness, A for green-red, B for blue-yellow.
    tpl_lab = cv2.cvtColor(tpl, cv2.COLOR_BGR2LAB)
    aligned_lab = cv2.cvtColor(aligned, cv2.COLOR_BGR2LAB)

    tpl_a = tpl_lab[:, :, 1]
    aligned_a = aligned_lab[:, :, 1]
    tpl_b = tpl_lab[:, :, 2]
    aligned_b = aligned_lab[:, :, 2]

    # Brighter/Yellow defects: aligned is more yellow than template (positive diff in B)
    diff_bright_yellow_raw = cv2.subtract(aligned_b, tpl_b)
    _, brighter_mask = cv2.threshold(diff_bright_yellow_raw, bright_threshold, 255, cv2.THRESH_BINARY)

    # Blue defects: aligned is bluer/less yellow than template (template B is higher than aligned B)
    diff_blue_raw = cv2.subtract(tpl_b, aligned_b)
    _, blue_mask = cv2.threshold(diff_blue_raw, blue_threshold, 255, cv2.THRESH_BINARY)

    # Red defects: aligned is redder than template (positive diff in A)
    diff_red_raw = cv2.subtract(aligned_a, tpl_a)
    _, red_mask = cv2.threshold(diff_red_raw, red_threshold, 255, cv2.THRESH_BINARY)

    # --- 4. Morphological Operations to Clean Masks ---
    # Use helper function to apply opening and closing
    darker_clean = _apply_morphological_ops(darker_mask_filtered, dark_morph_kernel_size, dark_morph_iterations)
    brighter_clean = _apply_morphological_ops(brighter_mask, bright_morph_kernel_size, bright_morph_iterations)
    blue_clean = _apply_morphological_ops(blue_mask, bright_morph_kernel_size, bright_morph_iterations)
    red_clean = _apply_morphological_ops(red_mask, bright_morph_kernel_size, bright_morph_iterations)

    # --- 5. Combine and Filter Defects ---
    # Combine all cleaned masks using logical OR
    combined_cleaned_temp = cv2.bitwise_or(darker_clean, brighter_clean)
    combined_cleaned_temp = cv2.bitwise_or(combined_cleaned_temp, blue_clean)
    combined_cleaned = cv2.bitwise_or(combined_cleaned_temp, red_clean)

    # Apply the overall inspection mask (ROI) to the combined result
    final_defect_mask = cv2.bitwise_and(combined_cleaned, combined_cleaned, mask=mask)

    # Find contours from the final defect mask
    contours, _ = cv2.findContours(final_defect_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours by minimum area to remove noise
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_defect_area]

    end_time = time.time()
    print(f"detect_defects took {end_time - start_time:.4f} seconds")

    # Return all intermediate masks for debugging/visualization
    return final_defect_mask, filtered_contours, darker_mask_filtered, brighter_mask, blue_mask, red_mask

'''import cv2
import numpy as np
import time

def detect_defects(tpl, aligned, mask,
                   dark_threshold, bright_threshold,
                   dark_morph_kernel_size, dark_morph_iterations,
                   bright_morph_kernel_size, bright_morph_iterations,
                   min_defect_area,
                   dark_gradient_threshold,
                   blue_threshold, red_threshold): # <--- NEW PARAMETERS
    """
    Detects defects by comparing a template image with an aligned current image.

    Args:
        tpl (np.array): The template image (BGR).
        aligned (np.array): The current image, already aligned to the template (BGR).
        mask (np.array): A grayscale mask defining the region of interest.
        dark_threshold (int): Threshold for detecting darker-than-template defects.
        bright_threshold (int): Threshold for detecting brighter-than-template defects (yellowish).
        dark_morph_kernel_size (int): Kernel size for morphological ops on dark defects.
        dark_morph_iterations (int): Iterations for morphological ops on dark defects.
        bright_morph_kernel_size (int): Kernel size for morphological ops on bright/color defects.
        bright_morph_iterations (int): Iterations for morphological ops on bright/color defects.
        min_defect_area (int): Minimum pixel area for a contour to be considered a defect.
        dark_gradient_threshold (int): Minimum gradient magnitude for a dark pixel to be considered a defect.
        blue_threshold (int): Threshold for detecting bluer-than-template defects. # <--- NEW
        red_threshold (int): Threshold for detecting redder-than-template defects.   # <--- NEW

    Returns:
        tuple: A tuple containing:
            - final_defect_mask (np.array): The binary mask showing detected defects.
            - filtered_contours (list): A list of contours representing detected defects.
            - darker_mask_filtered (np.array): The intermediate mask for darker defects (for debugging/info).
            - brighter_mask (np.array): The intermediate mask for brighter/yellow defects (for debugging/info).
            - blue_mask (np.array): The intermediate mask for blue defects (for debugging/info). # <--- NEW
            - red_mask (np.array): The intermediate mask for red defects (for debugging/info).   # <--- NEW
    """
    start_time = time.time()

    # Convert to grayscale
    t_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian Blur
    t_gray_blur = cv2.GaussianBlur(t_gray, (3, 3), 0)
    a_gray_blur = cv2.GaussianBlur(a_gray, (3, 3), 0)

    # Use CLAHE for histogram equalization
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    t_gray_eq = clahe.apply(t_gray_blur)
    a_gray_eq = clahe.apply(a_gray_blur)

    # --- 1. Grayscale Difference for Darker Defects ---
    # Darker: pixels in aligned are darker than template
    diff_dark_raw = cv2.subtract(t_gray_eq, a_gray_eq)
    darker_mask = cv2.threshold(diff_dark_raw, dark_threshold, 255, cv2.THRESH_BINARY)[1]

    # --- Shadow Avoidance: Gradient-based filtering for Dark Defects ---
    sobelx = cv2.Sobel(a_gray_eq, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(a_gray_eq, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = cv2.magnitude(sobelx, sobely)
    gradient_magnitude_normalized = cv2.normalize(gradient_magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, gradient_mask_dark = cv2.threshold(gradient_magnitude_normalized, dark_gradient_threshold, 255, cv2.THRESH_BINARY)
    darker_mask_filtered = cv2.bitwise_and(darker_mask, gradient_mask_dark)

    # --- 2. Color Differences using LAB Space ---
    tpl_lab = cv2.cvtColor(tpl, cv2.COLOR_BGR2LAB)
    aligned_lab = cv2.cvtColor(aligned, cv2.COLOR_BGR2LAB)

    tpl_a = tpl_lab[:, :, 1] # A channel: green (-) to red (+)
    aligned_a = aligned_lab[:, :, 1]
    tpl_b = tpl_lab[:, :, 2] # B channel: blue (-) to yellow (+)
    aligned_b = aligned_lab[:, :, 2]

    # Brighter/Yellow defects: aligned is more yellow than template (positive diff in B)
    diff_bright_yellow_raw = cv2.subtract(aligned_b, tpl_b)
    _, brighter_mask = cv2.threshold(diff_bright_yellow_raw, bright_threshold, 255, cv2.THRESH_BINARY)

    # Blue defects: aligned is bluer/less yellow than template (template B is higher than aligned B)
    diff_blue_raw = cv2.subtract(tpl_b, aligned_b) # Positive when template is yellower/aligned is bluer
    _, blue_mask = cv2.threshold(diff_blue_raw, blue_threshold, 255, cv2.THRESH_BINARY) # <--- NEW BLUE MASK

    # Red defects: aligned is redder than template (positive diff in A)
    diff_red_raw = cv2.subtract(aligned_a, tpl_a) # Positive when aligned is redder
    _, red_mask = cv2.threshold(diff_red_raw, red_threshold, 255, cv2.THRESH_BINARY) # <--- NEW RED MASK


    # --- Apply morphological operations separately with independent parameters ---

    # Ensure kernel size is odd and positive for dark defects
    effective_dark_kernel_size = dark_morph_kernel_size
    if effective_dark_kernel_size % 2 == 0:
        effective_dark_kernel_size += 1
    effective_dark_kernel_size = max(1, effective_dark_kernel_size)
    k_dark = np.ones((effective_dark_kernel_size, effective_dark_kernel_size), np.uint8)

    # Process darker defects mask
    darker_clean = cv2.morphologyEx(darker_mask_filtered, cv2.MORPH_OPEN, k_dark, iterations=dark_morph_iterations)
    darker_clean = cv2.morphologyEx(darker_clean, cv2.MORPH_CLOSE, k_dark, iterations=dark_morph_iterations)

    # Use bright kernel/iterations for all color defects for simplicity.
    effective_bright_kernel_size = bright_morph_kernel_size
    if effective_bright_kernel_size % 2 == 0:
        effective_bright_kernel_size += 1
    effective_bright_kernel_size = max(1, effective_bright_kernel_size)
    k_bright = np.ones((effective_bright_kernel_size, effective_bright_kernel_size), np.uint8)

    # Process brighter/yellow defects mask
    brighter_clean = cv2.morphologyEx(brighter_mask, cv2.MORPH_OPEN, k_bright, iterations=bright_morph_iterations)
    brighter_clean = cv2.morphologyEx(brighter_clean, cv2.MORPH_CLOSE, k_bright, iterations=bright_morph_iterations)

    # Process blue defects mask
    blue_clean = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, k_bright, iterations=bright_morph_iterations)
    blue_clean = cv2.morphologyEx(blue_clean, cv2.MORPH_CLOSE, k_bright, iterations=bright_morph_iterations)

    # Process red defects mask
    red_clean = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, k_bright, iterations=bright_morph_iterations)
    red_clean = cv2.morphologyEx(red_clean, cv2.MORPH_CLOSE, k_bright, iterations=bright_morph_iterations)

    # Combine ALL cleaned masks
    combined_cleaned_temp = cv2.bitwise_or(darker_clean, brighter_clean)
    combined_cleaned_temp = cv2.bitwise_or(combined_cleaned_temp, blue_clean)
    combined_cleaned = cv2.bitwise_or(combined_cleaned_temp, red_clean)


    # Apply the overall inspection mask (ROI)
    final_defect_mask = cv2.bitwise_and(combined_cleaned, combined_cleaned, mask=mask)

    # Find contours from the final defect mask
    contours, _ = cv2.findContours(final_defect_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours by minimum area
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_defect_area]

    end_time = time.time()
    print(f"detect_defects took {end_time - start_time:.4f} seconds")

    # Return all intermediate masks for debugging/visualization
    return final_defect_mask, filtered_contours, darker_mask_filtered, brighter_mask, blue_mask, red_mask'''