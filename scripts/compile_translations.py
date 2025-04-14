import os
import subprocess
from pathlib import Path

# Define base directory
BASE_DIR = Path(__file__).parent.parent
LOCALE_DIR = BASE_DIR / "app" / "i18n" / "locales"

def compile_all_translations():
    """Compile .po files into .mo files for all languages"""
    print("Compiling translations...")
    
    for lang_dir in LOCALE_DIR.iterdir():
        if lang_dir.is_dir():
            lang_code = lang_dir.name
            po_file = lang_dir / "LC_MESSAGES" / "messages.po"
            
            if po_file.exists():
                print(f"Compiling {lang_code} translations...")
                try:
                    subprocess.run([
                        "pybabel", "compile",
                        "-f", "-i", str(po_file),
                        "-o", str(po_file.parent / "messages.mo"),
                        "--statistics"
                    ], check=True)
                    print(f"Successfully compiled {lang_code} translations")
                except subprocess.CalledProcessError as e:
                    print(f"Error compiling {lang_code} translations: {e}")
            else:
                print(f"No .po file found for {lang_code}")

def update_pot_file():
    """Extract translatable strings from templates and create a POT file"""
    print("Extracting strings from templates...")
    
    pot_file = BASE_DIR / "app" / "i18n" / "messages.pot"
    template_dir = BASE_DIR / "app" / "templates"
    
    try:
        subprocess.run([
            "pybabel", "extract",
            "-F", str(BASE_DIR / "babel.cfg"),
            "-o", str(pot_file),
            str(template_dir)
        ], check=True)
        print("Successfully created template file")
    except subprocess.CalledProcessError as e:
        print(f"Error creating template file: {e}")

def update_po_files():
    """Update all .po files with the strings from the POT file"""
    print("Updating .po files...")
    
    pot_file = BASE_DIR / "app" / "i18n" / "messages.pot"
    
    for lang_dir in LOCALE_DIR.iterdir():
        if lang_dir.is_dir():
            lang_code = lang_dir.name
            po_file = lang_dir / "LC_MESSAGES" / "messages.po"
            
            if po_file.exists():
                print(f"Updating {lang_code} translations...")
                try:
                    subprocess.run([
                        "pybabel", "update",
                        "-i", str(pot_file),
                        "-o", str(po_file),
                        "-l", lang_code
                    ], check=True)
                    print(f"Successfully updated {lang_code} translations")
                except subprocess.CalledProcessError as e:
                    print(f"Error updating {lang_code} translations: {e}")
            else:
                print(f"Initializing {lang_code} translations...")
                # Create LC_MESSAGES directory if it doesn't exist
                os.makedirs(lang_dir / "LC_MESSAGES", exist_ok=True)
                try:
                    subprocess.run([
                        "pybabel", "init",
                        "-i", str(pot_file),
                        "-o", str(po_file),
                        "-l", lang_code
                    ], check=True)
                    print(f"Successfully initialized {lang_code} translations")
                except subprocess.CalledProcessError as e:
                    print(f"Error initializing {lang_code} translations: {e}")

if __name__ == "__main__":
    # Create babel.cfg if it doesn't exist
    babel_cfg = BASE_DIR / "babel.cfg"
    if not babel_cfg.exists():
        with open(babel_cfg, "w") as f:
            f.write("[python: **.py]\n")
            f.write("[jinja2: **/templates/**.html]\n")
            f.write("extensions=jinja2.ext.autoescape,jinja2.ext.with_\n")
    
    update_pot_file()
    update_po_files()
    compile_all_translations()
