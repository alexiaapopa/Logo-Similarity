import os
from PIL import Image
import imagehash
from tqdm import tqdm
import shutil

INPUT_LOGOS_DIR = "downloaded_logos"
OUTPUT_CLUSTERS_DIR = "clustered_logos_non_ml" 

HASH_SIZE = 8 
HASH_ALGORITHM = imagehash.phash 

MAX_HASH_DISTANCE = 8 

# Create output directories if they don't exist
os.makedirs(OUTPUT_CLUSTERS_DIR, exist_ok=True)

# --- Main Logic for Non-ML Grouping ---

if __name__ == "__main__":
    print(f"Starting non-ML logo grouping from '{INPUT_LOGOS_DIR}' using perceptual hashing...")
    clusters = [] 
    
    # Collect all image files
    image_files = [
        f for f in os.listdir(INPUT_LOGOS_DIR) 
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico')) 
    ]

    if not image_files:
        print(f"No image files found in '{INPUT_LOGOS_DIR}'. Exiting.")
        exit()

    processed_count = 0
    skipped_count = 0

    image_hashes = []
    for filename in tqdm(image_files, desc="Calculating Hashes"):
        filepath = os.path.join(INPUT_LOGOS_DIR, filename)
        try:
            img = Image.open(filepath).convert('RGB') 
            current_hash = HASH_ALGORITHM(img, hash_size=HASH_SIZE)
            image_hashes.append((filepath, current_hash))
            processed_count += 1
        except (IOError, SyntaxError, OSError) as e:
            # print(f"  [ERROR] Could not process image '{filename}': {e}. Skipping.")
            skipped_count += 1
            continue
        except Exception as e:
            # print(f"  [CRITICAL] An unexpected error occurred for '{filename}': {e}. Skipping.")
            skipped_count += 1
            continue

    print(f"Finished calculating hashes for {processed_count} logos. Skipped {skipped_count} invalid files.")
    print(f"Starting grouping based on MAX_HASH_DISTANCE = {MAX_HASH_DISTANCE}...")

    for filepath, current_hash in tqdm(image_hashes, desc="Grouping Logos"):
        assigned_to_existing_cluster = False
        
        for cluster_id, cluster_info in enumerate(clusters):
            
            representative_hash = cluster_info['representative_hash']
            hash_distance = current_hash - representative_hash 
            
            if hash_distance <= MAX_HASH_DISTANCE:
                clusters[cluster_id]['filepaths'].append(filepath)
                assigned_to_existing_cluster = True
                break
        
        if not assigned_to_existing_cluster:
            clusters.append({
                'representative_hash': current_hash, 
                'filepaths': [filepath]
            })

    print(f"Found {len(clusters)} unique logo groups.")

    moved_count = 0
    for i, cluster_info in enumerate(tqdm(clusters, desc="Moving Clustered Logos")):
        cluster_dir = os.path.join(OUTPUT_CLUSTERS_DIR, f"cluster_{i+1}") 
        os.makedirs(cluster_dir, exist_ok=True)
        
        for filepath in cluster_info['filepaths']:
            filename = os.path.basename(filepath)
            dest_path = os.path.join(cluster_dir, filename)
            try:
                shutil.copy(filepath, dest_path) 
                moved_count += 1
            except Exception as e:
                print(f"  [ERROR] Could not copy '{filepath}' to '{dest_path}': {e}")
    
    print(f"\n--- Non-ML Logo Grouping Summary ---")
    print(f"Total logos processed for hashing: {processed_count}")
    print(f"Total invalid/skipped files: {skipped_count}")
    print(f"Total unique logo groups created: {len(clusters)}")
    print(f"Total logos copied to clusters: {moved_count}")
    print(f"Clustered logos are in '{OUTPUT_CLUSTERS_DIR}'")
    print("\nNote: This script *copies* logos to the cluster directories, original files remain in 'downloaded_logos'.")
    print(f"Adjust 'MAX_HASH_DISTANCE' in the script to control similarity threshold.")