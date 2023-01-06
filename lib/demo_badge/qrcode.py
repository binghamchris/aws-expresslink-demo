import displayio
import adafruit_miniqr

def bitmap_qr(matrix: adafruit_miniqr.QRBitMatrix) -> displayio.Bitmap:
    border_pixels = 2
    bitmap = displayio.Bitmap(
        matrix.width + 2 * border_pixels,
        matrix.height + 2 * border_pixels,
        2,
    )
    for y in range(matrix.height):
        for x in range(matrix.width):
            if matrix[x, y]:
                bitmap[x + border_pixels, y + border_pixels] = 1
            else:
                bitmap[x + border_pixels, y + border_pixels] = 0
    return bitmap

def encode_qr_code(display, data: str, qr_type=6, error_correct=adafruit_miniqr.L) -> displayio.Group:
    qr_code = adafruit_miniqr.QRCode(qr_type=qr_type, error_correct=error_correct)
    qr_code.add_data(data.encode())
    qr_code.make()

    # black and white
    palette = displayio.Palette(2)
    palette[0] = 0xFFFFFF
    palette[1] = 0x000000

    # full-screen centered size
    bitmap = bitmap_qr(qr_code.matrix)
    scale = min(
        display.width // bitmap.width,
        display.height // bitmap.height,
    )
    x = int(
        ((display.width / scale) - bitmap.width) / 2
    )
    y = int(
        ((display.height / scale) - bitmap.height) / 2
    )

    qr_img = displayio.TileGrid(
        bitmap=bitmap,
        pixel_shader=palette,
        x=x,
        y=y,
    )

    group = displayio.Group(scale=scale)
    group.append(qr_img)
    return group
