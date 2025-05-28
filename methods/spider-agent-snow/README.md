# Spider-Agent-Snow

An Agent Method Baseline for Spider 2.0-Snow based on Docker environment.

## 🚀 Quickstart

#### Run Spider-Agent(Snow)

1. **Install Docker**. Follow the instructions in the [Docker setup guide](https://docs.docker.com/engine/install/) to install Docker on your machine. 
2. **Install conda environment**.
```
git clone https://github.com/xlang-ai/Spider2.git
cd methods/spider-agent-snow

# Optional: Create a Conda environment for Spider 2.0
# conda create -n spider2 python=3.11
# conda activate spider2

# Install required dependencies
pip install -r requirements.txt
```
3. **Configure credential**: Follow this [guideline](https://github.com/xlang-ai/Spider2/blob/main/assets/Snowflake_Guideline.md) to get your own Snowflake username and password in our snowflake database. You must update `snowflake_credential.json`.

4. **Spider 2.0-Snow Setup**
```
python spider_agent_setup_snow.py
```

5. **Run agent**
```
export OPENAI_API_KEY=your_openai_api_key
python run.py --model gpt-4o -s test1
```

### For MARS
```
export SPIDER_SNOW_PROMPT_PATH=/home/jl6/GitRepos/Spider2/methods/spider-agent-snow/textgrad_optimization/optimized_snowflake_prompt.py
export AZURE_API_KEY=your_openai_api_key
python run.py --example_index 0 --multi_loop --use_rag --self_retrieval --model azure/o4-mini -s modified_test
```

### Running with RAG (Retrieval-Augmented Generation)

The agent now supports Retrieval-Augmented Generation (RAG) to enhance SQL queries with relevant context:

```
# Run with default RAG settings
python run.py --model azure/o4-mini -s rag_test1 --use_rag

# Run with custom RAG settings
python run.py --model azure/o4-mini -s rag_test2 --use_rag \
  --embedding_model "sentence-transformers/all-mpnet-base-v2" \
  --persist_directory "./custom_rag_vectors" \
  --schema_dir "./examples" \
  --knowledge_dir "../../spider2-snow/resource/documents"
```

### Using Multi-Loop with Self-Retrieval (Analogical Prompting)

The agent supports self-retrieval functionality based on "Large Language Models as Analogical Reasoners" that generates relevant examples before each solution attempt:

```
# Run with multi-loop and self-retrieval enabled
python run.py --model gpt-4o -s self_retrieval_test --multi_loop --self_retrieval

# This will:
# 1. Generate analogical examples before each attempt
# 2. Use these examples to guide the solution process
# 3. Provide better context for SQL problem solving
```

### Evaluation

#### Extract Results

Reorganize run results into a standard submission format, here we store the answer directly into the evaluation suite

```python
python get_spider2snow_submission_data.py --experiment_suffix <The name of this experiment> --results_folder_name <Standard Submission Folders>
python get_spider2snow_submission_data.py --experiment_suffix gpt-4o-test1 --results_folder_name ../../spider2-snow/evaluation_suite/gpt-4o-test1
```

#### Run Evaluation Scripts

You can run `evaluate.py` in the [evaluation suite](https://github.com/xlang-ai/Spider2/tree/main/spider2-snow/evaluation_suite) folder of `spider2-snow` to get the evaluation results.


```bash
python evaluate.py --result_dir gpt-4o-test1 --mode exec_result
```


