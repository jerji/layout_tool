import argparse
import configparser
import math
import os
import sys
from typing import List, Tuple, Optional, Dict, Any

import reportlab
from PIL import Image, ImageDraw, UnidentifiedImageError
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def generate_default_config() -> configparser.ConfigParser:
    """Generates a default configuration."""
    config = configparser.ConfigParser()

    config['Bleed'] = {
        'bleed_size': '30',  # in pixels
        'crop_mark_length': '20',  # in pixels
        'crop_mark_color': 'inverted',
        'bleed_mode': 'repeat',
        'cut_mark_length': '50',  # in pixels
    }

    config['Imposition'] = {
        'paper_size': 'letter',
        'orientation': 'portrait',
        'num_copies': '4',
        'cut_marks': 'True',
        'margin': '1',  # in mm
        'spacing': '0',  # in mm
        'imposition_mark_length': '5',  # in mm
    }

    return config


def write_config_to_file(config: configparser.ConfigParser, filename: str = "layout.ini"):
    """Writes the configuration to a file."""
    with open(filename, 'w') as configfile:
        config.write(configfile)


def load_config(config_path: str) -> configparser.ConfigParser:
    """Loads configuration from a .ini file."""
    if not os.path.isfile(config_path):
        print('Configuration file not found.', file=sys.stderr)
        result = input('Use Default? (4 flyers on letter paper in portrait mode) Y/n')
        if result == 'Y' or result == '':
            return generate_default_config()
        else:
            print('No configuration file found, use --generate-config to create one.', file=sys.stderr)
            sys.exit(1)
    config = configparser.ConfigParser()
    config.read(config_path)
    return config


# --- PIL-related functions (Bleed) ---

def _open_image(image_path: str) -> Tuple[Optional[Image.Image], Optional[int], Optional[int]]:
    """Opens the image and returns it, along with its width and height."""
    try:
        img = Image.open(image_path)
        return img, img.width, img.height
    except (FileNotFoundError, UnidentifiedImageError) as e:
        print(f"Error opening image: {e}")
        sys.exit(1)


def _add_repeat_bleed(new_img: Image.Image, img: Image.Image, width: int, height: int, bleed_size: int):
    """Adds bleed by repeating the edges."""
    for i in range(bleed_size):
        new_img.paste(img.crop((0, 0, 1, height)), (bleed_size - i - 1, bleed_size))
        new_img.paste(img.crop((width - 1, 0, width, height)), (bleed_size + width + i, bleed_size))
        new_img.paste(img.crop((0, 0, width, 1)), (bleed_size, bleed_size - i - 1))
        new_img.paste(img.crop((0, height - 1, width, height)), (bleed_size, bleed_size + height + i))
        new_img.paste(img.crop((0, 0, 1, 1)), (bleed_size - i - 1, bleed_size - i - 1))
        new_img.paste(img.crop((width - 1, 0, width, 1)), (bleed_size + width + i, bleed_size - i - 1))
        new_img.paste(img.crop((0, height - 1, 1, height)), (bleed_size - i - 1, bleed_size + height + i))
        new_img.paste(img.crop((width - 1, height - 1, width, height)),
                      (bleed_size + width + i, bleed_size + height + i))


def _add_mirror_bleed(new_img: Image.Image, img: Image.Image, width: int, height: int, bleed_size: int):
    """Adds bleed by mirroring the edges."""
    new_img.paste(img.crop((0, 0, bleed_size, height)).transpose(Image.FLIP_LEFT_RIGHT), (0, bleed_size))
    new_img.paste(img.crop((width - bleed_size, 0, width, height)).transpose(Image.FLIP_LEFT_RIGHT),
                  (width + bleed_size, bleed_size))
    new_img.paste(img.crop((0, 0, width, bleed_size)).transpose(Image.FLIP_TOP_BOTTOM), (bleed_size, 0))
    new_img.paste(img.crop((0, height - bleed_size, width, height)).transpose(Image.FLIP_TOP_BOTTOM),
                  (bleed_size, height + bleed_size))


