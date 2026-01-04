import shutil
import os
from pathlib import Path
import datetime

def package_agent():
    base_dir = Path(__file__).parent.parent.resolve()
    dist_dir = base_dir / "dist"
    version = datetime.datetime.now().strftime("%Y%m%d")
    archive_name = dist_dir / f"unified-ipsec-agent-{version}"
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    
    # Files to include
    includes = [
        "agent",
        "scripts",
        "config.json",
        "README.md",
        "requirements.txt" # if exists, or create one
    ]
    
    # Create temp dir for zip structure
    temp_dir = dist_dir / "temp"
    temp_dir.mkdir()
    
    for item in includes:
        src = base_dir / item
        dst = temp_dir / item
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "output", "dist"))
        elif src.exists():
            shutil.copy2(src, dst)
            
    # Create Zip
    shutil.make_archive(str(archive_name), 'zip', temp_dir)
    
    # Cleanup temp
    shutil.rmtree(temp_dir)
    
    print(f"Package created at: {archive_name}.zip")

if __name__ == "__main__":
    package_agent()
