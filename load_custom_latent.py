import os
import hashlib
import safetensors.torch
import json

# ------------------------------
# Pfade
# ------------------------------
NODE_DIR = os.path.dirname(os.path.abspath(__file__))          # .../custom_nodes/load_latent_node
COMFYUI_ROOT = os.path.dirname(os.path.dirname(NODE_DIR))      # zwei Ebenen hoch -> ComfyUI/
LATENT_OUTPUT_DIR = os.path.join(COMFYUI_ROOT, "output")       # ComfyUI/output

# JSON-Dateien für gespeicherte Liste und letztes Selection
LATENTS_LIST_FILE = os.path.join(NODE_DIR, ".latents_list.json")
LAST_SELECTED_FILE = os.path.join(NODE_DIR, ".last_selected_latent.json")

# ------------------------------
# Hilfsfunktionen
# ------------------------------
def update_latents_list():
    latents = []
    for root, dirs, files in os.walk(LATENT_OUTPUT_DIR):
        for f in files:
            if f.endswith(".latent"):
                rel_path = os.path.relpath(os.path.join(root, f), LATENT_OUTPUT_DIR)
                latents.append(rel_path)
    with open(LATENTS_LIST_FILE, "w") as f:
        json.dump(latents, f)
    return latents

def get_latents_list():
    if os.path.exists(LATENTS_LIST_FILE):
        try:
            with open(LATENTS_LIST_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return update_latents_list()

def get_last_selected():
    if os.path.exists(LAST_SELECTED_FILE):
        try:
            with open(LAST_SELECTED_FILE, "r") as f:
                data = json.load(f)
                return data.get("last", "")
        except Exception:
            pass
    return ""

def save_last_selected(latent_file):
    try:
        with open(LAST_SELECTED_FILE, "w") as f:
            json.dump({"last": latent_file}, f)
    except Exception:
        pass

# ------------------------------
# Node
# ------------------------------
class LoadCustomLatent:
    """
    Load a latent tensor from ComfyUI/output (including subfolders)
    using a textfield with auto-default selection.
    """
    @classmethod
    def INPUT_TYPES(cls):
        latents = get_latents_list()
        default_value = get_last_selected() or (latents[0] if latents else "")
        return {
            "required": {
                "latent_file": ("STRING", {
                    "default": default_value,
                    "choices": latents,   # Autocomplete in ComfyUI Textfeld
                    "label": "Select latent file"
                }),
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "load_custom_latent_file"
    CATEGORY = "latent/io"
    DESCRIPTION = "Loads a latent tensor from ComfyUI/output (including subfolders)."
    SEARCH_ALIASES = ["load latent", "latent loader", "load latent file"]

    def load_custom_latent_file(self, latent_file):
        path = os.path.join(LATENT_OUTPUT_DIR, latent_file)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Latent file not found: {path}")

        save_last_selected(latent_file)

        latent = safetensors.torch.load_file(path, device="cpu")

        multiplier = 1.0
        if "latent_format_version_0" not in latent:
            multiplier = 1.0 / 0.18215

        return ({"samples": latent["latent_tensor"].float() * multiplier},)

    @classmethod
    def IS_CHANGED(cls, latent_file):
        path = os.path.join(LATENT_OUTPUT_DIR, latent_file)
        if not os.path.exists(path):
            return ""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()

    @classmethod
    def VALIDATE_INPUTS(cls, latent_file):
        path = os.path.join(LATENT_OUTPUT_DIR, latent_file)
        if not os.path.exists(path):
            return f"Invalid latent file: {path}"
        return True
