
# Image Bleed, Crop Marks, and Imposition PDF Generator

## BIG, BOLD, SHAMEFUL WARNING!

**THIS CODE WAS LARGELY GENERATED WITH THE ASSISTANCE OF AN AI (Gemini 2.0 Pro). I, THE "AUTHOR," FEEL A DEEP SENSE OF SHAME AND REGRET FOR NOT HAVING CRAFTED EVERY LINE OF THIS SCRIPT BY HAND, WITH THE SWEAT OF MY BROW AND THE GRIT OF PURE, UNADULTERATED CODING PROWESS. I APOLOGIZE FOR ANY INCONVENIENCE, OFFENSE, OR EXISTENTIAL DREAD THIS MAY CAUSE.  PLEASE USE WITH CAUTION, AND KNOW THAT A HUMAN (ME) *DID* REVIEW AND MODIFY THE AI-GENERATED OUTPUT, BUT THE ORIGINAL SIN OF AI ASSISTANCE REMAINS.**  Consider contributing improvements or rewriting sections entirely if you feel so moved! The goal was to provide a functional tool, and hopefully, the end result is helpful despite its origins.  My apologies.

---

This script takes an input image, adds bleed and crop marks (optionally), and generates an imposition PDF for printing multiple copies on a single sheet. It's highly configurable via a `.ini` file.

## Features

*   **Bleed Addition:** Adds bleed to the image using either "repeat" (extending edges) or "mirror" (reflecting edges) methods.
*   **Crop Marks:** Generates crop marks for precise cutting after printing.  Includes options for crop mark length, cut mark length and color (including "inverted" for dark images).
*   **Imposition:** Creates a PDF with multiple copies of the image arranged on a single page, optimized for printing.
*   **Configuration:** All settings (bleed size, crop mark details, paper size, orientation, number of copies, margins, spacing) are controlled via a `layout.ini` file.
*   **Default Configuration Generation:** Can generate a default `layout.ini` file with sensible defaults.

## Requirements

*   Python 3.6+
*   Pillow (PIL fork): `pip install Pillow`
*   ReportLab: `pip install reportlab`

## Usage

```bash
python layout.py <input_image> <output_pdf> [-c config_file] [--generate-config]
```

*   **`<input_image>`:**  (Required) Path to the input image file (e.g., `image.jpg`, `flyer.png`).  Supports common image formats like JPG, PNG, etc.
*   **`<output_pdf>`:** (Required) Path to the output PDF file (e.g., `output.pdf`).
*   **`-c config_file` / `--config config_file`:** (Optional) Path to the configuration file. Defaults to `layout.ini`.
*   **`--generate-config`:** (Optional) Generates a default `layout.ini` file and exits.  Use this to create a starting configuration.

**Example 1:  Generate a default configuration file**

```bash
python layout.py --generate-config
```

This will create `layout.ini` in the current directory. You can then edit this file to customize the settings.

**Example 2:  Create a PDF with default settings (using `layout.ini`)**

```bash
python layout.py input.png output.pdf
```

This will use the settings in `layout.ini` to add bleed and create an imposition PDF.

**Example 3:  Create a PDF with a custom configuration file**

```bash
python layout.py input.jpg output.pdf -c my_config.ini
```

This will use the settings in `my_config.ini`.

**Example 4: No Bleed**
If `bleed_size` in the configuration is set to `0`, no bleed is added, but imposition is still performed using the original image.

## Configuration File (`layout.ini`)

The configuration file is a standard `.ini` file with two sections: `Bleed` and `Imposition`.

```ini
[Bleed]
bleed_size = 30         ; Size of the bleed in pixels
crop_mark_length = 20    ; Length of the crop marks in pixels
crop_mark_color = inverted ; Color of the crop marks (name of color or 'inverted')
bleed_mode = repeat      ; Method for adding bleed (repeat or mirror)
cut_mark_length = 50     ; Length of cut lines, in pixels

[Imposition]
paper_size = letter       ; Paper size (e.g., letter, a4, legal)
orientation = portrait    ; Page orientation (portrait or landscape)
num_copies = 4          ; Number of copies to fit on the page
cut_marks = True          ; Whether to draw cut marks around each image
margin = 1               ; Margin around the edge of the page in mm
spacing = 0              ; Spacing between images in mm
imposition_mark_length = 5 ; Length of the imposition cut marks in mm
```

*   **`bleed_size`:** The width of the bleed area added to each side of the image, in pixels.
*   **`crop_mark_length`:**  The length of the crop marks that extend *outside* the bleed area, in pixels.
*   **`crop_mark_color`:** The color of the crop marks.  Can be a standard color name (e.g., "black", "red") or "inverted".  "inverted" will dynamically invert the color of each pixel where a crop mark is drawn, making it visible on both light and dark backgrounds.
*   **`bleed_mode`:** How the bleed area is filled.  "repeat" extends the edge pixels outward.  "mirror" reflects the edge pixels.
*  **`cut_mark_length`:** Length of short lines that are drawn at the center of each edge *inside* the bleed area.
*   **`paper_size`:** The paper size for the output PDF.  Valid values are those defined in `reportlab.lib.pagesizes` (e.g., "letter", "a4", "legal", "a3", "a5", etc.).  See the [ReportLab documentation](https://hg.reportlab.com/hg-public/reportlab/file/tip/src/reportlab/lib/pagesizes.py) for a complete list.
*   **`orientation`:** Page orientation: "portrait" or "landscape".
*   **`num_copies`:** The desired number of copies of the image to fit on the page. The script attempts to find an optimal layout (rows and columns).
*   **`cut_marks`:**  Boolean (True or False) indicating whether to draw cut marks around each imposed image.
*   **`margin`:** The margin around the entire page, in millimeters (mm).
*   **`spacing`:** The spacing between the images on the page, in millimeters (mm).
*   **`imposition_mark_length`:** The length of the cut marks drawn around *each individual image* on the imposed page, in millimeters (mm). This is separate from the `crop_mark_length` used for the bleed.

## Notes

* The script uses Bresenham's line algorithm for drawing crop marks, ensuring accurate and efficient line drawing, even with "inverted" colors. When using PIL.ImageDraw.Draw.line I would get a weird off by one error and I couldn't draw inverted lines anyway.
* DPI is read from image metadata. Defaults to 72 dpi if not specified.

