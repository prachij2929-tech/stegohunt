import os
import re
import numpy as np
from PIL import Image


# ============================================================
# BASIC IMAGE LOADER
# ============================================================

def load_image(image_path):
    """
    Load PGM / JPG / PNG / JPEG / BMP and convert to grayscale.
    """
    img = Image.open(image_path).convert("L")
    return np.array(img, dtype=np.uint8)


# ============================================================
# LSB ANALYSIS
# ============================================================

def calculate_lsb_ratio(img):
    """
    Percentage of pixels whose LSB is 1.
    """
    lsb = img & 1
    return float(np.mean(lsb))


# ============================================================
# CHI-SQUARE STATISTICAL ANALYSIS
# ============================================================

def calculate_chi_square(img):
    """
    Histogram-based chi-square statistical indicator.
    """

    histogram = np.bincount(
        img.flatten(),
        minlength=256
    ).astype(float)

    expected = np.zeros(
        256,
        dtype=float
    )

    for i in range(0, 256, 2):

        pair_total = (
            histogram[i]
            + histogram[i + 1]
        )

        expected[i] = pair_total / 2.0
        expected[i + 1] = pair_total / 2.0

    chi_square = 0.0

    for i in range(256):

        if expected[i] > 0:

            chi_square += (
                (histogram[i] - expected[i]) ** 2
            ) / expected[i]

    return float(chi_square)


# ============================================================
# NOISE / LOCAL VARIATION
# ============================================================

def calculate_noise_level(img):

    img_float = img.astype(
        np.float32
    )

    horizontal = np.abs(
        img_float[:, 1:]
        - img_float[:, :-1]
    )

    vertical = np.abs(
        img_float[1:, :]
        - img_float[:-1, :]
    )

    values = np.concatenate([
        horizontal.flatten(),
        vertical.flatten()
    ])

    return float(
        np.mean(values)
    )


# ============================================================
# RANDOMNESS / ENTROPY SCORE
# ============================================================

def calculate_randomness_score(img):

    histogram = np.bincount(
        img.flatten(),
        minlength=256
    ).astype(np.float64)

    total = histogram.sum()

    if total == 0:
        return 0.0

    probabilities = (
        histogram / total
    )

    probabilities = probabilities[
        probabilities > 0
    ]

    entropy = -np.sum(
        probabilities
        * np.log2(probabilities)
    )

    score = (
        entropy / 8.0
    ) * 100.0

    return float(
        min(score, 100.0)
    )


# ============================================================
# FIND MATCHING COVER
# ============================================================

def find_matching_cover(stego_path):
    """
    Dataset pairing:

        1_SUNI_4.pgm -> 1_SUNI_2.pgm
        2_SUNI_4.pgm -> 2_SUNI_2.pgm
        5_SUNI_4.pgm -> 5_SUNI_2.pgm
    """

    directory = os.path.dirname(
        stego_path
    )

    filename = os.path.basename(
        stego_path
    )

    match = re.match(
        r"^(.*)_SUNI_4\.pgm$",
        filename,
        re.IGNORECASE
    )

    if not match:
        return None

    prefix = match.group(1)

    stego_dir = os.path.abspath(
        directory
    )

    dataset_dir = os.path.dirname(
        stego_dir
    )

    cover_dir = os.path.join(
        dataset_dir,
        "Cover"
    )

    cover_filename = (
        f"{prefix}_SUNI_2.pgm"
    )

    cover_path = os.path.join(
        cover_dir,
        cover_filename
    )

    if os.path.exists(cover_path):
        return cover_path

    return None


# ============================================================
# COVER VS STEGO COMPARISON
# ============================================================

def compare_cover_and_stego(
    cover_path,
    stego_path
):

    cover = load_image(
        cover_path
    )

    stego = load_image(
        stego_path
    )

    if cover.shape != stego.shape:

        return {
            "available": False,
            "error": (
                f"Image dimensions do not match: "
                f"Cover={cover.shape}, "
                f"Stego={stego.shape}"
            )
        }

    cover_float = cover.astype(
        np.int16
    )

    stego_float = stego.astype(
        np.int16
    )

    difference = np.abs(
        stego_float - cover_float
    )

    # --------------------------------------------------------
    # Changed pixels
    # --------------------------------------------------------

    changed_pixels = np.count_nonzero(
        difference
    )

    total_pixels = difference.size

    pixel_modification = (
        changed_pixels
        / total_pixels
    ) * 100.0

    # --------------------------------------------------------
    # Mean absolute difference
    # --------------------------------------------------------

    mean_absolute_difference = float(
        np.mean(difference)
    )

    # --------------------------------------------------------
    # LSB modification
    # --------------------------------------------------------

    cover_lsb = cover & 1
    stego_lsb = stego & 1

    lsb_changed = np.count_nonzero(
        cover_lsb != stego_lsb
    )

    lsb_modification = (
        lsb_changed
        / total_pixels
    ) * 100.0

    # --------------------------------------------------------
    # Maximum difference
    # --------------------------------------------------------

    max_difference = int(
        np.max(difference)
    )

    # --------------------------------------------------------
    # One-level changes
    # --------------------------------------------------------

    one_level_changes = np.count_nonzero(
        difference == 1
    )

    one_level_change_percentage = (
        one_level_changes
        / total_pixels
    ) * 100.0

    return {

        "available": True,

        "cover_file": os.path.basename(
            cover_path
        ),

        "stego_file": os.path.basename(
            stego_path
        ),

        "pixel_modification_percent": round(
            float(pixel_modification),
            4
        ),

        "lsb_modification_percent": round(
            float(lsb_modification),
            4
        ),

        "mean_absolute_difference": round(
            mean_absolute_difference,
            5
        ),

        "changed_pixel_count": int(
            changed_pixels
        ),

        "total_pixel_count": int(
            total_pixels
        ),

        "max_pixel_difference": (
            max_difference
        ),

        "one_level_change_percent": round(
            float(
                one_level_change_percentage
            ),
            4
        )
    }


