Security Check
The Security Check feature ensures that users are aware of potential risks associated with tokens by evaluating them against a set of security criteria. Each criterion is carefully designed to highlight aspects that may indicate a token’s safety or risks.

Security Criteria
Criteria

Description

Severity

Type

Solution

Fake Token

This token is either a scam or imitation of another token.

Critical

Token Info


Ownership Renounced

Token's owner can adjust token parameters such as minting, token name, logo, website, etc.

Critical

Token Info

The current owner of token must transfer their owner ship to a NULL address .
Or set the Mint Authority and Freeze Authority as disable while using CLI at the creation for Solana tokens.

Honeypot

If a token is Honeypot, very high chance it is a scam. Buyers may not be able to sell this token, or the token contains malicious code.

Critical

Token Info


Freezable

Token SPL V2 element - the authority can freeze every token from transferring among wallets.

Critical

Token Extension

Freeze Authority

Freeze Authority

Freeze Authority is who can freeze every token from transferring among wallets.

Critical

Token Extension

Change Freeze Authority to Null address or just disable freeze authority at the creation of token.

Jupiter Strict List

If a token is in Strict List, it was verified by Jupiter's community.

High Risk

Community

https://station.jup.ag/guides/general/get-your-token-on-jupiter#getting-on-the-strict-list

Top Holders Percentage

If a token has high top 10 holder percentage, there are risks of those holders mass selling and make the token's price volatile.

High Risk

Community

Reduce the proportion of total token supply holdings within top 10 wallets.

Token Percentage of Owner

The percentage of tokens held by the token owner.

High Risk

Dev

Reduce the proportion of total token supply holding in Owner Address.

UA Percentage

The percentage of tokens held by the token Update Authority.

High Risk

Dev

Reduce the proportion of total token supply holding in Update Authority Address.

Buy Tax

Transfer fee will cause the actual value received when transfer a token to be less than expected, and high transfer fee may lead to large losses.

High Risk

Token Extension


Sell Tax

Transfer fee will cause the actual value received when transfer a token to be less than expected, and high transfer fee may lead to large losses.

High Risk

Token Extension


Max Fee

The maximum fee that the authority can charge on each transfer.

High Risk

Token Extension


Transfer Fees

Token SPL V2 element - the authority can charge a percentage fee when this token is transferred among wallets.

High Risk

Token Extension


Transfer Fee Config Authority

Config Authority is who can change the transfer fee anywhere from 0 to Max fee.

High Risk

Token Extension

Change the Transfer Fee Config Authority to NULL address.

Mintable

Mint function enables contract owner to issue more tokens and cause the coin price to plummet. It is extremely risky.

High Risk

Token Info

Change Mint Authority to Null wallet or just disable mint authority at the creation of token.

Mutable Info

The token information such as name, logo, website can be changed by the owner.

Medium Risk

Token Info

Change Update Authority to Null wallet or just disable at the creation of token.
First Mint Time

The token is first minted at this time. There can be several other mint events after this.

Neutral

Dev


First Mint Tx

The token is first minted at this transaction. There can be several other mint events after this.

Neutral

Dev


Creator Address

The token creator's address.

Neutral

Dev


Creator Balance

The token balance of token creator.

Neutral

Dev


Owner Address

Ownership is mostly used to adjust the parameters and status of the token, such as minting, token name, logo, website, etc.

Neutral

Dev


Owner Balance

The token current owner's address.

Neutral

Dev


UA Balance

The token balance of token Update Authority.

Neutral

Dev


Update Authority (UA)

The token's update authority address.

Neutral

Dev


Liquidity Burned

When a part of token liquidity is burnt, that part can never be traded in the open market.

Neutral

Liquidity


Liquidity Locked

When a part of token liquidity is locked, that part can not be transacted in the open market, which reduce the risks of mass selling. However those tokens can be unlocked in the future.

Neutral

Liquidity


LP Holders Count

The total number of liquidity providers on this token in multiple markets. The more LPs there are, the more decentralized the token becomes. Only count from the most liquid pool

Neutral

Liquidity


Fee Withdrawer

Withdrawer is who can withraw all the transfer fees to a wallet of their choice.

Neutral

Token Extension


Current Transfer Fees

The authority can charge a percentage fee when this token is transfered among wallets.

Neutral

Token Extension


Interpreting the Results
Pass: The token satisfies the criterion with no significant risks detected.
Warning: A potential risk is detected. Click the tooltip for more information.
Fail: The token fails the criterion and poses significant security concerns.
❗ Disclaimer
The Security Check feature is a tool to assist in evaluating token security. It is not a guarantee of safety or investment performance. Users should conduct their own due diligence and consult professionals before making investment decisions.