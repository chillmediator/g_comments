import json
import asyncio
import requests
import pandas as pd
from rich.console import Console
from rich.panel import Panel
import time
import os
from typing import Dict, List
import argparse

# Initialize console for nice output
console = Console()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Generate Google Maps comments using LLM')
    parser.add_argument('--issues', type=str, required=True,
                      help='Comma-separated list of issues to address in comments')
    parser.add_argument('--tone', type=str, required=True,
                      help='Tone and mood for the comments')
    return parser.parse_args()

async def wait_for_server(max_attempts=5):
    """Wait for Ollama server to be ready"""
    for i in range(max_attempts):
        try:
            response = requests.get('http://localhost:11434')
            if response.status_code == 200:
                console.print("[green]LLM server is ready![/green]")
                return True
        except:
            pass
        console.print(f"[yellow]Waiting for server... attempt {i+1}/{max_attempts}[/yellow]")
        await asyncio.sleep(2)
    return False

def load_prompts() -> Dict:
    """Load prompts from prompts.json file"""
    try:
        with open('prompts.json', 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        console.print("[green]Successfully loaded prompts for languages:", ", ".join(prompts.keys()))
        return prompts
    except Exception as e:
        console.print(f"[red]Error loading prompts: {str(e)}[/red]")
        raise

async def run_inference(system_prompt: str, user_prompt: str, language: str, args) -> List[Dict]:
    """Run inference with the LLM for a specific language"""
    try:
        # Prepare the prompt with placeholders
        formatted_user_prompt = user_prompt.replace(
            "{$ISSUES}", args.issues
        ).replace(
            "{$TONE_AND_MOOD}", args.tone
        ).replace(
            "{$ENGLISH_VARIANT}", "American English" if language == "english" else ""
        )

        # Make API call to the LLM
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "mistral",
                "prompt": f"{system_prompt}\n\n{formatted_user_prompt}",
                "stream": False
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"API call failed with status {response.status_code}")

        response_data = response.json()
        
        # Extract the CSV content from between <comments> tags
        response_text = response_data.get('response', '')
        start_idx = response_text.find('<comments>') + len('<comments>')
        end_idx = response_text.find('</comments>')
        
        if start_idx == -1 or end_idx == -1:
            raise Exception("Could not find comments section in response")
            
        csv_content = response_text[start_idx:end_idx].strip()
        
        # Parse CSV content
        import io
        df = pd.read_csv(io.StringIO(csv_content))
        return df.to_dict('records')

    except Exception as e:
        console.print(f"[red]Error running inference for {language}: {str(e)}[/red]")
        return []

async def main():
    """Main function to coordinate the comment generation process"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load prompts
    prompts = load_prompts()
    
    # Wait for LLM server
    if not await wait_for_server():
        console.print("[red]Could not connect to LLM server[/red]")
        return

    # Store all generated comments
    all_comments = []
    
    # Run inference for each language
    for language, prompts_data in prompts.items():
        console.print(f"\n[bold blue]Generating comments for {language}...[/bold blue]")
        
        comments = await run_inference(
            prompts_data['system_prompt'],
            prompts_data['user_prompt'],
            language,
            args
        )
        
        # Add language column to each comment
        for comment in comments:
            comment['language'] = language
        
        all_comments.extend(comments)
        
        # Small delay between languages
        await asyncio.sleep(2)
    
    # Save all comments to CSV
    if all_comments:
        df = pd.DataFrame(all_comments)
        df.to_csv('comments.csv', index=False)
        console.print(f"\n[green]Successfully saved {len(all_comments)} comments to comments.csv[/green]")
    else:
        console.print("[red]No comments were generated[/red]")

if __name__ == "__main__":
    asyncio.run(main())
