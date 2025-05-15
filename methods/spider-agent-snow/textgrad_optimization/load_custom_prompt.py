#!/usr/bin/env python

import os
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

def patch_prompts():
    custom_prompt_path = os.environ.get("SPIDER_SNOW_PROMPT_PATH")
    
    if custom_prompt_path and os.path.exists(custom_prompt_path):
        print(f"Loading custom prompt from {custom_prompt_path}")
        
        globals_dict = {}
        with open(custom_prompt_path, 'r') as f:
            exec(f.read(), globals_dict)
        
        from spider_agent.agent import prompts
        
        if "SNOWFLAKE_SYSTEM" in globals_dict:
            print("Patching SNOWFLAKE_SYSTEM prompt")
            prompts.SNOWFLAKE_SYSTEM = globals_dict["SNOWFLAKE_SYSTEM"]
        
        return True
    
    return False

if __name__ == "__main__":
    patched = patch_prompts()
    if patched:
        print("Successfully patched prompts")
    else:
        print("No custom prompts to patch")