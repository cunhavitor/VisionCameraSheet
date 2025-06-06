import cv2
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

    # Process blue defects mask # <--- NEW
    blue_clean = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, k_bright, iterations=bright_morph_iterations)
    blue_clean = cv2.morphologyEx(blue_clean, cv2.MORPH_CLOSE, k_bright, iterations=bright_morph_iterations)

    # Process red defects mask # <--- NEW
    red_clean = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, k_bright, iterations=bright_morph_iterations)
    red_clean = cv2.morphologyEx(red_clean, cv2.MORPH_CLOSE, k_bright, iterations=bright_morph_iterations)

    # Combine ALL cleaned masks
    combined_cleaned_temp = cv2.bitwise_or(darker_clean, brighter_clean)
    combined_cleaned_temp = cv2.bitwise_or(combined_cleaned_temp, blue_clean) # <--- NEW
    combined_cleaned = cv2.bitwise_or(combined_cleaned_temp, red_clean)       # <--- NEW


    # Apply the overall inspection mask (ROI)
    final_defect_mask = cv2.bitwise_and(combined_cleaned, combined_cleaned, mask=mask)

    # Find contours from the final defect mask
    contours, _ = cv2.findContours(final_defect_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours by minimum area
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_defect_area]

    end_time = time.time()
    print(f"detect_defects took {end_time - start_time:.4f} seconds")

    # Return all intermediate masks for debugging/visualization
    return final_defect_mask, filtered_contours, darker_mask_filtered, brighter_mask, blue_mask, red_mask