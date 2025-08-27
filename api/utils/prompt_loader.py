"""
Prompt loading utility for KohTravel agents
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class PromptLoader:
    """Utility class for loading markdown prompts"""
    
    def __init__(self, prompts_base_dir: Optional[str] = None):
        if prompts_base_dir is None:
            # Default to prompts directory in project root (go up from api/utils to root)
            current_dir = Path(__file__).parent.parent.parent
            prompts_base_dir = current_dir / "prompts"
        
        self.prompts_dir = Path(prompts_base_dir)
        logger.info("PromptLoader initialized", prompts_dir=str(self.prompts_dir))
    
    def load_agent_prompt(self, agent_name: str) -> Optional[str]:
        """Load system prompt for an agent from markdown file"""
        prompt_file = self.prompts_dir / "agents" / f"{agent_name}.md"
        
        try:
            if prompt_file.exists():
                content = prompt_file.read_text(encoding="utf-8")
                logger.info("Loaded agent prompt", agent=agent_name, file=str(prompt_file))
                return content.strip()
            else:
                logger.warning("Agent prompt file not found", agent=agent_name, file=str(prompt_file))
                return None
        except Exception as e:
            logger.error("Failed to load agent prompt", agent=agent_name, error=str(e))
            return None
    
    def load_tool_prompt(self, tool_name: str) -> Optional[str]:
        """Load prompt/documentation for a tool from markdown file"""
        prompt_file = self.prompts_dir / "tools" / f"{tool_name}.md"
        
        try:
            if prompt_file.exists():
                content = prompt_file.read_text(encoding="utf-8")
                logger.info("Loaded tool prompt", tool=tool_name, file=str(prompt_file))
                return content.strip()
            else:
                logger.warning("Tool prompt file not found", tool=tool_name, file=str(prompt_file))
                return None
        except Exception as e:
            logger.error("Failed to load tool prompt", tool=tool_name, error=str(e))
            return None
    
    def get_all_agent_prompts(self) -> Dict[str, str]:
        """Get all available agent prompts"""
        prompts = {}
        agents_dir = self.prompts_dir / "agents"
        
        if not agents_dir.exists():
            logger.warning("Agents prompts directory not found", dir=str(agents_dir))
            return prompts
        
        try:
            for prompt_file in agents_dir.glob("*.md"):
                agent_name = prompt_file.stem
                content = self.load_agent_prompt(agent_name)
                if content:
                    prompts[agent_name] = content
        except Exception as e:
            logger.error("Failed to load agent prompts", error=str(e))
        
        return prompts
    
    def get_all_tool_prompts(self) -> Dict[str, str]:
        """Get all available tool prompts"""
        prompts = {}
        tools_dir = self.prompts_dir / "tools"
        
        if not tools_dir.exists():
            logger.warning("Tools prompts directory not found", dir=str(tools_dir))
            return prompts
        
        try:
            for prompt_file in tools_dir.glob("*.md"):
                tool_name = prompt_file.stem
                content = self.load_tool_prompt(tool_name)
                if content:
                    prompts[tool_name] = content
        except Exception as e:
            logger.error("Failed to load tool prompts", error=str(e))
        
        return prompts


# Global instance for easy import
prompt_loader = PromptLoader()