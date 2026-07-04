import os
import shutil
from pathlib import Path
import re

def main():
    root = Path(r"c:\Users\ADMIN\OneDrive\Documents\MiningMassiveData\Whess-AI-Server")
    src = root / "src"
    old_ai = src / "ai_engine"
    
    # 1. Create backup
    backup = src / "ai_engine_backup"
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(old_ai, backup)
    print("Backup created at:", backup)

    # 2. Define new structure
    new_ai = src / "ai_engine_new"
    if new_ai.exists():
        shutil.rmtree(new_ai)
    
    dirs = [
        "api",
        "core",
        "domain",
        "ai_agents",
        "ai_agents/prompts",
        "inference",
        "services",
        "services/eco_data",
        "utils"
    ]
    for d in dirs:
        (new_ai / d).mkdir(parents=True, exist_ok=True)
        
    # 3. File mapping (old -> new)
    file_map = {
        "api_models.py": "api/dtos.py",
        "server.py": "api/routers.py",
        "main.py": "main.py",
        "config.py": "core/config.py",
        "errors.py": "core/errors.py",
        "full_pipeline.py": "core/full_pipeline.py",
        "schemas.py": "domain/schemas.py",
        "pipeline.py": "ai_agents/orchestrator.py",
        "agents/data_miner.py": "ai_agents/data_miner.py",
        "agents/tactician.py": "ai_agents/tactician.py",
        "agents/head_coach.py": "ai_agents/head_coach.py",
        "predictor.py": "inference/elo_predictor.py",
        "stockfish_analyzer.py": "services/stockfish.py",
        "llm/client.py": "services/llm_client.py",
        "llm/json_utils.py": "utils/json_utils.py",
        "services/opening_book.py": "services/opening_book.py",
        "eco_data/eco.json": "services/eco_data/eco.json",
    }
    
    # Copy files to new locations
    for old_rel, new_rel in file_map.items():
        old_file = old_ai / old_rel
        new_file = new_ai / new_rel
        if old_file.exists():
            shutil.copy2(old_file, new_file)
            
    # 4. Import Renaming Map
    import_replacements = [
        ("src.ai_engine.api_models", "src.ai_engine.api.dtos"),
        ("src.ai_engine.server", "src.ai_engine.api.routers"),
        ("src.ai_engine.config", "src.ai_engine.core.config"),
        ("src.ai_engine.errors", "src.ai_engine.core.errors"),
        ("src.ai_engine.full_pipeline", "src.ai_engine.core.full_pipeline"),
        ("src.ai_engine.schemas", "src.ai_engine.domain.schemas"),
        ("src.ai_engine.pipeline", "src.ai_engine.ai_agents.orchestrator"),
        ("src.ai_engine.agents.data_miner", "src.ai_engine.ai_agents.data_miner"),
        ("src.ai_engine.agents.tactician", "src.ai_engine.ai_agents.tactician"),
        ("src.ai_engine.agents.head_coach", "src.ai_engine.ai_agents.head_coach"),
        ("src.ai_engine.predictor", "src.ai_engine.inference.elo_predictor"),
        ("src.ai_engine.stockfish_analyzer", "src.ai_engine.services.stockfish"),
        ("src.ai_engine.llm.client", "src.ai_engine.services.llm_client"),
        ("src.ai_engine.llm.json_utils", "src.ai_engine.utils.json_utils"),
        ("src.ai_engine.services.opening_book", "src.ai_engine.services.opening_book"),
        ("src.ai_engine.eco_data.eco", "src.ai_engine.services.eco_data.eco")
    ]
    
    # Process files
    for filepath in new_ai.rglob("*.py"):
        content = filepath.read_text(encoding="utf-8")
        
        # Replace imports
        for old_imp, new_imp in import_replacements:
            content = content.replace(old_imp, new_imp)
            
        # Specific fixes for eco_data path in opening_book.py
        if filepath.name == "opening_book.py":
            content = content.replace('eco_data/eco.json', 'services/eco_data/eco.json')
            
        # Extract prompts in tactician and head_coach
        if filepath.name == "tactician.py":
            prompt_match = re.search(r'SYSTEM_PROMPT\s*=\s*\"\"\"(.*?)\"\"\"\.strip\(\)', content, re.DOTALL)
            if prompt_match:
                prompt_text = prompt_match.group(1).strip()
                prompt_file = new_ai / "ai_agents" / "prompts" / "tactician.txt"
                prompt_file.write_text(prompt_text, encoding="utf-8")
                
                content = re.sub(r'SYSTEM_PROMPT\s*=\s*\"\"\"(.*?)\"\"\"\.strip\(\)', 
                                 'import os\nfrom pathlib import Path\n'
                                 'PROMPT_PATH = Path(__file__).parent / "prompts" / "tactician.txt"\n'
                                 'SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()', 
                                 content, flags=re.DOTALL)
                                 
        if filepath.name == "head_coach.py":
            prompt_match = re.search(r'SYSTEM_PROMPT\s*=\s*\"\"\"(.*?)\"\"\"\.strip\(\)', content, re.DOTALL)
            if prompt_match:
                prompt_text = prompt_match.group(1).strip()
                prompt_file = new_ai / "ai_agents" / "prompts" / "head_coach.txt"
                prompt_file.write_text(prompt_text, encoding="utf-8")
                
                content = re.sub(r'SYSTEM_PROMPT\s*=\s*\"\"\"(.*?)\"\"\"\.strip\(\)', 
                                 'import os\nfrom pathlib import Path\n'
                                 'PROMPT_PATH = Path(__file__).parent / "prompts" / "head_coach.txt"\n'
                                 'SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()', 
                                 content, flags=re.DOTALL)
                                 
        filepath.write_text(content, encoding="utf-8")
        
    # Replace old folder with new
    try:
        shutil.rmtree(old_ai)
        new_ai.rename(old_ai)
        print("Refactoring completed successfully!")
    except Exception as e:
        print(f"Error swapping folders: {e}")

if __name__ == "__main__":
    main()
