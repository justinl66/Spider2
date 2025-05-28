# Self-retrieval module for analogical prompting implementation
# Based on "Large Language Models as Analogical Reasoners" paper

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from spider_agent.agent.models import call_llm

logger = logging.getLogger("spider_agent")

class AnalogicalPrompter:
    """
    Implements analogical prompting functionality that generates relevant SQL/database examples 
    before each solution attempt, following the methodology from 
    "Large Language Models as Analogical Reasoners" paper.
    """
    
    def __init__(self, model="gpt-4", max_tokens=2000, temperature=0.3):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
    def generate_analogical_examples(self, 
                                   task_instruction: str, 
                                   database_context: str = "",
                                   num_examples: int = 3) -> List[Dict[str, Any]]:
        """
        Generate relevant analogical examples for the given task instruction.
        
        Args:
            task_instruction: The current task/problem to solve
            database_context: Context about the database schema and structure
            num_examples: Number of analogical examples to generate
            
        Returns:
            List of analogical examples with problem-solution pairs
        """
        
        analogical_prompt = self._create_analogical_prompt(
            task_instruction, database_context, num_examples
        )
        
        status = False
        response = ""
        
        while not status:
            status, response = call_llm({
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert database analyst who can recall relevant SQL problems and solutions to help solve new problems through analogical reasoning."
                    },
                    {
                        "role": "user", 
                        "content": analogical_prompt
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            })
            
            if not status:
                if response in ["context_length_exceeded", "rate_limit_exceeded", "max_tokens", "unknown_error"]:
                    logger.warning(f"LLM call failed with: {response}, retrying...")
                    continue
                else:
                    raise Exception(f"Failed to generate analogical examples: {response}")
        
        try:
            examples = self._parse_analogical_response(response)
            logger.info(f"Generated {len(examples)} analogical examples")
            return examples
        except Exception as e:
            logger.warning(f"Failed to parse analogical examples: {e}")
            return []
    
    def _create_analogical_prompt(self, task_instruction: str, database_context: str, num_examples: int) -> str:
        """Create the prompt for generating analogical examples."""
        
        prompt = f"""# Recall relevant problems and solutions

You are given a new SQL/database problem to solve. Before attempting to solve it, recall {num_examples} relevant problems and their solutions that share similar patterns, concepts, or approaches.

## Current Problem:
{task_instruction}

## Database Context:
{database_context}

## Instructions:
Generate {num_examples} analogical examples that are relevant to solving the current problem. Each example should:
1. Present a similar SQL/database problem scenario
2. Provide a clear, working SQL solution
3. Explain the key concepts or patterns used
4. Show how it relates to the current problem

Focus on problems involving similar:
- SQL operations (JOINs, aggregations, window functions, CTEs, etc.)
- Database concepts (data modeling, schema design, query optimization)
- Business logic patterns (time-based analysis, customer segmentation, financial calculations, etc.)
- Data transformation techniques

## Response Format:
Return your response as a JSON array where each example has this structure:
```json
[
  {{
    "problem": "Description of the analogical problem",
    "solution": "SQL query or solution approach", 
    "explanation": "Key concepts and reasoning",
    "relevance": "How this relates to the current problem"
  }}
]
```

Generate exactly {num_examples} examples that will help solve the current problem through analogical reasoning."""

        return prompt
    
    def _parse_analogical_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the LLM response to extract analogical examples."""
        
        # Try to extract JSON from the response
        response = response.strip()
        
        # Look for JSON array in the response
        import re
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                examples = json.loads(json_str)
                if isinstance(examples, list):
                    return examples
            except json.JSONDecodeError:
                pass
        
        # Fallback: try to parse structured text
        examples = []
        sections = re.split(r'(?:Example \d+|Problem \d+)', response)
        
        for section in sections[1:]:  # Skip first empty section
            if len(section.strip()) > 0:
                example = self._parse_text_example(section)
                if example:
                    examples.append(example)
        
        return examples[:3]  # Limit to 3 examples
    
    def _parse_text_example(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse a single example from text format."""
        
        example = {
            "problem": "",
            "solution": "",
            "explanation": "",
            "relevance": ""
        }
        
        # Simple pattern matching for structured text
        lines = text.strip().split('\n')
        current_field = None
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith(('problem:', 'scenario:')):
                current_field = "problem"
                example[current_field] = line.split(':', 1)[1].strip()
            elif line.lower().startswith(('solution:', 'sql:', 'query:')):
                current_field = "solution"
                example[current_field] = line.split(':', 1)[1].strip()
            elif line.lower().startswith(('explanation:', 'concept:', 'key')):
                current_field = "explanation"
                example[current_field] = line.split(':', 1)[1].strip()
            elif line.lower().startswith(('relevance:', 'relation:')):
                current_field = "relevance"
                example[current_field] = line.split(':', 1)[1].strip()
            elif current_field and line:
                example[current_field] += " " + line
        
        # Only return if we have at least problem and solution
        if example["problem"] and example["solution"]:
            return example
        
        return None
    
    def format_examples_for_prompt(self, examples: List[Dict[str, Any]]) -> str:
        """Format the analogical examples for inclusion in the main task prompt."""
        
        if not examples:
            return ""
        
        formatted = "\n# Relevant Examples and Solutions\n\n"
        formatted += "Here are some relevant problems and solutions that might help with the current task:\n\n"
        
        for i, example in enumerate(examples, 1):
            formatted += f"## Example {i}\n"
            formatted += f"**Problem:** {example.get('problem', 'N/A')}\n\n"
            formatted += f"**Solution:**\n```sql\n{example.get('solution', 'N/A')}\n```\n\n"
            formatted += f"**Key Concepts:** {example.get('explanation', 'N/A')}\n\n"
            formatted += f"**Relevance:** {example.get('relevance', 'N/A')}\n\n"
            formatted += "---\n\n"
        
        formatted += "Use these examples as inspiration and guidance for solving the current problem.\n\n"
        
        return formatted