# ============================================================
# HIDDEN MESSAGE EXTRACTION
# ============================================================

def extract_lsb_message(
    img,
    max_bytes=4096
):
    """
    Multi-method LSB hidden-message extraction.

    Tests:
    - Grayscale LSB
    - Bit planes 0, 1 and 2
    - Normal and reversed bit order
    - Printable-text detection

    This is an extraction attempt only.
    It does not claim that a payload exists when
    readable evidence is not recovered.
    """

    extraction_results = []

    # --------------------------------------------------------
    # Prepare grayscale image
    # --------------------------------------------------------

    gray = np.asarray(
        img,
        dtype=np.uint8
    )

    # --------------------------------------------------------
    # Helper: evaluate extracted bytes
    # --------------------------------------------------------

    def evaluate_bytes(
        bits,
        method_name
    ):

        usable_length = (
            len(bits) // 8
        ) * 8

        if usable_length == 0:
            return None

        bits = bits[
            :usable_length
        ]

        byte_array = np.packbits(
            bits,
            bitorder="big"
        )

        byte_array = byte_array[
            :max_bytes
        ]

        raw_bytes = (
            byte_array.tobytes()
        )

        if not raw_bytes:
            return None

        printable = 0

        for byte in raw_bytes:

            if (
                32 <= byte <= 126
                or byte in (9, 10, 13)
            ):
                printable += 1

        printable_ratio = (
            printable
            / len(raw_bytes)
        ) * 100.0

        decoded = raw_bytes.decode(
            "utf-8",
            errors="ignore"
        )

        readable_chars = []

        for char in decoded:

            if (
                char.isprintable()
                or char in "\n\r\t"
            ):
                readable_chars.append(char)

        message = "".join(
            readable_chars
        ).strip()

        # ----------------------------------------------------
        # Detect likely readable payload
        # ----------------------------------------------------

        found = (
            printable_ratio >= 70.0
            and len(message) >= 8
        )

        if len(message) > 1000:
            message = message[:1000]

        return {
            "method": method_name,
            "found": bool(found),
            "message": message if found else "",
            "printable_ratio": round(
                float(printable_ratio),
                2
            )
        }

    # --------------------------------------------------------
    # Test bit planes 0, 1 and 2
    # --------------------------------------------------------

    for bit_plane in [0, 1, 2]:

        bits = (
            (gray >> bit_plane) & 1
        ).flatten().astype(np.uint8)

        result = evaluate_bytes(
            bits,
            f"Grayscale Bit Plane {bit_plane}"
        )

        if result:
            extraction_results.append(
                result
            )

        # ----------------------------------------------------
        # Reverse bit order
        # ----------------------------------------------------

        reversed_bits = bits[::-1]

        result = evaluate_bytes(
            reversed_bits,
            f"Grayscale Bit Plane {bit_plane} Reversed"
        )

        if result:
            extraction_results.append(
                result
            )

    # --------------------------------------------------------
    # Select best result based on printable ratio
    # --------------------------------------------------------

    if not extraction_results:

        return {
            "attempted": True,
            "found": False,
            "message": "",
            "printable_ratio": 0.0,
            "method": "No usable extraction data"
        }

    best_result = max(
        extraction_results,
        key=lambda x: x["printable_ratio"]
    )

    # --------------------------------------------------------
    # Return forensic extraction result
    # --------------------------------------------------------

    return {
        "attempted": True,

        "found": bool(
            best_result["found"]
        ),

        "message": (
            best_result["message"]
            if best_result["found"]
            else ""
        ),

        "printable_ratio": (
            best_result["printable_ratio"]
        ),

        "method": best_result["method"]
    }


# ============================================================
# PAIRED CONCLUSION
# ============================================================

