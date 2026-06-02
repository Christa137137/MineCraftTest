import os
import shutil

def sync_json_files(source_dir, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".json"):
                source_path = os.path.join(root, file)
                target_path = os.path.join(target_dir, file)
                
                if os.path.exists(target_path):
                    base, extension = os.path.splitext(file)
                    i = 1
                    while os.path.exists(os.path.join(target_dir, f"{base}_{i}{extension}")):
                        i += 1
                    target_path = os.path.join(target_dir, f"{base}_{i}{extension}")
                
                shutil.copy2(source_path, target_path)


def sample_subdirs(source_dir, target_dir, max_per_subdir=2):

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for subdir in os.listdir(source_dir):
        subdir_path = os.path.join(source_dir, subdir)
        
        if os.path.isdir(subdir_path):

            files = sorted([f for f in os.listdir(subdir_path) if os.path.isfile(os.path.join(subdir_path, f))])
 
            files_to_copy = files[:max_per_subdir]
            
            for file in files_to_copy:
                source_path = os.path.join(subdir_path, file)
                
                target_path = os.path.join(target_dir, file)
                if os.path.exists(target_path):
                    base, extension = os.path.splitext(file)
                    i = 1
                    while os.path.exists(os.path.join(target_dir, f"{base}_{i}{extension}")):
                        i += 1
                    target_path = os.path.join(target_dir, f"{base}_{i}{extension}")
                
                shutil.copy2(source_path, target_path)
                # print(f"[Sample] Copied: {subdir}/{file} -> {os.path.basename(target_path)}")

if __name__ == "__main__":
    # sync_json_files("outputs\inconsistent_seeds\watertest", "outputs/temp/generation")
    sample_subdirs("outputs\inconsistent_seeds\waterrandomtest", "outputs/temp/generation", max_per_subdir=1)