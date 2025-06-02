import argparse
import datetime
import json
import logging
import os
import random
import sys
import glob

from tqdm import tqdm

from spider_agent.envs.spider_agent import Spider_Agent_Env
from spider_agent.agent.agents import PromptAgent
from spider_agent.rag.integration import RagAugmentedAgent
from spider_agent.self_retrieval import AnalogicalPrompter, DatabaseContextExtractor

# Add support for custom prompts
if os.environ.get("SPIDER_SNOW_PROMPT_PATH"):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "textgrad_optimization"))
    try:
        from load_custom_prompt import patch_prompts
        patch_prompts()
    except ImportError:
        print("Warning: Custom prompt loader not found")

#  Logger Configs {{{ #
logger = logging.getLogger("spider_agent")
logger.setLevel(logging.DEBUG)

datetime_str: str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")

file_handler = logging.FileHandler(os.path.join("logs", "normal-{:}.log".format(datetime_str)), encoding="utf-8")
debug_handler = logging.FileHandler(os.path.join("logs", "debug-{:}.log".format(datetime_str)), encoding="utf-8")
stdout_handler = logging.StreamHandler(sys.stdout)
sdebug_handler = logging.FileHandler(os.path.join("logs", "sdebug-{:}.log".format(datetime_str)), encoding="utf-8")

file_handler.setLevel(logging.INFO)
debug_handler.setLevel(logging.DEBUG)
stdout_handler.setLevel(logging.INFO)
sdebug_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    fmt="\x1b[1;33m[%(asctime)s \x1b[31m%(levelname)s \x1b[32m%(module)s/%(lineno)d-%(processName)s\x1b[1;33m] \x1b[0m%(message)s")
file_handler.setFormatter(formatter)
debug_handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)
sdebug_handler.setFormatter(formatter)

stdout_handler.addFilter(logging.Filter("spider_agent"))
sdebug_handler.addFilter(logging.Filter("spider_agent"))

logger.addHandler(file_handler)
logger.addHandler(debug_handler)
logger.addHandler(stdout_handler)
logger.addHandler(sdebug_handler)
#  }}} Logger Configs # 



def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run end-to-end evaluation on the benchmark"
    )
    
    parser.add_argument("--multi_loop", action="store_true", default=False, help="Utilize multiple solution attempts to achieve best solution")
    parser.add_argument("--self_retrieval", action="store_true", default=False, help="Enable self-retrieval (analogical prompting) for generating relevant examples before each attempt")
    
    parser.add_argument("--max_steps", type=int, default=20)
    
    parser.add_argument("--max_memory_length", type=int, default=30)
    parser.add_argument("--suffix", '-s', type=str, default="gpt-4-try1")
    
    parser.add_argument("--model", type=str, default="gpt-4o")
    parser.add_argument("--temperature", type=float, default=0.5)
    parser.add_argument("--top_p", type=float, default=0.9)
    parser.add_argument("--max_tokens", type=int, default=2500)
    parser.add_argument("--stop_token", type=str, default=None)
    
    # example config
    parser.add_argument("--test_path","-t", type=str, default="./examples/spider2-snow.jsonl")
    parser.add_argument("--example_index", "-i", type=str, default="all", help="index range of the examples to run, e.g., '0-10', '2,3', 'all'")
    parser.add_argument("--example_name", "-n", type=str, default="", help="name of the example to run")
    parser.add_argument("--overwriting", action="store_true", default=False)
    parser.add_argument("--retry_failed", action="store_true", default=False)

    # output related
    parser.add_argument("--output_dir", type=str, default="output")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--bq_only", action="store_true")
    parser.add_argument("--local_only", action="store_true")
    parser.add_argument("--dbt_only", action="store_true")
    parser.add_argument("--sf_only", action="store_true")
    
    # RAG-specific arguments
    parser.add_argument("--use_rag", action="store_true", default=False, help="Use Retrieval-Augmented Generation")
    parser.add_argument("--embedding_model", type=str, default="sentence-transformers/all-MiniLM-L6-v2", help="Embedding model to use for RAG")
    parser.add_argument("--persist_directory", type=str, default="./rag_vectors", help="Directory to persist vector store")
    parser.add_argument("--schema_dir", type=str, default="./examples", help="Directory containing schema files")
    parser.add_argument("--knowledge_dir", type=str, default="./documents", help="Directory containing external knowledge")
    
    args = parser.parse_args()

    return args