def _create_new_image_with_bleed(img: Image.Image, width: int, height: int, bleed_size: int,
                                 bleed_mode: str) -> Tuple[Image.Image, int, int]:
    """Creates a new image with the specified bleed."""
    new_width = width + 2 * bleed_size
    new_height = height + 2 * bleed_size
    new_img = Image.new("RGB", (new_width, new_height), "white")
    new_img.paste(img, (bleed_size, bleed_size))

    if bleed_mode == 'repeat':
        _add_repeat_bleed(new_img, img, width, height, bleed_size)
    elif bleed_mode == 'mirror':
        _add_mirror_bleed(new_img, img, width, height, bleed_size)
    else:
        raise ValueError("bleed_mode must be 'repeat' or 'mirror'")

    return new_img, new_width, new_height


def _draw_line(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, image_width: int, image_height: int,
               color: str = "black", width: int = 2):
    """Draws a line using Bresenham's algorithm, handling per-pixel inversion."""
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx, sy = 1 if x1 < x2 else -1, 1 if y1 < y2 else -1
    err = (dx if dx > dy else -dy) / 2

    temp_img = draw._image.copy()  # Make a copy of the image
    while True:
        if 0 <= x1 < image_width and 0 <= y1 < image_height:
            for i in range(-(width // 2), (width + 1) // 2):
                for j in range(-(width // 2), (width + 1) // 2):
                    px, py = x1 + i, y1 + j
                    # Bounds check is still needed *inside* the loop
                    if 0 <= px < image_width and 0 <= py < image_height:
                        if color.lower() == 'inverted':
                            r, g, b = temp_img.getpixel((px, py))  # Read color from (px, py)
                            chosen_color = (255 - r, 255 - g, 255 - b)
                        else:
                            chosen_color = color
                        draw.point((px, py), fill=chosen_color)
        if x1 == x2 and y1 == y2:
            break
        e2 = err
        if e2 > -dx:
            err -= dy
            x1 += sx
        if e2 < dy:
            err += dx
            y1 += sy


def _draw_bleed_crop_marks(draw: ImageDraw.ImageDraw, image_width: int, image_height: int, bleed_size: int,
                           crop_mark_length: int, cut_mark_length: int, crop_mark_color: str):
    """Draws crop and cut marks for bleed."""
    _draw_line(draw, bleed_size - crop_mark_length, bleed_size, bleed_size, bleed_size, image_width, image_height,
               color=crop_mark_color, width=2)
    _draw_line(draw, bleed_size, bleed_size - crop_mark_length, bleed_size, bleed_size, image_width, image_height,
               color=crop_mark_color, width=2)
    _draw_line(draw, image_width - bleed_size, bleed_size - crop_mark_length, image_width - bleed_size, bleed_size,
               image_width, image_height, color=crop_mark_color, width=2)
    _draw_line(draw, image_width - bleed_size, bleed_size, image_width - bleed_size + crop_mark_length, bleed_size,
               image_width, image_height, color=crop_mark_color, width=2)
    _draw_line(draw, bleed_size - crop_mark_length, image_height - bleed_size, bleed_size, image_height - bleed_size,
               image_width, image_height, color=crop_mark_color, width=2)
    _draw_line(draw, bleed_size, image_height - bleed_size, bleed_size,
               image_height - bleed_size + crop_mark_length, image_width, image_height, color=crop_mark_color, width=2)
    _draw_line(draw, image_width - bleed_size, image_height - bleed_size, image_width - bleed_size + crop_mark_length,
               image_height - bleed_size, image_width, image_height, color=crop_mark_color, width=2)
    _draw_line(draw, image_width - bleed_size, image_height - bleed_size, image_width - bleed_size,
               image_height - bleed_size + crop_mark_length, image_width, image_height, color=crop_mark_color, width=2)
    _draw_line(draw, image_width // 2 - cut_mark_length // 2, bleed_size, image_width // 2 + cut_mark_length // 2,
               bleed_size, image_width, image_height, color=crop_mark_color, width=2)
    _draw_line(draw, image_width // 2 - cut_mark_length // 2, image_height - bleed_size,
               image_width // 2 + cut_mark_length // 2, image_height - bleed_size, image_width, image_height,
               color=crop_mark_color, width=2)
    _draw_line(draw, bleed_size, image_height // 2 - cut_mark_length // 2, bleed_size,
               image_height // 2 + cut_mark_length // 2, image_width, image_height, color=crop_mark_color, width=2)
    _draw_line(draw, image_width - bleed_size, image_height // 2 - cut_mark_length // 2, image_width - bleed_size,
               image_height // 2 + cut_mark_length // 2, image_width, image_height, color=crop_mark_color, width=2)


def add_bleed_and_marks(image_path: str, bleed_size: int, crop_mark_length: int,
                        crop_mark_color: str, bleed_mode: str, cut_mark_length: int) -> Optional[Image.Image]:
    """Adds bleed and crop marks to the image. Returns the modified image object, or None on failure. [Bleed]"""
    img, width, height = _open_image(image_path)
    if img is None:
        return None

    try:
        new_img, new_width, new_height = _create_new_image_with_bleed(img, width, height, bleed_size, bleed_mode)
        draw = ImageDraw.Draw(new_img)
        _draw_bleed_crop_marks(draw, new_width, new_height, bleed_size, crop_mark_length, cut_mark_length,
                               crop_mark_color)
        return new_img
    except Exception as e:
        print(f"Error adding bleed and marks: {e}")
        return None


# --- ReportLab-related functions (Imposition) ---

def _get_image_dimensions(img: Image.Image) -> Tuple[float, float]:
    """Returns the image's dimensions in mm."""
    image_width, image_height = img.size
    dpi = img.info.get('dpi', (72, 72))  # Default to 72 DPI if not specified
    image_width_mm = (image_width / dpi[0]) * 25.4
    image_height_mm = (image_height / dpi[1]) * 25.4
    return image_width_mm, image_height_mm


def _calculate_layout(image_width_mm: float, image_height_mm: float, page_width: float, page_height: float,
                      num_copies: int, margin: float, spacing: float) -> Tuple[
    int, int, float, float, List[Tuple[float, float]]]:
    """Calculates the optimal layout for images on the page."""
    available_width = page_width - 2 * margin
    available_height = page_height - 2 * margin

    cols = int(math.sqrt(num_copies))
    rows = (num_copies + cols - 1) // cols

    while True:
        temp_cols = cols + 1
        temp_rows = (num_copies + temp_cols - 1) // temp_cols
        if temp_rows < rows:
            rows, cols = temp_rows, temp_cols
        else:
            break

    max_width = (available_width - (cols - 1) * spacing) / cols
    max_height = (available_height - (rows - 1) * spacing) / rows

    scale = min(max_width / image_width_mm, max_height / image_height_mm)
    scaled_width, scaled_height = image_width_mm * scale, image_height_mm * scale

    image_positions = []
    for row in range(rows):
        for col in range(cols):
            if (row * cols + col) < num_copies:
                x = margin + col * (scaled_width + spacing)
                y = page_height - margin - (row + 1) * (scaled_height + spacing)
                image_positions.append((x, y))

    return cols, rows, scaled_width, scaled_height, image_positions


def _draw_cut_marks(c: canvas.Canvas, x: float, y: float, width: float, height: float, mark_length: float = 5 * mm):
    """Draws cut marks around a rectangle."""
    c.line(x, y + height, x + mark_length, y + height)
    c.line(x, y + height, x, y + height - mark_length)
    c.line(x + width, y + height, x + width - mark_length, y + height)
    c.line(x + width, y + height, x + width, y + height - mark_length)
    c.line(x, y, x + mark_length, y)
    c.line(x, y, x, y + mark_length)
    c.line(x + width, y, x + width - mark_length, y)
    c.line(x + width, y, x + width, y + mark_length)


def _set_paper_size_and_orientation(paper_size_name: str, orientation: str) -> Tuple[float, float]:
    """Sets the paper size and orientation."""
    dimensions = getattr(reportlab.lib.pagesizes, paper_size_name.upper(), None)
    if dimensions is None:
        print(f"Error: Invalid paper size '{paper_size_name}'. See "
              "https://hg.reportlab.com/hg-public/reportlab/file/tip/src/reportlab/lib/pagesizes.py")
        sys.exit(1)

    if orientation.lower() == "landscape":
        page_width, page_height = dimensions[1], dimensions[0]
    elif orientation.lower() == "portrait":
        page_width, page_height = dimensions
    else:
        print("Error: Orientation must be 'portrait' or 'landscape'.")
        sys.exit(1)

    return page_width, page_height


def _draw_images_and_cut_marks(c: canvas.Canvas, img: Image.Image, image_positions: List[Tuple[float, float]],
                               scaled_width: float, scaled_height: float, cut_marks: bool,
                               imposition_mark_length: float):
    """Draws the images and cut marks on the canvas."""
    for x, y in image_positions:
        c.drawImage(ImageReader(img), x, y, width=scaled_width, height=scaled_height, mask='auto')
        if cut_marks:
            _draw_cut_marks(c, x, y, scaled_width, scaled_height, mark_length=imposition_mark_length * mm)


def create_imposition_pdf(input_image: Image.Image, output_pdf_path: str, paper_size_name: str, orientation: str,
                          num_copies: int, cut_marks: bool, margin: float, spacing: float,
                          imposition_mark_length: float):
    """Creates the imposition PDF. [Imposition]"""
    if input_image is None:
        return

    image_width_mm, image_height_mm = _get_image_dimensions(input_image)

    page_width, page_height = _set_paper_size_and_orientation(paper_size_name, orientation)
    c = canvas.Canvas(output_pdf_path, pagesize=(page_width, page_height))

    cols, rows, scaled_width, scaled_height, image_positions = _calculate_layout(
        image_width_mm, image_height_mm, page_width, page_height, num_copies, margin, spacing
    )

    _draw_images_and_cut_marks(c, input_image, image_positions, scaled_width, scaled_height, cut_marks,
                               imposition_mark_length)
    c.save()


# --- Combined Script Logic ---

def main():
    parser = argparse.ArgumentParser(description="Add bleed, crop marks, and create an imposition PDF.",
                                     formatter_class=argparse.RawTextHelpFormatter)  # Keep line breaks
    parser.add_argument("input_image", nargs='?', help="Path to the input image file.")  # Optional now
    parser.add_argument("output_pdf", nargs='?', help="Path to the output PDF file.")  # Optional now
    parser.add_argument("-c", "--config", default="layout.ini",
                        help="Path to the configuration file (default: config.ini).")
    parser.add_argument("--generate-config", action="store_true",
                        help="Generate a default configuration file and exit.")

    args = parser.parse_args()

    if args.generate_config:
        default_config = generate_default_config()
        write_config_to_file(default_config)
        print("Default configuration file generated: layout.ini")
        sys.exit(0)

    # Check if input and output are provided if not generating config
    if not args.input_image or not args.output_pdf:
        parser.error("input_image and output_pdf are required unless --generate-config is used.")

    config = load_config(args.config)

    # Bleed settings
    bleed_size = config.getint('Bleed', 'bleed_size')
    crop_mark_length = config.getint('Bleed', 'crop_mark_length')
    crop_mark_color = config.get('Bleed', 'crop_mark_color')
    bleed_mode = config.get('Bleed', 'bleed_mode')
    cut_mark_length = config.getint('Bleed', 'cut_mark_length')

    # Imposition settings
    paper_size_name = config.get('Imposition', 'paper_size')
    orientation = config.get('Imposition', 'orientation')
    num_copies = config.getint('Imposition', 'num_copies')
    cut_marks = config.getboolean('Imposition', 'cut_marks')
    margin = config.getfloat('Imposition', 'margin') * mm
    spacing = config.getfloat('Imposition', 'spacing') * mm
    imposition_mark_length = config.getfloat('Imposition', 'imposition_mark_length')

    if bleed_size > 0:
        processed_image = add_bleed_and_marks(args.input_image, bleed_size, crop_mark_length,
                                              crop_mark_color, bleed_mode, cut_mark_length)
        if processed_image is None:
            print("Failed to add bleed and marks. Exiting.")
            sys.exit(1)
    else:
        processed_image = _open_image(args.input_image)[0]  # Get only the image part

    create_imposition_pdf(processed_image, args.output_pdf, paper_size_name, orientation,
                          num_copies, cut_marks, margin, spacing, imposition_mark_length)
    print(f"PDF created successfully: {args.output_pdf}")


if __name__ == "__main__":
    main()
