from __future__ import annotations

from pathlib import Path


def _leaf_mask_rgb(arr):
    """
    Estimate leaf pixels using simple RGB heuristics.
    arr: float32 array in [0,1] shape (H,W,3)
    """
    import numpy as np

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    # Leaf tends to be greener than background; keep thresholds loose.
    green = (g > 0.18) & (g > r + 0.04) & (g > b + 0.04)
    green = green | ((g > 0.25) & (r < 0.55) & (b < 0.55))

    # Many disease images include dark lesions; those pixels may fail the "green" test.
    # Include dark pixels that are adjacent to the green leaf region. We prefer SciPy
    # morphology here (lighter dependency footprint than scikit-image).
    value = np.maximum(np.maximum(r, g), b)
    dark = value < 0.32

    # 1) SciPy path
    try:
        from scipy import ndimage as ndi  # type: ignore

        grown = ndi.binary_dilation(green, iterations=6)
        leaf = green | (dark & grown)
        leaf = ndi.binary_closing(leaf, iterations=3)
        return leaf
    except Exception:
        pass

    # 2) scikit-image path (if installed)
    try:
        from skimage.morphology import binary_closing, binary_dilation, disk  # type: ignore

        grown = binary_dilation(green, disk(6))
        leaf = green | (dark & grown)
        leaf = binary_closing(leaf, disk(3))
        return leaf
    except Exception:
        pass

    # 3) Fallback: just use the green mask
    grown = green.copy()
    # Grow by 6 iterations using a simple 8-neighborhood dilation.
    for _ in range(6):
        m = grown
        # pad by 1 so shifts don't wrap
        p = np.pad(m, ((1, 1), (1, 1)), mode="constant", constant_values=False)
        grown = (
            p[1:-1, 1:-1]
            | p[:-2, 1:-1]
            | p[2:, 1:-1]
            | p[1:-1, :-2]
            | p[1:-1, 2:]
            | p[:-2, :-2]
            | p[:-2, 2:]
            | p[2:, :-2]
            | p[2:, 2:]
        )

    leaf = green | (dark & grown)
    return leaf


def _remove_small_components(mask, min_size: int):
    """Remove connected components smaller than min_size. Best-effort with SciPy, fallback to no-op."""
    try:
        import numpy as np
        from scipy import ndimage as ndi  # type: ignore

        lab, n = ndi.label(mask)
        if n <= 0:
            return mask, 0
        counts = np.bincount(lab.ravel())
        # background label 0 stays background
        keep = counts >= int(min_size)
        keep[0] = False
        out = keep[lab]
        kept = int(keep[1:].sum()) if keep.size > 1 else 0
        return out, kept
    except Exception:
        pass

    # Pure-numpy/Python fallback (4-connected), good enough for 200x200 masks.
    try:
        import numpy as np
        from collections import deque

        h, w = mask.shape
        seen = np.zeros((h, w), dtype=bool)
        out = np.zeros((h, w), dtype=bool)
        kept = 0

        def neigh(y, x):
            if y > 0:
                yield y - 1, x
            if y + 1 < h:
                yield y + 1, x
            if x > 0:
                yield y, x - 1
            if x + 1 < w:
                yield y, x + 1

        for y in range(h):
            for x in range(w):
                if not mask[y, x] or seen[y, x]:
                    continue
                q = deque([(y, x)])
                seen[y, x] = True
                coords = []
                while q:
                    cy, cx = q.popleft()
                    coords.append((cy, cx))
                    for ny, nx in neigh(cy, cx):
                        if mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                if len(coords) >= int(min_size):
                    kept += 1
                    for cy, cx in coords:
                        out[cy, cx] = True

        return out, kept
    except Exception:
        return mask, 0


