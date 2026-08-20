"""Réduit les photos originales de photos_local/ vers gallery/ (versions légères à committer).

Usage : python3 shrink.py

- Lit   : photos_local/photos_*/  (originaux, ignorés par git — jamais modifiés)
- Écrit : gallery/photos_*/       (réduites 2048px, qualité 82 — à committer)

L'EXIF est conservé (date de prise de vue + infos appareil) pour que build.py
puisse trier les photos par date et afficher les infos de prise de vue.
"""
import os
import glob
from PIL import Image

SOURCE = "photos_local"
OUTPUT = "gallery"
MAX_SIZE = (2048, 2048)
QUALITY = 82

# Extensions d'images acceptées (on ignore .DS_Store, .gitkeep, etc.)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}


def main():
    if not os.path.isdir(SOURCE):
        raise SystemExit(f"ERREUR : dossier '{SOURCE}' introuvable.")

    os.makedirs(OUTPUT, exist_ok=True)

    subdirs = sorted(
        d for d in os.listdir(SOURCE)
        if os.path.isdir(os.path.join(SOURCE, d)) and d.startswith("photos_")
    )
    if not subdirs:
        raise SystemExit(f"Aucun sous-dossier photos_* trouvé dans {SOURCE}/")

    total = 0
    for d in subdirs:
        src_dir = os.path.join(SOURCE, d)
        dst_dir = os.path.join(OUTPUT, d)
        os.makedirs(dst_dir, exist_ok=True)

        done = skipped = 0
        for path in sorted(glob.glob(os.path.join(src_dir, "*"))):
            ext = os.path.splitext(path)[1].lower()
            if ext not in IMAGE_EXTS:
                skipped += 1
                continue

            name = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(dst_dir, name + ".jpg")

            try:
                with Image.open(path) as img:
                    exif_bytes = img.info.get("exif")  # EXIF brut conservé tel quel
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
                    if exif_bytes:
                        img.save(out_path, "JPEG", optimize=True, quality=QUALITY, exif=exif_bytes)
                    else:
                        img.save(out_path, "JPEG", optimize=True, quality=QUALITY)
                done += 1
            except Exception as e:
                skipped += 1
                print(f"  [ignorée] {os.path.basename(path)} : {e}")

        total += done
        print(f"{d}: {done} réduite(s), {skipped} ignorée(s)")

    print(f"\nTerminé — {total} photos dans '{OUTPUT}/'.")


if __name__ == "__main__":
    main()
