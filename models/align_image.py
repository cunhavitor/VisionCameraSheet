import cv2
import numpy as np
import json


def align_with_template(current_img, template_img, config_path="config/config_alignment.json"):
    """
    Alinha a imagem atual com o template usando ORB + Homografia, com parâmetros carregados de ficheiro JSON.
    """

    # ✅ Carregar parâmetros do ficheiro JSON
    with open(config_path, "r") as f:
        config = json.load(f)

    max_features = config.get("max_features", 1000)
    good_match_percent = config.get("good_match_percent", 0.2)

    # Converter para grayscale se necessário
    if len(template_img.shape) == 3:
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    else:
        template_gray = template_img

    if len(current_img.shape) == 3:
        current_gray = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
    else:
        current_gray = current_img

    # ORB
    orb = cv2.ORB_create(nfeatures=max_features)
    keypoints1, descriptors1 = orb.detectAndCompute(template_gray, None)
    keypoints2, descriptors2 = orb.detectAndCompute(current_gray, None)

    # Matcher
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(descriptors1, descriptors2)
    matches = sorted(matches, key=lambda x: x.distance)

    num_good_matches = int(len(matches) * good_match_percent)
    matches = matches[:num_good_matches]

    if len(matches) < 4:
        raise ValueError("Não foi possível encontrar matches suficientes para alinhamento.")

    # Pontos correspondentes
    points1 = np.float32([keypoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    points2 = np.float32([keypoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

    # Homografia
    h, mask = cv2.findHomography(points2, points1, cv2.RANSAC)

    # Aplicar warpPerspective
    height, width = template_gray.shape
    aligned_img = cv2.warpPerspective(current_img, h, (width, height))

    return aligned_img, h
