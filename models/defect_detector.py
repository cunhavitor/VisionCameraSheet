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
    effective_kernel_size = max(1, kernel_size + 1 if kernel_size % 2 == 0 else kernel_size)
    kernel = np.ones((effective_kernel_size, effective_kernel_size), np.uint8)

    clean_mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)
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

    Returns:
        tuple: (final_defect_mask, filtered_contours,
               darker_mask_filtered, brighter_mask,
               blue_mask, red_mask)
    """
    start_time = time.perf_counter()

    # --- Grayscale Preprocessing ---
    t_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    t_gray_eq = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(cv2.GaussianBlur(t_gray, (3, 3), 0))
    a_gray_eq = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(cv2.GaussianBlur(a_gray, (3, 3), 0))

    # --- Darker Defect Detection ---
    diff_dark_raw = cv2.subtract(t_gray_eq, a_gray_eq)
    darker_mask = cv2.threshold(diff_dark_raw, dark_threshold, 255, cv2.THRESH_BINARY)[1]
    morph_grad = cv2.morphologyEx(a_gray_eq, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
    _, gradient_mask_dark = cv2.threshold(morph_grad, dark_gradient_threshold, 255, cv2.THRESH_BINARY)
    darker_mask_filtered = cv2.bitwise_and(darker_mask, gradient_mask_dark)

    # --- Color Defect Detection in LAB Space ---
    tpl_lab = cv2.cvtColor(tpl, cv2.COLOR_BGR2LAB)
    aligned_lab = cv2.cvtColor(aligned, cv2.COLOR_BGR2LAB)

    diff_bright_yellow_raw = cv2.subtract(aligned_lab[:, :, 2], tpl_lab[:, :, 2])
    _, brighter_mask = cv2.threshold(diff_bright_yellow_raw, bright_threshold, 255, cv2.THRESH_BINARY)

    diff_blue_raw = cv2.subtract(tpl_lab[:, :, 2], aligned_lab[:, :, 2])
    _, blue_mask = cv2.threshold(diff_blue_raw, blue_threshold, 255, cv2.THRESH_BINARY)

    diff_red_raw = cv2.subtract(aligned_lab[:, :, 1], tpl_lab[:, :, 1])
    _, red_mask = cv2.threshold(diff_red_raw, red_threshold, 255, cv2.THRESH_BINARY)

    # --- Morphological Cleaning ---
    darker_clean = _apply_morphological_ops(darker_mask_filtered, dark_morph_kernel_size, dark_morph_iterations)
    brighter_clean = _apply_morphological_ops(brighter_mask, bright_morph_kernel_size, bright_morph_iterations)
    blue_clean = _apply_morphological_ops(blue_mask, bright_morph_kernel_size, bright_morph_iterations)
    red_clean = _apply_morphological_ops(red_mask, bright_morph_kernel_size, bright_morph_iterations)

    # --- Combine and Mask ROI ---
    combined = cv2.bitwise_or(darker_clean, brighter_clean)
    combined = cv2.bitwise_or(combined, blue_clean)
    combined = cv2.bitwise_or(combined, red_clean)
    final_defect_mask = cv2.bitwise_and(combined, combined, mask=mask)

    contours, _ = cv2.findContours(final_defect_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_defect_area]

    end_time = time.perf_counter()
    print(f"detect_defects took {end_time - start_time:.4f} seconds")

    return final_defect_mask, filtered_contours, darker_mask_filtered, brighter_mask, blue_mask, red_mask
