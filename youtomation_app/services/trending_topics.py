"""
Trending Topics Service
Fetches trending searching topics from Google Trends
"""
import logging
from typing import List, Dict, Optional
from pytrends.request import TrendReq
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class TrendingTopicsService:
    """Service for fetching trending topics from Google Trends"""
    
    def __init__(self, language: str = 'en', timezone: int = 0, hl: str = 'en-US'):
        """
        Initialize Google Trends API client
        
        Args:
            language: Language code (e.g., 'en', 'es', 'fr')
            timezone: Timezone offset in minutes
            hl: Host language
        """
        self.language = language
        self.timezone = timezone
        self.hl = hl
        self.pytrends = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize PyTrends client with retry logic"""
        try:
            self.pytrends = TrendReq(hl=self.hl, tz=self.timezone, retries=2, backoff_factor=0.1)
            logger.info("Google Trends API client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Trends client: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_trending_searches(self, geo: str = 'US', category: str = '0') -> List[Dict]:
        """
        Get trending searches for a region
        
        Args:
            geo: Geographic region code (e.g., 'US', 'GB', 'IN')
            category: Google Trends category ID
            
        Returns:
            List of trending topics with metadata
        """
        if not self.pytrends:
            self._initialize_client()
        
        try:
            logger.info(f"Fetching trending searches for {geo}")
            # Get daily trends
            trending = self.pytrends.trending_searches(pn=geo)
            
            # Convert to list of dicts with additional metadata
            results = []
            for idx, topic in enumerate(trending[0].tolist()):
                results.append({
                    'title': topic,
                    'rank': idx + 1,
                    'geo': geo,
                    'category': category,
                })
            
            logger.info(f"Found {len(results)} trending topics")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching trending searches: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_interest_by_time(self, keyword: str, timeframe: str = 'now 7-d') -> Dict:
        """
        Get interest over time for a keyword
        
        Args:
            keyword: Search keyword
            timeframe: Time range (e.g., 'now 1-d', 'now 7-d', '2020-01-01 2020-12-31')
            
        Returns:
            Interest data with timestamps
        """
        if not self.pytrends:
            self._initialize_client()
        
        try:
            logger.info(f"Fetching interest over time for '{keyword}'")
            self.pytrends.build_payload([keyword], timeframe=timeframe, geo='US')
            interest_df = self.pytrends.interest_over_time()
            
            return {
                'keyword': keyword,
                'data': interest_df.to_dict(),
                'timeframe': timeframe,
            }
            
        except Exception as e:
            logger.error(f"Error fetching interest over time: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_interest_by_region(self, keyword: str, resolution: str = 'COUNTRY') -> Dict:
        """
        Get interest by region for a keyword
        
        Args:
            keyword: Search keyword
            resolution: Regional resolution ('COUNTRY', 'REGION', 'CITY', 'DMA')
            
        Returns:
            Interest data by region
        """
        if not self.pytrends:
            self._initialize_client()
        
        try:
            logger.info(f"Fetching interest by region for '{keyword}'")
            self.pytrends.build_payload([keyword])
            
            if resolution == 'COUNTRY':
                interest_df = self.pytrends.interest_by_region()
            else:
                interest_df = self.pytrends.interest_by_region(resolution=resolution)
            
            return {
                'keyword': keyword,
                'data': interest_df.to_dict(),
                'resolution': resolution,
            }
            
        except Exception as e:
            logger.error(f"Error fetching interest by region: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_related_queries(self, keyword: str) -> Dict:
        """
        Get related queries for a keyword
        
        Args:
            keyword: Search keyword
            
        Returns:
            Related queries with metrics
        """
        if not self.pytrends:
            self._initialize_client()
        
        try:
            logger.info(f"Fetching related queries for '{keyword}'")
            self.pytrends.build_payload([keyword])
            related_queries = self.pytrends.related_queries()
            
            return {
                'keyword': keyword,
                'top_queries': related_queries[keyword]['top'].to_dict() if related_queries[keyword]['top'] is not None else [],
                'rising_queries': related_queries[keyword]['rising'].to_dict() if related_queries[keyword]['rising'] is not None else [],
            }
            
        except Exception as e:
            logger.error(f"Error fetching related queries: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_suggestions(self, keyword: str) -> List[str]:
        """
        Get Google Trends suggestions for a keyword
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of suggestions
        """
        if not self.pytrends:
            self._initialize_client()
        
        try:
            logger.info(f"Fetching suggestions for '{keyword}'")
            suggestions = self.pytrends.suggestions(keyword)
            
            return [s['title'] for s in suggestions]
            
        except Exception as e:
            logger.error(f"Error fetching suggestions: {str(e)}")
            raise
    
    def get_top_trending_topic(self, geo: str = 'US') -> Optional[Dict]:
        """
        Get the top trending topic for a region
        
        Args:
            geo: Geographic region code
            
        Returns:
            Top trending topic details
        """
        try:
            trending = self.get_trending_searches(geo=geo)
            if trending:
                top_topic = trending[0]
                logger.info(f"Top trending topic: {top_topic['title']}")
                return top_topic
            return None
            
        except Exception as e:
            logger.error(f"Error getting top trending topic: {str(e)}")
            return None
    
    def get_trending_topics_batch(
        self,
        regions: List[str] = None,
        limit: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Get trending topics from multiple regions
        
        Args:
            regions: List of region codes (default: ['US', 'GB', 'IN', 'CA', 'AU'])
            limit: Number of trending topics per region
            
        Returns:
            Dict mapping region to trending topics
        """
        if regions is None:
            regions = ['US', 'GB', 'IN', 'CA', 'AU']
        
        batch_results = {}
        
        for region in regions:
            try:
                trending = self.get_trending_searches(geo=region)
                batch_results[region] = trending[:limit]
                logger.info(f"Retrieved {len(trending[:limit])} topics for {region}")
            except Exception as e:
                logger.error(f"Error fetching trends for {region}: {str(e)}")
                batch_results[region] = []
        
        return batch_results
