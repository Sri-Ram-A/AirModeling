from pathlib import Path
from tqdm import tqdm

ROOT_DIR = Path(__name__).resolve().parent
DATASET_DIR = ROOT_DIR / "backend" / "data"

folder_path = DATASET_DIR / "raw" / "2025"

folder = Path(folder_path)
generator = folder.glob("*.csv")
for file in tqdm(generator, desc="Processing files"):
    old_name = file.name
    # Remove unwanted parts
    new_name = old_name.replace("Raw_data_15Min_2025_", "")
    new_name = new_name.replace("_15Min", "")
    new_name = new_name.replace("_Bengaluru", "")
    new_path = file.with_name(new_name)
    # Rename file
    file.rename(new_path)
