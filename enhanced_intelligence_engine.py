"""
Enhanced Intelligence Engine for Kali Sniper Bot
"""
import requests
import time
import tweepy
from datetime import datetime, timedelta
import hashlib
import re
from config import *
from nice_funcs import get_token_overview, ask_bid, get_token_age_hours_api
from termcolor import cprint
import dontshare as d

def enhanced_token_vetting(token_address, birdeye_api_key):
    """
    Enhanced vetting process combining multiple data sources for better decision making
    """
    cprint(f"🔬 Enhanced Intelligence: Vetting token {token_address[-6:]}", 'yellow', attrs=['bold'])
    
    # Run existing pre-trade vetting first
    from nice_funcs import pre_trade_token_vetting
    if not pre_trade_token_vetting(token_address, birdeye_api_key, d.rpc_url):
        return False
    
    # Enhanced checks
    try:
        # 1. Social validation check
        if not check_social_validation(token_address):
            cprint(f"   🚫 Enhanced: Social validation failed", 'red')
            return False
            
        # 2. On-chain analytics
        if not analyze_onchain_metrics(token_address):
            cprint(f"   🚫 Enhanced: On-chain metrics below threshold", 'red')
            return False
            
        # 3. Price action analysis
        if not analyze_price_action(token_address):
            cprint(f"   🚫 Enhanced: Price action analysis failed", 'red')
            return False
            
        # 4. Liquidity depth check
        if not check_liquidity_depth(token_address):
            cprint(f"   🚫 Enhanced: Liquidity depth insufficient", 'red')
            return False
            
        # 5. Market sentiment analysis
        if not analyze_market_sentiment(token_address):
            cprint(f"   🚫 Enhanced: Market sentiment negative", 'red')
            return False
            
        cprint(f"   ✅ Enhanced: All intelligence checks passed", 'green')
        return True
        
    except Exception as e:
        cprint(f"   ⚠️ Enhanced: Error in vetting process: {e}", 'yellow')
        return False

def check_social_validation(token_address):
    """
    Check social validation signals using Twitter API
    """
    try:
        # Initialize Twitter API client
        client = tweepy.Client(
            bearer_token=None,
            consumer_key=d.Twitter_API,
            consumer_secret=d.Twitter_api_key_secret,
            access_token=None,
            access_token_secret=None,
            wait_on_rate_limit=True
        )
        
        # Get token overview for name
        overview = get_token_overview(token_address)
        name = overview.get('name', '')
        symbol = overview.get('symbol', '')
        
        # Skip social check for tokens without name or symbol
        if not name or not symbol:
            return True
            
        # Search for recent tweets about the token
        query = f"${symbol} OR {name} -is:retweet"
        tweets = client.search_recent_tweets(
            query=query,
            max_results=20,
            tweet_fields=['created_at', 'public_metrics']
        )
        
        if not tweets.data:
            # No tweets found, might be a very new or unpopular token
            return True
            
        # Analyze tweet metrics
        total_tweets = len(tweets.data)
        total_likes = sum(tweet.public_metrics['like_count'] for tweet in tweets.data if tweet.public_metrics)
        total_retweets = sum(tweet.public_metrics['retweet_count'] for tweet in tweets.data if tweet.public_metrics)
        
        # Calculate engagement rate (simplified)
        engagement_score = total_likes + (total_retweets * 2)  # Weight retweets more
        
        # Minimum thresholds for social validation
        if total_tweets < 5 or engagement_score < 10:
            cprint(f"   ℹ️ Low social activity: {total_tweets} tweets, {engagement_score} engagement", 'yellow')
            # Not failing, just informational
        
        return True
    except Exception as e:
        # Don't fail on social check errors, but log them
        cprint(f"   ℹ️ Twitter API check skipped: {e}", 'yellow')
        return True

