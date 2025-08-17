Here are three filter ideas you can combine into a powerful "Freshness Pipeline":

💡 Idea 1: The "Candle Count" Filter (The Simplest & Most Effective)
This is the most direct way to ensure a token is new.

Logic: After a new pool is detected, use the Birdeye API to fetch the 1-minute OHLCV data for the token. Count the number of candles.

Rule: If number_of_candles > 10 (i.e., the token has existed for more than 10 minutes), REJECT it. A true fresh launch will only have 1-3 candles when your bot first sees it.

Implementation: Add this check inside your pre_trade_token_vetting function. It's a fast and incredibly effective way to discard 90% of old tokens.

💡 Idea 2: The "Initial Momentum" Filter
This filter checks if the token has immediate signs of life, which legitimate projects do.

Logic: Look at the first 3-5 one-minute candles.

Rule 1 (Volume): Is the total volume for the first 5 minutes above a minimum threshold (e.g., $5,000)? If not, it's likely a dead or abandoned launch. REJECT.

Rule 2 (Price Action): Is there a catastrophic dump within the first 3 candles? For example, if candle_2_low < candle_1_high * 0.2 (an 80% dump), it's a classic rug pull. REJECT.

Implementation: This logic also goes into your pre_trade_token_vetting function. It requires fetching the first few candles and performing these simple calculations.

💡 Idea 3: The "Buy/Sell Pressure" Filter
This filter analyzes the nature of the initial trading activity.

Logic: Use the Birdeye API to get the number of unique buyers vs. unique sellers in the first 5-10 minutes.

Rule: Is the ratio of buyers / sellers < 2? A healthy launch should have significantly more buyers than sellers initially. If the ratio is close to 1, it could indicate bot activity or insiders selling into the launch. Consider this a red flag and REJECT.

Implementation: This is a slightly more advanced check that adds another layer of security to your vetting process.

Recommended Strategy
Combine all three ideas into a single, powerful pipeline. A token must pass all of these checks to be considered a valid snipe:

Age Check: Is the token's creation time confirmed to be within the last hour?

Candle Count Check: Does it have fewer than 10 one-minute candles?

Initial Momentum Check: Does it have sufficient initial volume and no immediate 80%+ crash?

Pressure Check: Is the initial buy pressure healthy?

By implementing this multi-stage "Freshness Filter," you will dramatically reduce the number of old tokens and rug pulls your bot interacts with, saving you capital and allowing you to focus only on the most promising new launches.