def extract_features(image_path: Path) -> list[float]:
    # Simple, fast features that work on CPU and on Python 3.13:
    # - per-channel color histogram (16 bins each)
    # - per-channel mean and std
    from PIL import Image

    img = Image.open(image_path).convert("RGB").resize((128, 128))
    pixels = list(img.getdata())

    bins = 16
    hist_r = [0] * bins
    hist_g = [0] * bins
    hist_b = [0] * bins

    rs = []
    gs = []
    bs = []
    for r, g, b in pixels:
        hist_r[r * bins // 256] += 1
        hist_g[g * bins // 256] += 1
        hist_b[b * bins // 256] += 1
        rs.append(r)
        gs.append(g)
        bs.append(b)

    total = float(len(pixels)) if pixels else 1.0
    hist = [h / total for h in (hist_r + hist_g + hist_b)]

    def _mean_std(values: list[int]) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0
        m = sum(values) / float(len(values))
        v = sum((x - m) ** 2 for x in values) / float(len(values))
        return m / 255.0, (v ** 0.5) / 255.0

    mr, sr = _mean_std(rs)
    mg, sg = _mean_std(gs)
    mb, sb = _mean_std(bs)
    features = hist + [mr, sr, mg, sg, mb, sb]

    # Add lightweight texture/structure features (no extra deps).
    try:
        import numpy as np

        arr = np.array(img).astype("float32") / 255.0  # (128,128,3)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]
        gray = (0.299 * r + 0.587 * g + 0.114 * b).clip(0.0, 1.0)

        # Grayscale histogram (captures disease discoloration patterns).
        gray_hist, _ = np.histogram(gray, bins=16, range=(0.0, 1.0))
        gray_hist = (gray_hist / float(gray.size)).astype("float32")
        features.extend([float(x) for x in gray_hist])

        # Edge magnitude stats + histogram (captures spotting/lesion texture).
        gx = np.abs(gray[:, 1:] - gray[:, :-1])
        gy = np.abs(gray[1:, :] - gray[:-1, :])
        # Match shapes
        gxm = gx[:-1, :]
        gym = gy[:, :-1]
        mag = (gxm + gym).clip(0.0, 1.0)
        features.extend([float(mag.mean()), float(mag.std())])
        mag_hist, _ = np.histogram(mag, bins=8, range=(0.0, 1.0))
        mag_hist = (mag_hist / float(mag.size)).astype("float32")
        features.extend([float(x) for x in mag_hist])

        # Low-res pooled grayscale (keeps some spatial layout information).
        small = np.array(Image.open(image_path).convert("L").resize((64, 64))).astype("float32") / 255.0
        pooled = small.reshape(16, 4, 16, 4).mean(axis=(1, 3))  # (16,16)
        features.extend([float(x) for x in pooled.reshape(-1)[:256]])
    except Exception:
        pass

    # Add HOG (shape/texture) features when available.
    try:
        from skimage.color import rgb2gray
        from skimage.feature import hog

        import numpy as np

        arr = np.array(img).astype("float32") / 255.0
        gray = rgb2gray(arr)
        hog_vec = hog(
            gray,
            orientations=9,
            pixels_per_cell=(8, 8),
            cells_per_block=(2, 2),
            block_norm="L2-Hys",
            feature_vector=True,
        )
        # Keep feature size bounded for small datasets.
        hog_vec = hog_vec[:500]
        features.extend([float(x) for x in hog_vec])
    except Exception:
        pass

    # Ensure all features are finite and bounded.
    out: list[float] = []
    for x in features:
        try:
            fx = float(x)
        except Exception:
            fx = 0.0
        if fx != fx:  # NaN
            fx = 0.0
        if fx == float("inf") or fx == float("-inf"):
            fx = 0.0
        # Clamp extreme values to keep linear models stable.
        if fx > 10.0:
            fx = 10.0
        if fx < -10.0:
            fx = -10.0
        out.append(fx)
    return out


def looks_healthy(image_path: Path) -> bool:
    """
    Very lightweight heuristic for demo usability:
    - healthy leaves tend to be strongly green with limited brown/yellow spotting
    - returns True when image appears mostly green and not heavily spotted
    """
    from PIL import Image

    import numpy as np

    img = Image.open(image_path).convert("RGB").resize((200, 200))
    arr = (np.array(img).astype("float32") / 255.0).clip(0.0, 1.0)

    leaf = _leaf_mask_rgb(arr)
    leaf_px = int(leaf.sum())
    if leaf_px < 500:
        # If we can't find the leaf reliably, do not claim healthy.
        return False

    r = arr[:, :, 0][leaf]
    g = arr[:, :, 1][leaf]
    b = arr[:, :, 2][leaf]

    green = (g > r + 0.06) & (g > b + 0.06) & (g > 0.25)
    green_ratio = float(green.sum()) / float(leaf_px)

    # Dark/brown lesion proxy, within leaf only.
    value = np.maximum(np.maximum(arr[:, :, 0], arr[:, :, 1]), arr[:, :, 2])
    dark = (value < 0.35) & leaf
    brown = ((arr[:, :, 0] > 0.38) & (arr[:, :, 1] > 0.22) & (arr[:, :, 2] < 0.25)) & leaf
    spots = dark | brown

    # Remove tiny noise so a few pixels don't flip the result.
    spots, spot_components = _remove_small_components(spots, min_size=18)
    spot_ratio = float(spots.sum()) / float(leaf_px)

    # Healthy should be strongly green with very few lesions.
    # NOTE: this must be strict; otherwise diseased leaves get mislabeled "Healthy (heuristic)".
    return green_ratio >= 0.55 and spot_ratio <= 0.015 and spot_components <= 3


def spot_metrics(image_path: Path) -> dict:
    """
    Extract lesion/spot metrics for simple, explainable classification.
    Works best for close-up leaf images on a plain-ish background.
    """
    from PIL import Image

    try:
        import numpy as np
        from skimage.color import rgb2hsv
        from skimage.measure import label, regionprops
        from skimage.morphology import remove_small_objects
    except Exception:
        # If scikit-image isn't installed, return empty metrics.
        return {"ok": False}

    img = Image.open(image_path).convert("RGB").resize((256, 256))
    arr = (np.array(img).astype("float32") / 255.0).clip(0.0, 1.0)
    hsv = rgb2hsv(arr)

    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # Rough foreground leaf mask: prefer RGB heuristic over HSV (more robust on small photos).
    leaf = _leaf_mask_rgb(arr)

    # Spot candidates: dark pixels OR brown-ish pixels within the leaf.
    dark = (v < 0.30) & leaf
    brown = ((h < 0.12) | (h > 0.92)) & (s > 0.25) & (v < 0.70) & leaf
    spots = dark | brown

    spots = remove_small_objects(spots, min_size=10)
    lab = label(spots)
    regions = regionprops(lab)

    total_leaf = int(leaf.sum()) or 1
    total_spots = int(spots.sum())
    spot_ratio = total_spots / float(total_leaf)

    areas = [int(r.area) for r in regions]
    areas.sort(reverse=True)
    count = len(areas)
    mean_area = (sum(areas) / float(count)) if count else 0.0
    max_area = float(areas[0]) if areas else 0.0

    return {
        "ok": True,
        "leaf_px": total_leaf,
        "spot_px": total_spots,
        "spot_ratio": float(spot_ratio),
        "spot_count": int(count),
        "spot_mean_area": float(mean_area),
        "spot_max_area": float(max_area),
    }


def heuristic_classify(image_path: Path) -> dict:
    """
    Heuristic classifier tuned for the current 3-class demo dataset:
    Healthy / Cercospora_leaf_spot / Early_blight.
    """
    m = spot_metrics(image_path)
    if not m.get("ok"):
        return {"label": "Unknown", "confidence": 0.0, "reason": "heuristic unavailable"}

    spot_ratio = float(m["spot_ratio"])
    count = int(m["spot_count"])
    mean_area = float(m["spot_mean_area"])
    max_area = float(m["spot_max_area"])

    # Healthy: very low spot ratio.
    if spot_ratio < 0.03 and count <= 4:
        return {"label": "Healthy", "confidence": 0.80, "reason": "very low spot ratio"}

    # Cercospora: many small spots.
    if count >= 8 and mean_area <= 220 and spot_ratio <= 0.20:
        return {"label": "Cercospora_leaf_spot", "confidence": 0.75, "reason": "many small spots"}

    # Early blight: fewer but larger lesions (often darker).
    if max_area >= 420 or mean_area >= 260:
        return {"label": "Early_blight", "confidence": 0.72, "reason": "larger lesions"}

    # Default: pick based on count/area blend.
    if count >= 6:
        return {"label": "Cercospora_leaf_spot", "confidence": 0.60, "reason": "moderate spot count"}
    return {"label": "Early_blight", "confidence": 0.58, "reason": "moderate lesion size"}
