#!/usr/bin/env python

import os
import sys
import json
import subprocess
import logging
from typing import List, Dict, Any, Tuple
import textgrad as tg
import numpy as np
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))
from spider_agent.agent.prompts import SNOWFLAKE_SYSTEM

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("textgrad_optimization/snowflake_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

EXAMPLES_PATH = os.path.join(parent_dir, "examples/spider2-snow.jsonl")
TEST_EXAMPLES = 5
MAX_STEPS = 15
MODEL = "gpt-4o"
FEEDBACK_MODEL = "gpt-4o"

tg.set_backward_engine(FEEDBACK_MODEL)

class PromptOptimizer:
    
    def __init__(self, base_prompt: str, num_examples: int = 5):
        self.base_prompt = base_prompt
        self.num_examples = num_examples
        self.examples = self._load_examples()
        
    def _load_examples(self) -> List[Dict[str, Any]]:
        with open(EXAMPLES_PATH, 'r') as f:
            examples = [json.loads(line) for line in f.readlines()]
        
        selected_examples = examples[:self.num_examples]
        logger.info(f"Loaded {len(selected_examples)} examples for evaluation")
        return selected_examples
    
    def _evaluate_prompt(self, prompt_template: str) -> Tuple[float, List[Dict]]:
        temp_prompt_file = os.path.join(parent_dir, "textgrad_optimization/temp_prompt.py")
        with open(temp_prompt_file, 'w') as f:
            f.write(f"""
SNOWFLAKE_SYSTEM = \"\"\"
{prompt_template}
\"\"\"
            """)
        
        results = []
        success_count = 0
        
        for i, example in enumerate(self.examples):
            logger.info(f"Testing example {i+1}/{self.num_examples}: {example['instance_id']}")
            
            cmd = [
                "python", str(os.path.join(parent_dir, "run.py")),
                "--model", MODEL,
                "--example_name", example["instance_id"],
                "--max_steps", str(MAX_STEPS),
                "--suffix", "textgrad-test",
                "--overwriting"
            ]
            
            env = os.environ.copy()
            env["SPIDER_SNOW_PROMPT_PATH"] = temp_prompt_file
            
            try:
                output = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT, text=True)
                
                output_dir = os.path.join(parent_dir, "output", f"{MODEL}-textgrad-test", example["instance_id"])
                result_path = os.path.join(output_dir, "spider/result.json")
                
                if os.path.exists(result_path):
                    with open(result_path, 'r') as f:
                        result_data = json.load(f)
                        
                    success = result_data.get("finished", False) and "error" not in str(result_data.get("result", "")).lower()
                    if success:
                        success_count += 1
                    
                    results.append({
                        "example_id": example["instance_id"],
                        "success": success,
                        "steps": result_data.get("steps", 0),
                        "result": result_data.get("result", "")
                    })
                else:
                    results.append({
                        "example_id": example["instance_id"],
                        "success": False,
                        "error": "No result file found"
                    })
            except subprocess.CalledProcessError as e:
                logger.error(f"Error running test for {example['instance_id']}: {e}")
                results.append({
                    "example_id": example["instance_id"],
                    "success": False,
                    "error": str(e)
                })
        
        score = success_count / self.num_examples if self.num_examples > 0 else 0
        logger.info(f"Evaluation complete. Success rate: {score:.2f} ({success_count}/{self.num_examples})")
        
        if os.path.exists(temp_prompt_file):
            os.unlink(temp_prompt_file)
            
        return score, results

    def optimize_prompt(self) -> str:
        logger.info("Starting prompt optimization with TextGrad")
        
        sections = {
            "query_tips": tg.Variable(
                """
# Snowflake-Query #

1. You are in the /workspace directory. Begin by checking if there are any markdown files in this directory. If found, read them as they may contain useful information for answering your questions.

2. The database schema folder is located in the /workspace directory. This folder contains one or more schema directories for the databases. Each directory includes a DDL.csv file with the database's DDL, along with JSON files that contain the column names, column types, column descriptions, and sample rows for individual tables. Start by reviewing the DDL.csv file in each directory, then selectively examine the JSON files as needed. Read them carefully.

3. Use SNOWFLAKE_EXEC_SQL to run your SQL queries and interact with the database. Do not use this action to query INFORMATION_SCHEMA or SHOW DATABASES/TABLES; the schema information is all stored in the /workspace/database_name folder. Refer to this folder whenever you have doubts about the schema.

4. Be prepared to write multiple SQL queries to find the correct answer. Once it makes sense, consider it resolved.

5. You may receieve from the user an initial SQL query along with the task. This SQL query can be a good starting point but it is likely not completely correct. Use it as a reference, but understand it may be wrong. 

6. Focus on SQL queries rather than frequently using Bash commands like grep and cat, though they can be used when necessary.

7. If you encounter an SQL error, reconsider the database information and your previous queries, then adjust your SQL accordingly. Do not output the same SQL queries repeatedly.

8. Ensure you get valid results, not an empty file. Once the results are stored in result.csv, make sure the file contains data. If it is empty or just contains the table header, it means your SQL query is incorrect.

9. The final result MUST be a CSV file, not an .sql file, a calculation, an idea, a sentence or merely an intermediate step. Save the answer as a CSV and provide the file name, it is usually from the SQL execution result.
""",
                requires_grad=True,
                role_description="Snowflake query guidelines section of the prompt"
            ),
            
            "tips": tg.Variable(
                """
# Tips #

1. When referencing table names in Snowflake SQL, you must include both the database_name and schema_name. For example, for /workspace/DEPS_DEV_V1/DEPS_DEV_V1/ADVISORIES.json, if you want to use it in SQL, you should write DEPS_DEV_V1.DEPS_DEV_V1.ADVISORIES.

2. Do not write SQL queries to retrieve the schema; use the existing schema documents in the folders.

3. When encountering bugs, carefully analyze and think them through; avoid writing repetitive code.

4. Column names must be enclosed in quotes. But don't use \",just use ".
""",
                requires_grad=True,
                role_description="SQL tips section of the prompt"
            )
        }
        
        def format_prompt(query_tips, tips):
            return f"""You are a data scientist proficient in database, SQL and DBT Project.
You are starting in the {{work_dir}} directory, which contains all the data needed for your tasks. 
You can only use the actions provided in the ACTION SPACE to solve the task. 
For each step, you must output an Action; it cannot be empty. The maximum number of steps you can take is {{max_steps}}.
Do not output an empty string!

# ACTION SPACE #
{{action_space}}

{query_tips}

{tips}

# RESPONSE FROMAT # 
For each task input, your response should contain:
1. One analysis of the task and the current environment, reasoning to determine the next action (prefix "Thought: ").
2. One action string in the ACTION SPACE (prefix "Action: ").

# EXAMPLE INTERACTION #
Observation: ...(the output of last actions, as provided by the environment and the code output, you don't need to generate it)

Thought: ...
Action: ...

################### TASK ###################
Please Solve this task:
{{task}}
"""

        def evaluate_prompt(query_tips, tips):
            prompt_template = format_prompt(query_tips.value, tips.value)
            score, results = self._evaluate_prompt(prompt_template)
            
            with open(f"textgrad_optimization/results_{int(time.time())}.json", 'w') as f:
                json.dump({
                    "score": score,
                    "results": results,
                    "prompt": prompt_template
                }, f, indent=2)
                
            return 1.0 - score
            
        eval_prompt = """
You're evaluating a system prompt for an SQL agent that uses the Snowflake database.
The goal is to optimize this prompt to make the agent more successful at correctly solving SQL tasks.

Evaluate the prompt critically by considering:
1. Clarity of instructions
2. Comprehensiveness of guidelines for SQL query writing
3. Error handling advice
4. Snowflake-specific best practices
5. Overall structure and readability

Provide specific feedback on how to improve the prompt to make the agent:
- More accurate in writing SQL queries
- Better at understanding database schemas
- More consistent in producing valid results
- More efficient in solving tasks with fewer steps
"""

        loss_fn = tg.TextLoss(eval_prompt)
        
        optimizer = tg.TGD(
            parameters=[sections["query_tips"], sections["tips"]]
        )
        
        best_prompt = None
        best_score = -1
        
        for iteration in range(5):
            logger.info(f"Starting optimization iteration {iteration+1}")
            
            current_prompt = format_prompt(sections["query_tips"].value, sections["tips"].value)
            loss = loss_fn(current_prompt)
            
            loss.backward()
            
            optimizer.step()
            
            score, results = self._evaluate_prompt(format_prompt(sections["query_tips"].value, sections["tips"].value))
            
            if score > best_score:
                best_score = score
                best_prompt = format_prompt(sections["query_tips"].value, sections["tips"].value)
                
                with open("textgrad_optimization/best_prompt.txt", 'w') as f:
                    f.write(best_prompt)
                    
                logger.info(f"New best prompt with score: {best_score}")
                
        logger.info(f"Optimization complete. Best score: {best_score}")
        return best_prompt

if __name__ == "__main__":
    import time
    
    os.makedirs("textgrad_optimization", exist_ok=True)
    
    optimizer = PromptOptimizer(SNOWFLAKE_SYSTEM, num_examples=TEST_EXAMPLES)
    
    optimized_prompt = optimizer.optimize_prompt()
    
    with open("textgrad_optimization/optimized_snowflake_prompt.py", 'w') as f:
        f.write(f"""
# Optimized SNOWFLAKE_SYSTEM prompt generated by TextGrad on {time.strftime('%Y-%m-%d %H:%M:%S')}

SNOWFLAKE_SYSTEM = \"\"\"
{optimized_prompt}
\"\"\"
""")
    
    logger.info("Optimization complete. Optimized prompt saved to textgrad_optimization/optimized_snowflake_prompt.py")