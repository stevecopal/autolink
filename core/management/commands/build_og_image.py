# core/management/commands/build_og_image.py
"""Génère l'image OpenGraph par défaut (1200x630) utilisée par og:image."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image

OG_SIZE = (1200, 630)
#: #000080 — couleur de marque (theme-color de l'application).
BACKGROUND = (0, 0, 128)


class Command(BaseCommand):
    help = "Génère static/og-image.jpg (1200x630) à partir du logo AutoLink."

    def handle(self, *args, **options):
        source = Path(settings.BASE_DIR) / "static" / "logo.jpg"
        target = Path(settings.BASE_DIR) / "static" / "og-image.jpg"

        if not source.exists():
            raise FileNotFoundError(f"Logo introuvable : {source}")

        canvas = Image.new("RGB", OG_SIZE, BACKGROUND)
        logo = Image.open(source).convert("RGBA")
        logo.thumbnail((520, 520), Image.Resampling.LANCZOS)

        position = (
            (OG_SIZE[0] - logo.width) // 2,
            (OG_SIZE[1] - logo.height) // 2,
        )
        canvas.paste(logo, position, logo)
        canvas.save(target, "JPEG", quality=88, optimize=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"{target} généré — {OG_SIZE[0]}x{OG_SIZE[1]}, "
                f"{target.stat().st_size // 1024} Ko"
            )
        )