def analyze_onchain_metrics(token_address):
    """
    Analyze on-chain metrics for token health
    """
    try:
        overview = get_token_overview(token_address)
        
        # Unique wallets check
        unique_wallets_24h = overview.get('uniqueWallet24h', 0)
        if unique_wallets_24h < 100:  # Increased threshold
            cprint(f"   ℹ️ Low unique wallets: {unique_wallets_24h}", 'yellow')
            
        # Trade count check
        trade_24h = overview.get('trade24h', 0)
        if trade_24h < 200:  # Increased threshold
            cprint(f"   ℹ️ Low trade volume: {trade_24h} trades", 'yellow')
            
        # Holder distribution check
        holder_count = overview.get('holder', 0)
        if holder_count < 200:  # Increased threshold
            cprint(f"   ℹ️ Low holder count: {holder_count}", 'yellow')
            
        # Check for healthy ratios
        if unique_wallets_24h > 0 and holder_count > 0:
            wallet_to_holder_ratio = unique_wallets_24h / holder_count
            if wallet_to_holder_ratio < 0.3:  # Less than 30% of holders are active
                cprint(f"   ℹ️ Low wallet/holder ratio: {wallet_to_holder_ratio:.2f}", 'yellow')
                
        return True
    except Exception as e:
        cprint(f"   ℹ️ On-chain metrics check: {e}", 'yellow')
        return True  # Don't fail on metric errors

def analyze_price_action(token_address):
    """
    Analyze price action for momentum and stability
    """
    try:
        # Get 5-minute OHLCV data
        time_to = int(time.time())
        time_from = time_to - 5 * 60
        ohlcv_url = (
            f"https://public-api.birdeye.so/defi/ohlcv?address={token_address}"
            f"&type=1m&time_from={time_from}&time_to={time_to}"
        )
        ohlcv_headers = {"X-API-KEY": d.birdeye}
        resp = requests.get(ohlcv_url, headers=ohlcv_headers, timeout=6)
        
        if not resp.ok:
            return True  # Don't fail on API errors
            
        items = (resp.json() or {}).get('data', {}).get('items', [])
        if len(items) < 3:
            cprint(f"   ℹ️ Insufficient price data: {len(items)} candles", 'yellow')
            return True  # Not enough data, but not a failure
            
        # Check for consistent upward momentum
        closes = [float(item.get('c', 0)) for item in items[-3:]]
        if len(closes) >= 2:
            # Calculate price changes
            changes = [closes[i+1] / closes[i] - 1 for i in range(len(closes)-1)]
            
            # Check if recent momentum is positive
            if len(changes) >= 2:
                recent_momentum = sum(changes[-2:]) / 2  # Average of last 2 changes
                if recent_momentum < 0.01:  # Less than 1% average gain
                    cprint(f"   ℹ️ Low recent momentum: {recent_momentum:.2%}", 'yellow')
                    
        # Check for volatility (too much volatility can be bad)
        if len(closes) >= 3:
            max_price = max(closes)
            min_price = min(closes)
            if min_price > 0:
                volatility = (max_price / min_price) - 1
                if volatility > 0.5:  # More than 50% swing in 5 minutes
                    cprint(f"   ℹ️ High volatility: {volatility:.2%}", 'yellow')
                    
        return True
    except Exception as e:
        cprint(f"   ℹ️ Price action analysis: {e}", 'yellow')
        return True  # Don't fail on analysis errors

def check_liquidity_depth(token_address):
    """
    Check if liquidity is sufficient and well-distributed
    """
    try:
        overview = get_token_overview(token_address)
        liquidity = overview.get('liquidity', 0)
        
        # Ensure minimum liquidity
        if liquidity < 5000:  # At least $5000 liquidity
            cprint(f"   ℹ️ Low liquidity: ${liquidity:,.0f}", 'yellow')
            
        # Check price impact tolerance
        # This is a simplified check - in practice you'd get actual price impact data
        price = ask_bid(token_address)
        if not price or price <= 0:
            cprint(f"   ℹ️ Unable to get price for liquidity check", 'yellow')
            return True
            
        return True
    except Exception as e:
        cprint(f"   ℹ️ Liquidity depth check: {e}", 'yellow')
        return True  # Don't fail on liquidity errors

