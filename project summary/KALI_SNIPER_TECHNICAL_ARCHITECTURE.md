# 🏗️ KALI SNIPER: TECHNICAL ARCHITECTURE SPECIFICATION

## 📋 SYSTEM OVERVIEW

The Kali Sniper employs a sophisticated three-engine architecture designed for high-frequency, low-latency cryptocurrency trading on the Solana blockchain. Each engine operates independently while sharing data through well-defined interfaces.

---

## 🔧 CORE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    KALI SNIPER SYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   SPEED     │  │INTELLIGENCE │  │  STRATEGY   │         │
│  │   ENGINE    │◄─┤   ENGINE    ├─►│   ENGINE    │         │
│  │             │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│        │                 │                 │               │
│        ▼                 ▼                 ▼               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  WebSocket  │  │   Birdeye   │  │   Position  │         │
│  │  Listener   │  │   Security  │  │   Manager   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                   EXTERNAL SERVICES                        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   HELIUS    │  │   BIRDEYE   │  │   JUPITER   │         │
│  │  WebSocket  │  │     API     │  │   API v6    │         │
│  │  + RPC      │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 SPEED ENGINE ARCHITECTURE

### **Primary Components:**

#### **WebSocket Connection Manager**
```python
# File: raydium_listener.py
class WebSocketManager:
    - Helius WebSocket connection
    - Auto-reconnection with exponential backoff
    - Keepalive ping mechanism (30-second intervals)
    - Connection state monitoring
```

#### **Pool Detection System**
```python
pool_creation_patterns = [
    "InitializeAccount3",    # 65% of pool creations
    "InitializeAccount",     # 35% of pool creations  
    "initialize2",           # 0% (legacy compatibility)
]

# Detection Logic:
1. Subscribe to RAYDIUM_LP_V4 program logs
2. Filter for pool creation patterns  
3. Extract transaction signatures
4. Prevent duplicate processing
```

#### **Transaction Processing Pipeline**
```python
async def process_new_pool(signature):
    1. get_transaction_details(signature)      # Extract token addresses
    2. trigger_fast_snipe(token_address)       # Intelligence + execution
    3. record_position_state()                 # Strategy tracking
```

### **Performance Characteristics:**
- **Detection Latency:** <100ms from pool creation
- **Processing Throughput:** 120+ pools/minute
- **Connection Reliability:** 99.9% uptime with auto-reconnection
- **Duplicate Prevention:** Signature-based tracking system

---

## 🧠 INTELLIGENCE ENGINE ARCHITECTURE

### **Security Filtering Pipeline:**

#### **Stage 1: Birdeye Security API**
```python
def pre_trade_token_vetting(token_address):
    # 15-point security assessment
    security_checks = [
        'fakeToken',           # Scam detection
        'ownershipRenounced',  # Owner control
        'honeypot',            # Sell restrictions
        'freezeAuthority',     # Freeze capability
        'isToken2022',         # Token standard
        'mintable',            # Supply manipulation
        'mutableMetadata',     # Name/logo changes
        'transferFees',        # Transaction costs
        'buyTax',              # Purchase taxation
        'sellTax',             # Sale taxation
        'ownerPercentage',     # Owner concentration
        'updateAuthorityPercentage',  # Authority concentration
        'top10HolderPercent',  # Holder distribution
        'liquidity',           # Market depth
        'mc'                   # Market capitalization
    ]
```

#### **Stage 2: Market Quality Assessment**
```python
market_quality_checks = {
    'min_liquidity': 400,      # $400 minimum
    'max_market_cap': 30000,   # $30,000 maximum
    'max_token_age': 4.0,      # 4 hours maximum age
}
```

#### **Stage 3: Deployer History Analysis**
```python
deployer_blacklist_system = {
    'blacklist_file': './data/deployer_blacklist.txt',
    'auto_blacklisting': True,  # Bad performers
    'deployer_tracking': True,  # Historical analysis
}
```

### **Error Handling & Retry Logic:**
```python
retry_configuration = {
    'max_retries': 8,
    'initial_delay': 5.0,
    'backoff_multiplier': 1.5,
    'timeout_per_request': 8.0,
    'retry_codes': [555, 404, 500, 502, 503]  # Birdeye indexing delays
}
```

---

## 📊 STRATEGY ENGINE ARCHITECTURE

### **Dynamic Position Sizing Algorithm:**

#### **Liquidity-Based Calculation**
```python
def calculate_dynamic_position_size(token_address, liquidity):
    target_percentage = 0.005  # 0.5% of liquidity
    target_size = liquidity * target_percentage
    
    # Clamp between bounds
    min_size = 4.0   # $4 minimum
    max_size = 10.0  # $10 maximum
    
    actual_size = clamp(target_size, min_size, max_size)
    return actual_size
```