def generate_paired_conclusion(
    comparison
):

    if not comparison.get(
        "available"
    ):

        return (
            "Paired analysis unavailable."
        )

    pixel_change = comparison[
        "pixel_modification_percent"
    ]

    lsb_change = comparison[
        "lsb_modification_percent"
    ]

    mean_difference = comparison[
        "mean_absolute_difference"
    ]

    if (
        pixel_change >= 5
        or lsb_change >= 5
        or mean_difference >= 0.5
    ):

        return (
            "Significant paired-image "
            "modifications detected."
        )

    elif (
        pixel_change >= 1
        or lsb_change >= 1
        or mean_difference >= 0.1
    ):

        return (
            "Moderate paired-image "
            "modifications detected."
        )

    else:

        return (
            "Only minor paired-image "
            "modifications detected."
        )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_image(file_path):

    # --------------------------------------------------------
    # Load image
    # --------------------------------------------------------

    img = load_image(
        file_path
    )

    # --------------------------------------------------------
    # Statistical analysis
    # --------------------------------------------------------

    lsb_ratio = calculate_lsb_ratio(
        img
    )

    chi_square = calculate_chi_square(
        img
    )

    noise_level = calculate_noise_level(
        img
    )

    randomness_score = (
        calculate_randomness_score(
            img
        )
    )

    # --------------------------------------------------------
    # Base heuristic scores
    # --------------------------------------------------------

    lsb_score = (
        abs(lsb_ratio - 0.5)
        * 100.0
    )

    chi_score = min(
        chi_square / 1000.0,
        100.0
    )

    noise_score = min(
        noise_level * 10.0,
        100.0
    )

    randomness_component = (
        randomness_score
    )

    # --------------------------------------------------------
    # Base risk
    # --------------------------------------------------------

    base_risk = (

        (chi_score * 0.30)

        + (noise_score * 0.20)

        + (
            randomness_component
            * 0.15
        )

        + (lsb_score * 0.15)
    )

    # --------------------------------------------------------
    # Hidden message analysis
    # --------------------------------------------------------

    hidden_message = (
        extract_lsb_message(img)
    )

    # --------------------------------------------------------
    # Find matching Cover
    # --------------------------------------------------------

    cover_path = find_matching_cover(
        file_path
    )

    paired_analysis = {

        "available": False,

        "message": (
            "No matching cover image "
            "found. Single-image "
            "analysis performed."
        )
    }

    # ========================================================
    # PAIRED ANALYSIS
    # ========================================================

    if cover_path:

        paired_analysis = compare_cover_and_stego(
            cover_path,
            file_path
        )

        if paired_analysis.get("available"):

            pixel_change = paired_analysis[
                "pixel_modification_percent"
            ]

            lsb_change = paired_analysis[
                "lsb_modification_percent"
            ]

            mean_difference = paired_analysis[
                "mean_absolute_difference"
            ]

            # ------------------------------------------------
            # Paired evidence scores
            # ------------------------------------------------

            pixel_score = min(
                pixel_change * 10.0,
                100.0
            )

            paired_lsb_score = min(
                lsb_change * 10.0,
                100.0
            )

            difference_score = min(
                mean_difference * 100.0,
                100.0
            )

            # ------------------------------------------------
            # Combined paired score
            # ------------------------------------------------

            paired_score = (
                (pixel_score * 0.40)
                + (paired_lsb_score * 0.40)
                + (difference_score * 0.20)
            )

            # ------------------------------------------------
            # Combined risk
            # ------------------------------------------------

            risk = (
                (base_risk * 0.25)
                + (paired_score * 0.75)
            )

            risk = max(
                0.0,
                min(100.0, risk)
            )

            # ------------------------------------------------
            # Paired conclusion
            # ------------------------------------------------

            paired_analysis[
                "conclusion"
            ] = generate_paired_conclusion(
                paired_analysis
            )

        else:

            risk = base_risk

    else:

      risk = base_risk

    # ========================================================
    # FINAL PREDICTION
    # ========================================================

    if risk >= 60:

        prediction = (
            "Stego Image Detected"
        )

    elif risk >= 40:

        prediction = (
            "Suspicious Image"
        )

    else:

        prediction = (
            "Likely Cover Image"
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {

        # Existing keys
        "prediction": prediction,

        "risk": round(
            float(risk),
            2
        ),

        "chi_square": round(
            float(chi_square),
            4
        ),

        "lsb_ratio": round(
            float(lsb_ratio),
            6
        ),

        "noise_level": round(
            float(noise_level),
            6
        ),

        "randomness_score": round(
            float(randomness_score),
            2
        ),

        # Analysis information
        "analysis_method": (
            "Statistical + LSB "
            "Forensic Analysis"
        ),

        "machine_learning_used": False,

        "cnn_used": False,

        # Hidden message
        "hidden_message_analysis": (
            hidden_message
        ),

        # Paired analysis
        "paired_analysis": (
            paired_analysis
        )
    }

    return result


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    test_file = (
        r"C:\caps\Dataset\Stego\1_SUNI_4.pgm"
    )

    if not os.path.exists(
        test_file
    ):

        print(
            "Test file not found:"
        )

        print(
            test_file
        )

    else:

        result = analyze_image(
            test_file
        )

        print(
            "\n==================================="
        )

        print(
            "STEGO FORENSIC ANALYSIS"
        )

        print(
            "===================================\n"
        )

        for key, value in result.items():

            print(
                f"{key}: {value}"
            )