def test(
    args: argparse.Namespace,
    test_all_meta: dict = None
) -> None:
    scores = []
    
    # log args
    logger.info("Args: %s", args)

    if args.suffix == "":
        logger.warning("No suffix is provided, the experiment id will be the model name.")
        experiment_id = args.model.split("/")[-1]
    else:
        experiment_id = args.model.split("/")[-1] + "-" + args.suffix
        
    if args.plan:
        experiment_id = f"{experiment_id}-plan"

    env_config = \
    {
        "image_name": "spider_agent-image",
        "init_args": {
            "name": experiment_id,
            "work_dir": "/workspace",
        }
    }
    
    # Create either a standard agent or RAG-augmented agent based on command-line args
    if args.use_rag:
        logger.info("Using RAG-augmented agent")
        agent = RagAugmentedAgent(
            model=args.model,
            max_tokens=args.max_tokens,
            top_p=args.top_p,
            temperature=args.temperature,
            max_memory_length=args.max_memory_length,
            max_steps=args.max_steps,
            use_plan=args.plan,
            # RAG-specific parameters
            use_rag=True,
            embedding_model=args.embedding_model,
            persist_directory=args.persist_directory,
            schema_dir=args.schema_dir,
            knowledge_dir=args.knowledge_dir
        )
    else:
        logger.info("Using standard agent without RAG")
        agent = PromptAgent(
            model=args.model,
            max_tokens=args.max_tokens,
            top_p=args.top_p,
            temperature=args.temperature,
            max_memory_length=args.max_memory_length,
            max_steps=args.max_steps,
            use_plan=args.plan
        )
    valid_ids = []
    ## load task configs
    assert os.path.exists(args.test_path) and args.test_path.endswith(".jsonl"), f"Invalid test_path, must be a valid jsonl file: {args.test_path}"
    with open(args.test_path, "r") as f:
        task_configs = [json.loads(line) for line in f]

        
    if args.example_name != "":
        task_configs = [task for task in task_configs if args.example_name in task["id"]]
    else:
        if args.example_index != "all":
            if "-" in args.example_index:
                start, end = map(int, args.example_index.split("-"))
                task_configs = task_configs[start:end]
            else:
                indices = list(map(int, args.example_index.split(",")))
                task_configs = [task_configs[i] for i in indices]
    
    for task_config in task_configs:
        instance_id = experiment_id +"/"+ task_config["instance_id"]
        output_dir = os.path.join(args.output_dir, instance_id)
        result_json_path =os.path.join(output_dir, "spider/result.json")


        task_type = None
        if task_config["instance_id"].startswith("bq") or task_config["instance_id"].startswith("ga"):
            task_type = 'bq'
        elif task_config["instance_id"].startswith("local"):
            task_type = 'local'
        elif task_config["instance_id"].startswith("sf"):
            task_type = 'sf'
        else:
            task_type = 'dbt'

        valid_types = set()
        if args.local_only: valid_types.add('local')
        if args.bq_only: valid_types.add('bq')
        if args.sf_only: valid_types.add('sf')
        if args.dbt_only: valid_types.add('dbt')
        
        if  (args.local_only or args.bq_only or args.sf_only or args.dbt_only):
            if task_type not in valid_types: continue
        else:
            pass

        valid_ids.append(task_config["instance_id"])
        
        if not args.overwriting and os.path.exists(result_json_path):
            logger.info("Skipping %s", instance_id)
            continue
        elif os.path.exists(result_json_path):
            logger.info("Overwriting %s", instance_id)
        else:
            logger.info("Running %s", instance_id)
        if args.retry_failed and os.path.exists(result_json_path):
            with open(result_json_path, "r") as f:
                result = json.load(f)
                if result["finished"] and (not "FAIL" in result["result"]) and (not "error" in result["result"].lower()):
                    logger.info("Skipping %s", instance_id)
                    continue
            logger.info("Retrying %s", instance_id)

        if os.path.exists(output_dir):
            os.system(f"rm -rf {output_dir}")
            logger.info("Removed existing %s", output_dir)

        os.makedirs(output_dir, exist_ok=True)

        env_config["init_args"]["name"] = experiment_id +"-"+ task_config["instance_id"]

        
        source_data_dir = os.path.dirname(args.test_path)        
        task_config['config'] = [{"type": "copy_all_subfiles", "parameters": {"dirs": [os.path.join(source_data_dir, task_config["instance_id"])]}}]

        if args.multi_loop:
            logger.info(f"Running multi-loop (3 attempts) for {instance_id}")
            successful_runs = []
            all_runs = []
            last_successful_sql = None  # Track the last successful SQL query
            
            # Initialize self-retrieval components if enabled
            analogical_prompter = None
            context_extractor = None
            if args.self_retrieval:
                analogical_prompter = AnalogicalPrompter(model=args.model)
                context_extractor = DatabaseContextExtractor()
                logger.info("Self-retrieval (analogical prompting) enabled")
            
            for attempt in range(3):
                # Create a separate output directory for each attempt
                attempt_dir = os.path.join(output_dir, f"attempt_{attempt+1}")
                os.makedirs(attempt_dir, exist_ok=True)
                
                # Create a new environment for each attempt
                attempt_env_config = env_config.copy()
                attempt_env_config["init_args"]["name"] = f"{experiment_id}-{task_config['instance_id']}-attempt-{attempt+1}"
                
                attempt_env = Spider_Agent_Env(
                    env_config=attempt_env_config,
                    task_config=task_config,
                    cache_dir="./cache",
                    mnt_dir=attempt_dir
                )
                
                # Prepare task instruction with potential modifications
                current_instruction = task_config["instruction"]
                
                # Add self-retrieval (analogical prompting) if enabled
                if args.self_retrieval and analogical_prompter and context_extractor:
                    try:
                        logger.info(f"Generating analogical examples for attempt {attempt+1}")
                        
                        # Extract database context from the environment
                        database_context = context_extractor.extract_database_context(task_config)
                        
                        # Generate analogical examples
                        analogical_examples = analogical_prompter.generate_analogical_examples(
                            task_instruction=current_instruction,
                            database_context=database_context,
                            num_examples=3
                        )
                        
                        # Format examples for inclusion in prompt
                        if analogical_examples:
                            examples_text = analogical_prompter.format_examples_for_prompt(analogical_examples)
                            current_instruction = examples_text + "\n" + current_instruction
                            logger.info(f"Added {len(analogical_examples)} analogical examples to prompt")
                        else:
                            logger.warning("No analogical examples generated")
                            
                    except Exception as e:
                        logger.warning(f"Failed to generate analogical examples: {e}")
                
                # If we have a previous successful solution, add it as well
                if attempt > 0 and last_successful_sql:
                    current_instruction = current_instruction + f"\n\nHere's a tentative previous solution that might help, however there is a possibility that it is wrong.:\n```\n{last_successful_sql}\n```"
                
                # Create modified task config with the enhanced instruction
                modified_task_config = task_config.copy()
                modified_task_config["instruction"] = current_instruction
                
                # Set up agent with the modified task
                agent.set_env_and_task(attempt_env)
                
                # Update the instruction and system message
                agent.instruction = modified_task_config["instruction"]
                agent.system_message = agent.system_message.replace(task_config["instruction"], modified_task_config["instruction"])
                
                # Update the first message in history_messages with the new system message
                if agent.history_messages and agent.history_messages[0]["role"] == "system":
                    agent.history_messages[0]["content"][0]["text"] = agent.system_message
                
                # Run the agent
                logger.info(f'Task input (attempt {attempt+1}/3): {agent.instruction}')
                done, result_output = agent.run()
                trajectory = agent.get_trajectory()
                
                # Save results for this attempt
                os.makedirs(os.path.join(attempt_dir, "spider"), exist_ok=True)
                result_files = attempt_env.post_process()
                
                spider_result = {
                    "attempt_number": attempt+1,
                    "finished": done, 
                    "steps": len(trajectory["trajectory"]),
                    "result": result_output,
                    "result_files": result_files, 
                    **trajectory
                }
                
                # Save individual attempt
                with open(os.path.join(attempt_dir, "spider/result.json"), "w") as f:
                    json.dump(spider_result, f, indent=2)
                
                all_runs.append(spider_result)
                
                # If successful, add to successful runs and extract SQL for next attempt
                if done:
                    successful_runs.append(spider_result)
                    
                    # Extract the SQL query for next attempt
                    if trajectory["trajectory"]:
                        for step in reversed(trajectory["trajectory"]):
                            action_str = step["action"]
                            if "SNOWFLAKE_EXEC_SQL" in action_str or "BIGQUERY_EXEC_SQL" in action_str:
                                last_successful_sql = action_str
                                break
                
                # Clean up
                attempt_env.close()
                
                # Delete sqlite files if needed
                # ... (rest of the implementation remains the same)
                
                # Delete sqlite files if needed
                if task_type == 'local':
                    sqlite_files = glob.glob(os.path.join(attempt_dir, '*.sqlite')) + \
                                  glob.glob(os.path.join(attempt_dir, '*.duckdb'))
                    for file_path in sqlite_files:
                        try:
                            os.remove(file_path)
                            print(f"Deleted: {file_path}")
                        except Exception as e:
                            print(f"Error deleting {file_path}: {e}")
            
            # Save multi-run summary
            with open(os.path.join(output_dir, "multi_results.json"), "w") as f:
                json.dump({
                    "total_attempts": 3,
                    "successful_attempts": len(successful_runs),
                    "successful_run_numbers": [run["attempt_number"] for run in successful_runs]
                }, f, indent=2)
            
            # Use best run as main result (last successful run, or last run if none succeeded)
            best_run = successful_runs[-1] if successful_runs else all_runs[-1]
            
            # Save as main result.json
            with open(os.path.join(output_dir, "best_result.json"), "w") as f:
                json.dump({
                    **best_run,
                    "multi_loop": True,
                    "total_attempts": 3,
                    "successful_attempts": len(successful_runs)
                }, f, indent=2)
            
            logger.info(f"Completed multi-loop for {instance_id}: {len(successful_runs)}/3 successful attempts")
        else:
            env = Spider_Agent_Env(
                env_config=env_config,
                task_config=task_config,
                cache_dir="./cache",
                mnt_dir=output_dir
            )
            agent.set_env_and_task(env)
            logger.info('Task input:' + task_config['instruction'])
            done, result_output = agent.run()
            trajectory = agent.get_trajectory()

            os.makedirs(os.path.join(output_dir, "spider"), exist_ok=True)
            result_files = env.post_process()
            spider_result = {"finished": done, "steps": len(trajectory["trajectory"]),
                           "result": result_output,"result_files": result_files, **trajectory}
            with open(os.path.join(output_dir, "spider/result.json"), "w") as f:
                json.dump(spider_result, f, indent=2)
            
            # Delete sqlite files
            if task_type == 'local':
                sqlite_files = glob.glob(os.path.join(output_dir, '*.sqlite')) + glob.glob(os.path.join(output_dir, '*.duckdb'))
                for file_path in sqlite_files:
                    try:
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")
        
        logger.info("Finished %s", instance_id)
        if not args.multi_loop:  # Only close env if not in multi_loop mode
            env.close()

if __name__ == '__main__':
    args = config()
    
    test(args)