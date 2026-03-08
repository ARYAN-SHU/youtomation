"""
Script Generator Service
Generates YouTube video scripts from trending topics
"""
import logging
import re
from typing import Optional, Dict
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScriptGeneratorService:
    """Service for generating video scripts"""
    
    # Script templates for different styles
    TEMPLATES = {
        'educational': """
Title: {title}

[HOOK - 0-5 seconds]
{hook}

[MAIN CONTENT - 5-50 seconds]
{main_content}

[TIPS/INSIGHTS - 50-100 seconds]
{tips}

[CALL TO ACTION - Final 10 seconds]
{cta}
""",
        'entertainment': """
{intro}

{story}

{punchline}

{outro}
""",
        'news': """
[BREAKING NEWS]
{headline}

[DETAILS]
{details}

[ANALYSIS]
{analysis}

[CONCLUSION]
{conclusion}
""",
    }
    
    def __init__(self):
        """Initialize script generator"""
        logger.info("Script Generator Service initialized")
    
    def generate_script_template(
        self,
        topic: str,
        style: str = 'educational',
        word_count: int = 650,
        **kwargs
    ) -> str:
        """
        Generate a script from template
        
        Args:
            topic: Topic for the script
            style: Script style ('educational', 'entertainment', 'news')
            word_count: Target word count
            **kwargs: Template variables
            
        Returns:
            Generated script text
        """
        try:
            if style not in self.TEMPLATES:
                logger.warning(f"Unknown style: {style}, using 'educational'")
                style = 'educational'
            
            # Generate sections
            script_data = {
                'title': kwargs.get('title', topic),
                'hook': self._generate_hook(topic),
                'main_content': self._generate_main_content(topic, word_count),
                'tips': self._generate_tips(topic),
                'cta': self._generate_cta(),
                'intro': self._generate_intro(topic),
                'story': self._generate_story(topic),
                'punchline': self._generate_punchline(topic),
                'outro': self._generate_outro(),
                'headline': self._generate_headline(topic),
                'details': self._generate_details(topic),
                'analysis': self._generate_analysis(topic),
                'conclusion': self._generate_conclusion(topic),
            }
            
            # Fill template
            template = self.TEMPLATES[style]
            script = template.format(**script_data)
            
            # Clean script
            script = self._clean_script(script)
            
            # Validate word count
            actual_words = len(script.split())
            logger.info(f"Script generated for '{topic}' ({actual_words} words)")
            
            return script
            
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            raise
    
    def _generate_hook(self, topic: str) -> str:
        """Generate opening hook"""
        hooks = [
            f"Did you know about the latest trend in {topic}?",
            f"You won't believe what we just discovered about {topic}!",
            f"Here's everything you need to know about {topic} right now.",
            f"This {topic} development is revolutionary.",
            f"Wait until you hear about this {topic} breakthrough!",
        ]
        return hooks[hash(topic) % len(hooks)]
    
    def _generate_main_content(self, topic: str, word_count: int) -> str:
        """Generate main content section"""
        # This is a simplified version. In production, use LLM APIs like OpenAI
        content = f"""
Today, we're diving deep into the fascinating world of {topic}. {topic} has been trending 
across the internet, and there are several important reasons why. First, let's understand what 
{topic} actually means and why it's captured the attention of so many people.

The significance of {topic} cannot be overstated. It represents a shift in how people think about 
this particular subject area. Over the past few weeks, we've seen unprecedented growth in interest, 
with millions of people searching for information about {topic} every single day.

What makes {topic} particularly interesting is its widespread impact across multiple industries 
and communities. From social media to traditional news outlets, everyone is talking about {topic}. 
This viral phenomenon has led to numerous discussions, debates, and innovations in the field.

Key aspects of {topic} include its accessibility, relevance, and potential long-term effects. 
Experts believe that {topic} will continue to shape our society for years to come. The implications 
are far-reaching and touch almost every aspect of our daily lives."""
        
        return content
    
    def _generate_tips(self, topic: str) -> str:
        """Generate tips/insights section"""
        tips = f"""
1. Stay informed about {topic} trends
2. Understand the core concepts of {topic}
3. Follow key opinion leaders discussing {topic}
4. Participate in {topic} communities
5. Apply insights from {topic} to your life
"""
        return tips
    
    def _generate_cta(self) -> str:
        """Generate call-to-action"""
        ctas = [
            "Don't forget to like, comment, and subscribe for more updates on trending topics!",
            "Make sure to hit the notification bell so you never miss our latest videos!",
            "Subscribe now for daily updates on what's trending today!",
            "Like this video, subscribe to our channel, and let us know your thoughts!",
        ]
        return ctas[0]
    
    def _generate_intro(self, topic: str) -> str:
        """Generate introduction"""
        return f"Welcome back! Today we're exploring the phenomenon that is {topic}."
    
    def _generate_story(self, topic: str) -> str:
        """Generate story section"""
        return f"The story of {topic} is truly remarkable. It all started when..."
    
    def _generate_punchline(self, topic: str) -> str:
        """Generate punchline"""
        return f"And that's what makes {topic} so incredibly interesting!"
    
    def _generate_outro(self) -> str:
        """Generate outro"""
        return "Thanks for watching! See you in the next video!"
    
    def _generate_headline(self, topic: str) -> str:
        """Generate headline"""
        return f"Breaking: {topic} reaches new heights"
    
    def _generate_details(self, topic: str) -> str:
        """Generate details section"""
        return f"Here are the key details about {topic}..."
    
    def _generate_analysis(self, topic: str) -> str:
        """Generate analysis section"""
        return f"What does {topic} mean for us? Let's analyze..."
    
    def _generate_conclusion(self, topic: str) -> str:
        """Generate conclusion"""
        return f"In conclusion, {topic} represents an important development."
    
    def _clean_script(self, script: str) -> str:
        """Clean up script formatting"""
        # Remove extra whitespace
        script = re.sub(r'\n\s*\n', '\n\n', script)
        script = re.sub(r' +', ' ', script)
        script = script.strip()
        return script
    
    def generate_script_from_content(
        self,
        content: str,
        target_word_count: int = 650
    ) -> str:
        """
        Generate script from provided content
        
        Args:
            content: Base content for script
            target_word_count: Target word count
            
        Returns:
            Formatted script
        """
        try:
            # Add intro, outro, and CTA
            script = f"""
INTRODUCTION:
Welcome to today's video. We have something truly interesting to share with you.

CONTENT:
{content}

TIPS:
Here are the key takeaways from today's discussion.

CALL TO ACTION:
Don't forget to like and subscribe for more great content!

OUTRO:
Thanks for watching. We'll see you in the next video!
"""
            
            script = self._clean_script(script)
            word_count = len(script.split())
            logger.info(f"Script generated from content ({word_count} words)")
            
            return script
            
        except Exception as e:
            logger.error(f"Error generating script from content: {str(e)}")
            raise
    
    def generate_script_with_llm(
        self,
        topic: str,
        word_count: int = 650,
        style: str = 'educational',
        api_key: str = None
    ) -> Optional[str]:
        """
        Generate script using LLM API (e.g., OpenAI GPT)
        
        Args:
            topic: Topic for the script
            word_count: Target word count
            style: Script style
            api_key: API key for LLM service
            
        Returns:
            Generated script or None if error
        """
        try:
            # This is a placeholder for LLM integration
            # In production, integrate with OpenAI, Anthropic, or similar
            logger.info(f"LLM script generation not yet implemented. Using template instead.")
            return self.generate_script_template(topic, style, word_count)
            
        except Exception as e:
            logger.error(f"Error generating script with LLM: {str(e)}")
            return None
    
    def validate_script(self, script: str, min_words: int = 650, max_words: int = 1100) -> Dict:
        """
        Validate script meets requirements
        
        Args:
            script: Script text to validate
            min_words: Minimum word count
            max_words: Maximum word count
            
        Returns:
            Validation result dictionary
        """
        word_count = len(script.split())
        lines = script.strip().split('\n')
        has_intro = any('intro' in line.lower() or 'welcome' in line.lower() for line in lines)
        has_conclusion = any('conclusion' in line.lower() or 'thanks' in line.lower() for line in lines)
        
        is_valid = (min_words <= word_count <= max_words) and has_intro and has_conclusion
        
        result = {
            'is_valid': is_valid,
            'word_count': word_count,
            'min_words': min_words,
            'max_words': max_words,
            'has_intro': has_intro,
            'has_conclusion': has_conclusion,
            'issues': []
        }
        
        if word_count < min_words:
            result['issues'].append(f"Script too short: {word_count} words (minimum: {min_words})")
        if word_count > max_words:
            result['issues'].append(f"Script too long: {word_count} words (maximum: {max_words})")
        if not has_intro:
            result['issues'].append("Script missing introduction")
        if not has_conclusion:
            result['issues'].append("Script missing conclusion")
        
        logger.info(f"Script validation: {result['is_valid']} ({word_count} words)")
        
        return result
    
    def add_speaker_notes(self, script: str, add_timing: bool = True) -> str:
        """
        Add speaker notes to script with timing
        
        Args:
            script: Original script
            add_timing: Add estimated timing annotations
            
        Returns:
            Script with speaker notes
        """
        if not add_timing:
            return script
        
        # Estimate 150 words per minute speaking rate
        words = script.split()
        words_per_minute = 150
        estimated_minutes = len(words) / words_per_minute
        
        return f"""
ESTIMATED DURATION: {estimated_minutes:.1f} minutes

SCRIPT:
{script}

SPEAKER NOTES:
- Speak clearly and at a moderate pace
- Emphasize key points
- Make eye contact with camera
- Use natural gestures
- Pause for emphasis where appropriate
"""
