from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ANDROID_RES = ROOT / "android" / "app" / "src" / "main" / "res"
SOURCE = Image.open(ROOT / "public" / "brand" / "loading-icon.png").convert("RGBA")
alpha = SOURCE.getchannel("A")
bounds = alpha.point(lambda value: 255 if value > 12 else 0).getbbox()
MARK = SOURCE.crop(bounds)
BACKGROUND = (248, 250, 247, 255)

SIZES = {
    "drawable": (480, 320),
    "drawable-land-mdpi": (480, 320),
    "drawable-land-hdpi": (800, 480),
    "drawable-land-xhdpi": (1280, 720),
    "drawable-land-xxhdpi": (1600, 960),
    "drawable-land-xxxhdpi": (1920, 1280),
    "drawable-port-mdpi": (320, 480),
    "drawable-port-hdpi": (480, 800),
    "drawable-port-xhdpi": (720, 1280),
    "drawable-port-xxhdpi": (960, 1600),
    "drawable-port-xxxhdpi": (1280, 1920),
}

for folder, size in SIZES.items():
    width, height = size
    canvas = Image.new("RGBA", size, BACKGROUND)
    max_edge = int(min(size) * 0.40)
    scale = min(max_edge / MARK.width, max_edge / MARK.height)
    mark = MARK.resize((round(MARK.width * scale), round(MARK.height * scale)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(mark, ((width - mark.width) // 2, (height - mark.height) // 2))
    canvas.convert("RGB").save(ANDROID_RES / folder / "splash.png", optimize=True)
