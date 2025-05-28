# Self-Retrieval Integration for Spider-Agent-Snow

## Overview

This implementation adds self-retrieval (analogical prompting) functionality to spider-agent-snow based on the paper "Large Language Models as Analogical Reasoners" (ICLR 2024). The self-retrieval system generates relevant SQL/database examples before each solution attempt, improving performance through analogical reasoning.

## Key Features

### 1. Analogical Prompting
- Generates 3-5 relevant SQL examples before each solution attempt
- Uses LLM to create database-specific analogies 
- Follows the methodology from the paper for self-generated exemplars

### 2. Database Context Extraction
- Automatically extracts database schema information
- Includes README files and DDL information
- Provides rich context for example generation

### 3. Integration with Multi-Loop
- Works seamlessly with existing `--multi_loop` functionality
- Generates fresh examples for each attempt iteration
- Enhances solution quality through diverse analogical reasoning

## Architecture

```
spider_agent/
└── self_retrieval/
    ├── __init__.py
    ├── analogical_prompter.py     # Core analogical prompting logic
    └── database_context.py       # Database context extraction
```

### Core Components

1. **AnalogicalPrompter**: Generates relevant SQL examples using LLM
2. **DatabaseContextExtractor**: Extracts database schema and documentation
3. **Integration in run.py**: Seamless integration with existing workflow

## Usage

### Basic Usage
```bash
# Enable self-retrieval with multi-loop
python3 run.py --multi_loop --self_retrieval --model gpt-4o -s test_analogical

# Run on specific example
python3 run.py --multi_loop --self_retrieval -n sf_bq001 --model gpt-4o
```

### Command Line Arguments
- `--self_retrieval`: Enable self-retrieval (analogical prompting)
- `--multi_loop`: Enable multiple solution attempts (recommended with self-retrieval)
- `--model`: LLM model to use (gpt-4o, gpt-4, etc.)

## Implementation Details

### Analogical Prompt Structure
```
# Recall relevant problems and solutions

## Current Problem:
{task_instruction}

## Database Context:
{database_context}

## Instructions:
Generate 3 analogical examples that are relevant to solving the current problem...
```

### Example Generation Process
1. Extract database context (schema, README, etc.)
2. Create analogical prompt with current task
3. Generate 3-5 relevant SQL examples via LLM
4. Format examples for inclusion in main prompt
5. Enhanced instruction sent to spider agent

### Integration Workflow
```python
if args.self_retrieval:
    # Extract database context
    db_context = extractor.extract_database_context(task_config)
    
    # Generate analogical examples
    examples = prompter.generate_analogical_examples(
        task_config["instruction"], 
        db_context
    )
    
    # Format and enhance instruction
    formatted_examples = prompter.format_examples_for_prompt(examples)
    enhanced_instruction = analogical_section + task_config["instruction"]
```

## Testing

### Integration Tests
Run comprehensive integration tests:
```bash
python3 test_integration.py
```

Tests validate:
- ✅ Database context extraction
- ✅ Analogical prompt generation  
- ✅ Example formatting
- ✅ Command line integration
- ✅ End-to-end workflow

### Manual Testing
```bash
# Test on a simple example
python3 run.py --multi_loop --self_retrieval -i 0 --model gpt-4o -s manual_test
```

## Configuration

### Model Settings
Default configuration in `AnalogicalPrompter`:
- Model: `gpt-4`
- Max tokens: `2000`
- Temperature: `0.3`
- Number of examples: `3`

### Customization
```python
prompter = AnalogicalPrompter(
    model="gpt-4o",
    max_tokens=3000, 
    temperature=0.2
)
```

## Performance Benefits

Based on the paper's findings, self-retrieval provides:
- **+4% average accuracy gain** over standard CoT
- **Tailored examples** for each specific problem
- **No manual labeling** required for examples
- **Better performance** with larger LLMs

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   pip install sentence-transformers
   ```

2. **LLM API Errors**
   - Check API keys and model availability
   - Retry logic handles temporary failures

3. **Context Length Issues**
   - Reduce `max_tokens` if hitting limits
   - Database context is automatically truncated

### Debug Mode
Enable detailed logging:
```python
import logging
logging.getLogger("spider_agent").setLevel(logging.DEBUG)
```

## Examples

### Input Task
```json
{
  "instruction": "Find the top 5 customers by total purchase amount in 2023",
  "type": "Snowflake", 
  "db_id": "ECOMMERCE"
}
```

### Generated Analogical Examples
```sql
-- Example 1: Top products by sales volume
SELECT product_name, SUM(quantity) as total_sold 
FROM sales 
GROUP BY product_name 
ORDER BY total_sold DESC LIMIT 10

-- Example 2: Highest spending customers  
SELECT c.name, SUM(o.amount) as total_spent
FROM customers c JOIN orders o ON c.id = o.customer_id 
WHERE o.date >= '2023-01-01'
GROUP BY c.id, c.name 
ORDER BY total_spent DESC
```

### Enhanced Instruction
The original instruction is enhanced with analogical examples before being sent to the spider agent, providing relevant context and patterns for solving the problem.

## Future Enhancements

1. **Dynamic Example Count**: Adjust number of examples based on problem complexity
2. **Example Caching**: Cache generated examples for similar problems
3. **Multi-Modal Examples**: Include visualization examples for complex queries
4. **Performance Metrics**: Track self-retrieval effectiveness per problem type

## References

- Paper: "Large Language Models as Analogical Reasoners" (ICLR 2024)
- Authors: Yasunaga et al.
- Original CoT: Wei et al. "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