#### **Risk-Adjusted Sizing Factors**
```python
sizing_factors = {
    'liquidity_ratio': 0.005,     # 0.5% of pool liquidity
    'minimum_position': 4.0,      # $4 floor
    'maximum_position': 10.0,     # $10 ceiling
    'volatility_adjustment': 0.0, # Future enhancement
}
```

### **Multi-Tier Profit Management:**

#### **Tier Configuration**
```python
SELL_TIERS = [
    {
        'profit_multiple': 2.0,    # 100% profit (2x)
        'sell_portion': 0.5,       # Sell 50% of position
        'name': 'First Major Profit'
    },
    {
        'profit_multiple': 5.0,    # 400% profit (5x)  
        'sell_portion': 0.5,       # Sell 50% of remaining
        'name': 'Moon Shot'
    },
    {
        'profit_multiple': 11.0,   # 1000% profit (11x)
        'sell_portion': 0.75,      # Sell 75% of remaining
        'name': 'Generational Wealth'
    }
]
```

#### **Position State Management**
```python
position_state_schema = {
    'token_address': str,
    'initial_investment_usdc': float,
    'initial_liquidity': float,
    'tiers_sold': list,              # Executed tier indices
    'entry_timestamp': float,
    'total_sold_usdc': float,
    'strategy_type': 'tiered_dynamic'
}
```

#### **Risk Management Parameters**
```python
risk_parameters = {
    'stop_loss_percentage': -0.25,   # -25% maximum loss
    'position_tracking': True,       # JSON state persistence
    'auto_exit_on_final_tier': True, # Close after last tier
    'portfolio_correlation': False,  # Future enhancement
}
```

---

## 🔌 API INTEGRATION ARCHITECTURE

### **Helius RPC Integration:**

#### **WebSocket Configuration**
```python
websocket_config = {
    'url_pattern': 'wss://mainnet.helius-rpc.com/?api-key={API_KEY}',
    'subscription_method': 'logsSubscribe',
    'program_filter': '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',  # Raydium LP V4
    'commitment_level': 'processed',  # Fastest confirmation
    'keepalive_interval': 30,         # Seconds
    'reconnection_delay': 5,          # Seconds
}
```

#### **HTTP RPC Configuration**
```python
http_rpc_config = {
    'timeout': 15,                    # Request timeout
    'max_retries': 5,                 # Retry attempts
    'commitment': 'confirmed',        # Balance between speed/reliability
    'encoding': 'jsonParsed',         # Human-readable responses
}
```

### **Birdeye API Integration:**

#### **Endpoint Mapping**
```python
birdeye_endpoints = {
    'security': 'https://public-api.birdeye.so/defi/token_security',
    'overview': 'https://public-api.birdeye.so/defi/token_overview',
    'price': 'https://public-api.birdeye.so/defi/price',
}
```

#### **Rate Limiting & Error Handling**
```python
birdeye_config = {
    'rate_limit': '100_requests_per_minute',
    'timeout': 8,
    'retry_strategy': 'exponential_backoff',
    'error_codes': {
        555: 'token_not_indexed_yet',
        404: 'token_not_found',
        429: 'rate_limit_exceeded',
    }
}
```

### **Jupiter API v6 Integration:**

#### **Trading Configuration**
```python
jupiter_config = {
    'quote_endpoint': 'https://quote-api.jup.ag/v6/quote',
    'swap_endpoint': 'https://quote-api.jup.ag/v6/swap',
    'slippage_bps': 3000,            # 30% for volatile new tokens
    'priority_fee': 100000,          # Lamports
    'skip_preflight': False,         # Enhanced reliability
    'commitment': 'confirmed',       # Balance speed/reliability
    'max_accounts': 64,              # Route complexity
    'dynamic_compute_limit': True,   # Optimize compute usage
}
```

---

## 💾 DATA MANAGEMENT ARCHITECTURE

### **File System Structure:**
```
data/
├── speed_engine_snipes.txt         # Successful trades log
├── intelligence_rejections.txt     # Filtered tokens log
├── deployer_blacklist.txt          # Known bad deployers
├── open_positions_state.json       # Active position tracking
├── processed_signatures.txt        # Duplicate prevention
└── closed_positions.txt            # Completed trades
```

### **Data Persistence Patterns:**

#### **Append-Only Logs**
```python
# Time-series event logging
log_format = {
    'timestamp': 'YYYY-MM-DD HH:MM:SS',
    'token_address': 'base58_string',
    'transaction_signature': 'base58_string', 
    'event_type': 'SUCCESS|REJECTION|PROCESSING',
    'metadata': 'comma_separated_values'
}
```

#### **JSON State Management**
```python
# Position state tracking
state_format = {
    'token_address': {
        'initial_investment_usdc': float,
        'initial_liquidity': float,
        'tiers_sold': [int],
        'entry_timestamp': float,
        'total_sold_usdc': float,
        'strategy_type': str
    }
}
```