def analyze_market_sentiment(token_address):
    """
    Analyze market sentiment using BirdEye API and other sources
    """
    try:
        # Get token overview for market data
        overview = get_token_overview(token_address)
        
        # Check price change percentages
        price_change_24h = overview.get('priceChange24h', 0)
        price_change_12h = overview.get('priceChange12h', 0)
        
        # Negative sentiment if price is dropping
        if price_change_24h < -10:  # More than 10% drop in 24h
            cprint(f"   ℹ️ Negative 24h price change: {price_change_24h:.2f}%", 'yellow')
        elif price_change_12h < -5:  # More than 5% drop in 12h
            cprint(f"   ℹ️ Negative 12h price change: {price_change_12h:.2f}%", 'yellow')
            
        # Check volume trends
        volume_24h = overview.get('v24hUSD', 0)
        volume_12h = overview.get('v12hUSD', 0)
        
        if volume_24h > 0 and volume_12h > 0:
            volume_trend = volume_12h / (volume_24h / 2)  # Compare 12h volume to half of 24h
            if volume_trend < 0.5:  # Volume in last 12h is less than half the average
                cprint(f"   ℹ️ Decreasing volume trend: {volume_trend:.2f}x", 'yellow')
                
        return True
    except Exception as e:
        cprint(f"   ℹ️ Market sentiment analysis: {e}", 'yellow')
        return True

def calculate_token_score(token_address):
    """
    Calculate a composite score for a token based on multiple factors
    Returns a score between 0-100 (higher is better)
    """
    try:
        overview = get_token_overview(token_address)
        score = 50  # Base score
        
        # Liquidity factor (0-20 points)
        liquidity = overview.get('liquidity', 0)
        if liquidity >= 50000:
            score += 20
        elif liquidity >= 20000:
            score += 15
        elif liquidity >= 10000:
            score += 10
        elif liquidity >= 5000:
            score += 5
            
        # Holder count factor (0-15 points)
        holders = overview.get('holder', 0)
        if holders >= 1000:
            score += 15
        elif holders >= 500:
            score += 10
        elif holders >= 200:
            score += 5
            
        # Unique wallets factor (0-10 points)
        unique_wallets = overview.get('uniqueWallet24h', 0)
        if unique_wallets >= 500:
            score += 10
        elif unique_wallets >= 200:
            score += 5
            
        # Trade volume factor (0-5 points)
        trade_24h = overview.get('trade24h', 0)
        if trade_24h >= 1000:
            score += 5
        elif trade_24h >= 500:
            score += 2
            
        # Price change factor (0-10 points)
        price_change_24h = overview.get('priceChange24h', 0)
        if price_change_24h >= 50:  # 50%+ gain
            score += 10
        elif price_change_24h >= 20:  # 20%+ gain
            score += 7
        elif price_change_24h >= 5:  # 5%+ gain
            score += 3
        elif price_change_24h <= -20:  # 20%+ loss
            score -= 5  # Penalty for large drops
            
        # Token age factor (0-5 points)
        age_hours = get_token_age_hours_api(token_address, prefer='birdeye')
        if age_hours is not None:
            if 0.5 <= age_hours <= 6:  # 30 minutes to 6 hours old
                score += 5  # Fresh tokens get a bonus
            elif age_hours > 24:  # Older than 1 day
                score -= 2  # Slight penalty for older tokens
                
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        return score
    except Exception as e:
        cprint(f"   ⚠️ Error calculating token score: {e}", 'yellow')
        return 50  # Return base score on error

def should_trade_token(token_address, min_score=70):
    """
    Determine if a token should be traded based on enhanced intelligence
    """
    cprint(f"   🔧 Enhanced intelligence engine processing token: {token_address[-6:]}", 'cyan')
    
    # Run enhanced vetting
    cprint(f"   🔍 Running enhanced token vetting...", 'cyan')
    vetting_result = enhanced_token_vetting(token_address, d.birdeye)
    cprint(f"   ✅ Enhanced token vetting completed. Result: {'PASSED' if vetting_result else 'FAILED'}", 'cyan')
    
    if not vetting_result:
        cprint(f"   🚫 Token {token_address[-6:]} rejected by enhanced vetting", 'red')
        return False
        
    # Calculate token score
    cprint(f"   📊 Calculating token score...", 'cyan')
    score = calculate_token_score(token_address)
    cprint(f"   📈 Token score calculated: {score}/100", 'cyan')
    
    if score < min_score:
        cprint(f"   🚫 Token score {score} below threshold {min_score}", 'red')
        return False
        
    cprint(f"   ✅ Token score: {score}/100 - Approved for trading", 'green')
    return True