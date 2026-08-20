import os
import glob
from PIL import Image, ImageOps
from datetime import datetime

os.makedirs("public/photos", exist_ok=True)

# --- Configuration ---
MAX_SIZE = (1920, 1920)
QUALITY = 80 
PHOTOS_PER_PAGE = 20 

# Dossier source des photos réduites (généré par `python3 shrink.py` depuis photos_local/)
SOURCE_DIR = "gallery"
# Extensions d'images acceptées (on ignore .DS_Store, .gitkeep, etc.)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}

def get_exif_date(img_path):
    try:
        with Image.open(img_path) as img:
            exif = img.getexif()
            # DateTimeOriginal (36867) peut être dans l'IFD principal OU le sous-IFD Exif
            dt = exif.get(36867)
            if not dt:
                dt = exif.get_ifd(34665).get(36867)
            if dt:
                return datetime.strptime(str(dt), '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(img_path))

def get_exif_str(img):
    try:
        exif = img.getexif()
        if not exif: return ""
        model = str(exif.get(272, "")).strip()
        ifd = exif.get_ifd(34665) 
        focal, aperture, iso = "", "", ""
        if ifd.get(37386): focal = f"{int(float(ifd.get(37386)))}mm"
        if ifd.get(33437): aperture = f"f/{float(ifd.get(33437)):.1f}"
        if ifd.get(34855): iso = f"ISO {ifd.get(34855)}"
        parts = [p for p in [model, focal, aperture, iso] if p]
        return " • ".join(parts)
    except Exception:
        return ""

# 1. Détecter les dossiers de lieux dans SOURCE_DIR (ex: gallery/photos_tokyo, gallery/photos_osaka)
if not os.path.isdir(SOURCE_DIR):
    raise SystemExit(f"ERREUR : dossier '{SOURCE_DIR}' introuvable. Lancez d'abord `python3 shrink.py` puis committez gallery/.")

all_dirs = [d for d in os.listdir(SOURCE_DIR)
            if os.path.isdir(os.path.join(SOURCE_DIR, d)) and d.startswith('photos_')]
all_dirs = sorted(all_dirs)  # Tri alphabétique des dossiers

categories = []
for d in all_dirs:
    if d == 'photos':
        cat_id = 'galerie'
        cat_name = 'Galerie'
    else:
        cat_id = d.split('photos_')[1]
        cat_name = cat_id.replace('_', ' ').capitalize()
    categories.append({'dir': os.path.join(SOURCE_DIR, d), 'id': cat_id, 'name': cat_name})

with open("template.html", "r") as f:
    template_html = f.read()

# Fonction pour obtenir le nom de fichier d'une page spécifique
def get_page_filename(cat_id, page_num, is_first_cat):
    if page_num == 1:
        return "index.html" if is_first_cat else f"{cat_id}.html"
    return f"{cat_id}-page-{page_num}.html"

# 2. Générer les pages pour chaque catégorie
for cat_idx, cat in enumerate(categories):
    is_first_cat = (cat_idx == 0)
    image_paths = [p for p in glob.glob(os.path.join(cat['dir'], "*"))
                   if os.path.splitext(p)[1].lower() in IMAGE_EXTS]
    images = sorted(image_paths, key=get_exif_date, reverse=True)
    
    chunks = [images[i:i + PHOTOS_PER_PAGE] for i in range(0, len(images), PHOTOS_PER_PAGE)]
    if not chunks:
        chunks = [[]]
        
    total_pages = len(chunks)
    
    for page_idx, chunk in enumerate(chunks):
        current_page = page_idx + 1
        html_tags = []
        
        # Traitement des images du paquet courant
        for img_path in chunk:
            filename = os.path.basename(img_path)
            name_only = os.path.splitext(filename)[0]
            # On ajoute l'id de la catégorie pour éviter les conflits de noms de fichiers identiques entre dossiers
            out_filename = f"{cat['id']}_{name_only}.jpg"
            out_path = os.path.join("public/photos", out_filename)
            
            with Image.open(img_path) as img:
                exif_str = get_exif_str(img)
                img_corrected = ImageOps.exif_transpose(img)
                if img_corrected.mode in ("RGBA", "P"):
                    img_corrected = img_corrected.convert("RGB")
                img_corrected.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
                img_corrected.save(out_path, format="JPEG", optimize=True, quality=QUALITY)

            exif_html = f'<div class="exif-data">{exif_str}</div>' if exif_str else ''
            card_html = f"""
            <div class="photo-card">
                <img src="photos/{out_filename}" loading="lazy" alt="Photo">
                {exif_html}
            </div>
            """
            html_tags.append(card_html)

        # --- Construction des Onglets (Tabs) ---
        tabs_elements = []
        for c_idx, c in enumerate(categories):
            c_is_first = (c_idx == 0)
            target_url = "index.html" if c_is_first else f"{c['id']}.html"
            active_tab_class = " active" if c['id'] == cat['id'] else ""
            tabs_elements.append(f'<a href="{target_url}" class="tab-link{active_tab_class}">{c["name"]}</a>')
        tabs_html = "\n".join(tabs_elements)

        # --- Construction de la pagination intelligente ---
        pagination_elements = []
        
        if current_page > 1:
            prev_url = get_page_filename(cat['id'], current_page - 1, is_first_cat)
            pagination_elements.append(f'<a href="{prev_url}" class="page-btn">←</a>')
            
        delta = 1
        pages_to_show = set([1, total_pages])
        for i in range(max(1, current_page - delta), min(total_pages, current_page + delta) + 1):
            pages_to_show.add(i)
            
        pages_to_show = sorted(list(pages_to_show))
        
        for idx, p in enumerate(pages_to_show):
            if idx > 0 and p - pages_to_show[idx-1] > 1:
                pagination_elements.append('<span class="ellipsis">...</span>')
                
            page_url = get_page_filename(cat['id'], p, is_first_cat)
            active_page_class = " active" if p == current_page else ""
            pagination_elements.append(f'<a href="{page_url}" class="page-link{active_page_class}">{p}</a>')
            
        if current_page < total_pages:
            next_url = get_page_filename(cat['id'], current_page + 1, is_first_cat)
            pagination_elements.append(f'<a href="{next_url}" class="page-btn">→</a>')

        pagination_html = " ".join(pagination_elements) if total_pages > 1 else ''

        # --- Remplacement final ---
        page_html = template_html.replace("<!-- TABS_CONTENT -->", tabs_html)
        page_html = page_html.replace("<!-- GALLERY_CONTENT -->", "\n".join(html_tags))
        page_html = page_html.replace("<!-- PAGINATION_CONTENT -->", pagination_html)

        out_file = get_page_filename(cat['id'], current_page, is_first_cat)
        with open(os.path.join("public", out_file), "w") as f:
            f.write(page_html)

print(f"Génération par lieux terminée pour {len(categories)} catégorie(s).")