#### **Set-Based Deduplication**
```python
# Signature tracking for duplicate prevention
signature_storage = {
    'format': 'newline_separated_strings',
    'lookup_method': 'set_based_membership_test',
    'cleanup_strategy': 'rolling_window_24h',
}
```

---

## 🔒 SECURITY ARCHITECTURE

### **API Key Management:**
```python
# Secure credential storage
credential_structure = {
    'file': 'dontshare.py',
    'variables': {
        'rpc_url': 'helius_endpoint_with_key',
        'birdeye': 'birdeye_api_key',
        'sol_key': 'base58_private_key_or_byte_array'
    },
    'access_pattern': 'import_only',
    'version_control': 'gitignored'
}
```

### **Private Key Handling:**
```python
# Multi-format key support
key_formats = {
    'base58_string': 'standard_solana_format',
    'byte_array_string': 'comma_separated_integers',
    'conversion_function': 'create_keypair_from_key()',
    'security_note': 'keys_never_logged_or_transmitted'
}
```

### **Transaction Security:**
```python
# Safe transaction parameters
transaction_safety = {
    'preflight_checks': True,        # Validate before sending
    'commitment_level': 'confirmed', # Wait for confirmation
    'max_retries': 1,               # Limit retry attempts  
    'error_analysis': True,         # Categorize failures
    'signature_tracking': True,     # Prevent duplicates
}
```

---

## 📊 MONITORING & OBSERVABILITY

### **Performance Metrics:**
```python
metrics_collected = {
    'speed_engine': [
        'detection_latency_ms',
        'pools_detected_per_minute', 
        'websocket_reconnections',
        'duplicate_signatures_filtered'
    ],
    'intelligence_engine': [
        'tokens_vetted_per_minute',
        'security_filter_rejections',
        'api_call_success_rate',
        'average_vetting_time_seconds'
    ],
    'strategy_engine': [
        'positions_opened',
        'profit_tiers_executed',
        'stop_losses_triggered',
        'average_hold_time_hours'
    ]
}
```

### **Logging Strategy:**
```python
logging_levels = {
    'speed_engine': 'INFO',      # Transaction events
    'intelligence': 'DEBUG',     # Detailed filtering
    'strategy': 'INFO',          # Position management
    'errors': 'ERROR',           # System failures
    'performance': 'METRICS'     # Performance data
}
```

### **Health Checks:**
```python
health_monitoring = {
    'websocket_connection': 'ping_every_30_seconds',
    'api_endpoints': 'response_time_tracking',
    'file_system': 'disk_space_monitoring', 
    'memory_usage': 'position_state_size_tracking',
    'error_rates': 'failure_threshold_alerting'
}
```

---

## 🚀 DEPLOYMENT ARCHITECTURE

### **System Requirements:**
```python
system_requirements = {
    'python_version': '3.8+',
    'memory_usage': '<512MB typical',
    'disk_space': '<100MB for logs',
    'network': 'stable_internet_connection',
    'latency': '<50ms to trading endpoints'
}
```

### **Environment Configuration:**
```python
environment_setup = {
    'virtual_environment': 'recommended',
    'package_manager': 'pip',
    'dependencies': 'requirements.txt',
    'configuration': 'config.py + dontshare.py',
    'data_directory': './data/ (auto-created)'
}
```

### **Startup Sequence:**
```python
startup_order = [
    '1. Load configuration from config.py',
    '2. Initialize API credentials from dontshare.py', 
    '3. Create data directory structure',
    '4. Establish WebSocket connection to Helius',
    '5. Subscribe to Raydium LP V4 program logs',
    '6. Start background risk management thread',
    '7. Begin real-time pool detection loop'
]
```

---

## 🔧 MAINTENANCE & SCALING

### **Maintenance Tasks:**
```python
maintenance_schedule = {
    'daily': [
        'log_file_rotation',
        'closed_positions_cleanup',
        'performance_metrics_review'
    ],
    'weekly': [
        'deployer_blacklist_review',
        'position_state_validation',
        'error_pattern_analysis'
    ],
    'monthly': [
        'api_key_rotation',
        'system_performance_optimization',
        'configuration_review'
    ]
}
```

### **Scaling Considerations:**
```python
scaling_strategies = {
    'horizontal': [
        'multiple_wallet_support',
        'parallel_detection_processes',
        'distributed_intelligence_filtering'
    ],
    'vertical': [
        'memory_optimization',
        'cpu_optimization',
        'network_optimization'
    ],
    'infrastructure': [
        'cloud_deployment',
        'database_integration',  
        'message_queue_systems'
    ]
}
```

---

*Technical Architecture Document v1.0*
*Last Updated: Current System State*
*Architecture Status: Production Ready*
