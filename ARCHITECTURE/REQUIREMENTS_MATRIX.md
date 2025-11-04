# Requirements and Capabilities Matrix

**Document Version:** 1.0
**Date:** November 4, 2025
**Status:** Comprehensive component requirements and feature roadmap

## Overview

This matrix provides visibility into what each component requires (inputs, parameters, dependencies) and what features are being built (Futures), organized by the 8-step request processing pipeline. This document directly addresses the gap between "what's needed to run this component" and "what's planned for the future."

For each component, you'll find:
- **Current Capabilities**: What works now in production/testing
- **Required Inputs**: What this component needs from the previous step
- **Input Parameters**: Configuration and runtime parameters required
- **Output Specifications**: What this component produces for the next step
- **Futures/Features**: What's being built and when it's needed
- **Prerequisites for Futures**: What must be completed first
- **Use Cases**: How to test and verify functionality
- **Dependencies**: What other components must be ready

---

## 1. DNS Network Layer (Step 1)

### Component: Scalable Relay - DNS Module

**Current Implementation Status:** 35% complete (interface-driven, partial stubs)
**Location:** `internal/dns/*`, `internal/config/dns_config.go`

### Current Capabilities

- GeoDNS service discovery with round-robin load balancing
- 3 edge PoPs (Moscow, Frankfurt, Amsterdam)
- Kubernetes-native service discovery integration
- Multi-tenant DNS record isolation
- DNS caching with Redis

### Required Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| Client DNS Query | DNS Query Packet (RFC 1035) | Client | Yes |
| Client IP Address | IPv4/IPv6 | DNS Query Header | Yes |
| Tenant Context | String (UUID) | Query tag or reverse lookup | No |
| Query Type | QTYPE (A, AAAA, CNAME) | DNS Question Section | Yes |
| Query Class | QCLASS (IN) | DNS Question Section | Yes |

### Input Parameters (Configuration)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `dns.enabled` | bool | `true` | Enable DNS module |
| `dns.listen_port` | int | `53` | UDP port for DNS |
| `dns.cache_ttl_seconds` | int | `300` | Cache TTL (5 minutes) |
| `dns.max_cache_entries` | int | `100000` | Redis memory limit |
| `dns.resolver_timeout_ms` | int | `1000` | Upstream resolution timeout |
| `dns.geo_distribution` | map | See below | PoP mapping |
| `dns.enable_dnssec` | bool | `false` | DNSSEC validation (Future) |
| `dns.redis_sentinel_nodes` | list | `[]` | Redis Sentinel endpoints |

**GeoDNS Distribution (Current):**
```
Moscow (AS64512):      Priority 1
Frankfurt (AS64512):   Priority 2
Amsterdam (AS64512):   Priority 3
```

### Output Specifications

| Output | Type | Format | Consumed By |
|--------|------|--------|-------------|
| DNS Resolution Result | DNS Response Packet (RFC 1035) | A/AAAA Records | Client |
| Resolved IP Address | IPv4 or IPv6 | String (CIDR notation) | Next: Control Plane |
| PoP Assignment | String (location code) | "moscow" \| "frankfurt" \| "amsterdam" | Next: Control Plane |
| Response Time | Duration | Milliseconds | Monitoring (Step 5) |
| TTL | Integer | Seconds (300-3600) | Client DNS cache |

**Example Output:**
```dns
Query: relay.cloudbridge.io A
Response:
  - 141.98.xxx.xxx (Moscow PoP)
  - 89.32.xxx.xxx (Frankfurt PoP)
  - 78.46.xxx.xxx (Amsterdam PoP)
TTL: 300
```

### Futures/Features Being Built

| Future Feature | Status | Target Completion | Priority | Why Needed |
|---|---|---|---|---|
| DNSSEC Validation | Planned | Q4 2025 | Medium | DNS spoofing protection for geo-routing |
| Anycast DNS (1.1.1.1-like) | Designed | Q1 2026 | High | Reduce DNS query latency globally |
| DNS Query Analytics | In Design | Q4 2025 | Medium | Traffic pattern understanding for ML |
| Geographic Weighted Distribution | Planned | Q1 2026 | Medium | Dynamic PoP assignment based on latency |
| DNS Failover (Health-based) | Stub | Q4 2025 | High | Automatic PoP exclusion if down |
| EDNS(0) Client Subnet (ECS) | Planned | Q1 2026 | Low | GeoIP-accurate DNS from CDNs |

### Prerequisites for Futures

| Future | Blocking Prerequisites | Status |
|--------|---|---|
| **DNSSEC Validation** | DNSSEC key management system | Not started |
| | DNSSEC trust chain verification | Not started |
| **Anycast DNS** | BGP Anycast routing setup (AS64512) | Ready (BGP configured) |
| | DNS server clustering | Partially ready (needs scaling) |
| **DNS Query Analytics** | Metrics collection pipeline (Step 5) | Ready - Prometheus in place |
| | Query logging infrastructure | Stub - needs implementation |
| **Weighted Distribution** | Latency measurement system | Stub - needs implementation |
| | Dynamic config updates | Ready - Cadence workflows available |
| **DNS Failover** | Health check system for PoPs | Stub - needs `internal/health/` |
| | DNS record update mechanism | Partial - needs automation |
| **ECS Support** | MaxMind GeoIP2 database integration | Not started |
| | ECS response caching | Not started |

### Use Cases / Testing Scenarios

**Use Case 1: Standard DNS Resolution**
```
Test: Basic A record resolution
Input:  nslookup relay.cloudbridge.io
Expected Output:
  - Returns 3 A records (Moscow, Frankfurt, Amsterdam)
  - Response time < 1ms (local cache) or < 100ms (upstream)
  - TTL = 300 seconds
Verification: dig relay.cloudbridge.io +short
```

**Use Case 2: Multi-Tenant Isolation**
```
Test: Tenant-specific DNS records
Input:  tenant1.relay.cloudbridge.io from Customer A
Expected Output:
  - Returns only Customer A's PoP IPs
  - Does NOT return Customer B's PoP IPs
  - Uses Customer A's cache entry
Verification: Query cross-tenant record, confirm isolation
```

**Use Case 3: PoP Failover (Future)**
```
Test: Moscow PoP down, should use Frankfurt
Input:  relay.cloudbridge.io query (Moscow marked down by health check)
Expected Output:
  - Returns only Frankfurt and Amsterdam
  - Client retries automatically
  - Traffic redistributed to remaining PoPs
Verification: Kill Moscow server, query DNS, check response
```

**Use Case 4: Cache Performance**
```
Test: Repeated queries use cache
Input:  Multiple identical queries within 5 minutes
Expected Output:
  - First query: 50-100ms (upstream resolution)
  - Subsequent queries: <1ms (Redis cache hit)
  - Cache hit rate > 95% under normal load
Verification: Redis INFO stats, response time monitoring
```

**Use Case 5: DNSSEC Validation (Future)**
```
Test: Detect spoofed DNS responses
Input:  DNSSEC-signed query, attacker tries to inject fake response
Expected Output:
  - DNSSEC validation fails
  - Query returns SERVFAIL
  - Invalid response rejected
Verification: Send forged DNS packet with bad signature, confirm rejection
```

### Dependencies

| Component | Required By | Status | Impact if Missing |
|-----------|---|---|---|
| Control Plane (Step 2) | Credential validation | Ready | Control Plane can't issue credentials |
| Redis Sentinel | DNS caching | Ready | Cache disabled, 100ms query times |
| BGP Routing (AS64512) | Anycast DNS (Future) | Ready | Can't deploy Anycast DNS |
| Prometheus Metrics | Analytics (Future) | Ready | Can collect metrics when ready |
| Cadence Workflows | Dynamic config (Future) | Ready | Can automate config updates when ready |
| Health Check System | Failover (Future) | **STUB** | Failover feature blocked |

### Notes

- Current DNS module is **geolocation-aware** but uses static PoP mapping
- No health checks on PoPs yet (marked as Stub in internal/health/)
- Redis caching provides 1000x speedup for repeated queries
- DNSSEC and Anycast are **locked** until BGP Anycast infrastructure is confirmed ready

---

## 2. Control Plane - Credentials & Validation (Step 2)

### Component: Control Plane - Zitadel OIDC Integration

**Current Implementation Status:** 75% complete
**Location:** `internal/auth/*`, `internal/config/zitadel_config.go`

### Current Capabilities

- OIDC/OAuth2 authentication with Zitadel identity provider
- JWT token generation and validation
- Service account support with JWT profile authentication
- Keycloak compatibility layer (enhanced auth interface)
- Multi-tenant credential isolation
- Token caching with Redis

### Required Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| DNS Resolution Result | IPv4/IPv6 address + PoP ID | Step 1: DNS | Yes |
| Client Credentials | Client ID + Secret | Client environment | Yes |
| Tenant Context | UUID | Client config or JWT sub claim | Yes |
| Request Metadata | User-Agent, IP, Headers | HTTP request | No |
| Scope Requirements | String list (space-separated) | Client app configuration | No |

### Input Parameters (Configuration)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `auth.zitadel_enabled` | bool | `true` | Enable Zitadel auth |
| `auth.zitadel_domain` | string | `zitadel.2gc.io` | Zitadel instance domain |
| `auth.zitadel_client_id` | string | `""` | OIDC client ID |
| `auth.zitadel_client_secret` | string | `""` | OIDC client secret (ENV var) |
| `auth.token_cache_ttl_seconds` | int | `3600` | JWT token cache TTL |
| `auth.jwks_refresh_interval_minutes` | int | `60` | JWKS key refresh interval |
| `auth.enable_mfa` | bool | `false` | Require MFA (Future) |
| `auth.max_token_age_seconds` | int | `86400` | Token expiry (24 hours) |
| `auth.redis_sentinel_nodes` | list | `[]` | Redis Sentinel for token cache |

**Zitadel Configuration (Current):**
```yaml
zitadel_domain: zitadel.2gc.io
oidc_endpoint: https://zitadel.2gc.io/oauth/v2
jwks_endpoint: https://zitadel.2gc.io/oauth/v2/keys
scopes: [openid, profile, email, custom:tenant_id]
```

### Output Specifications

| Output | Type | Format | Consumed By |
|--------|------|--------|-------------|
| JWT Token | Signed JWT | Header.Payload.Signature (base64) | All subsequent steps |
| Token Claims | JSON Object | Standard OIDC claims + custom | Authorization decisions |
| Tenant ID | UUID | claim: `custom:tenant_id` | Isolation (all components) |
| Subject (sub) | String | User ID in Zitadel | Audit logging |
| Response Time | Duration | Milliseconds | Monitoring (Step 5) |
| Validation Status | Boolean | true/false/error | Next: DDoS Protection |

**Example JWT Token Claims:**
```json
{
  "iss": "https://zitadel.2gc.io/",
  "sub": "user123@example.com",
  "aud": "cloudbridge-relay",
  "iat": 1704283200,
  "exp": 1704369600,
  "custom:tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "custom:roles": ["relay-user", "monitoring-read"],
  "email": "user@example.com"
}
```

### Futures/Features Being Built

| Future Feature | Status | Target Completion | Priority | Why Needed |
|---|---|---|---|---|
| MFA (Multi-Factor Auth) | Designed | Q4 2025 | High | Enterprise security requirement |
| PAT (Personal Access Tokens) | Testing | Q4 2025 | Medium | Service-to-service authentication |
| RBAC/ABAC Policies | In Design | Q1 2026 | High | Fine-grained access control |
| Token Refresh Mechanism | Stub | Q4 2025 | High | Seamless token renewal |
| Credential Rotation | Planned | Q1 2026 | Medium | Security best practices |
| SAML Support | Backlog | Q2 2026 | Low | Enterprise customer requirement |
| Device Grant Flow | Planned | Q1 2026 | Low | IoT/device authentication |
| Conditional Access | Designed | Q1 2026 | Medium | Risk-based authentication |

### Prerequisites for Futures

| Future | Blocking Prerequisites | Status |
|--------|---|---|
| **MFA** | Phone/email verification service | Not started |
| | Time-based OTP (TOTP) implementation | Not started |
| | Zitadel MFA configuration | Not started |
| **PAT (Service Tokens)** | PAT generation API in Zitadel | Ready (Zitadel v2.44+) |
| | PAT validation in RelayManager | Partial - needs `internal/p2p/` completion |
| | Audit logging for PAT usage | Needs implementation |
| **RBAC/ABAC** | Policy engine (Casbin/OPA) | Designed, not implemented |
| | Role mapping service | Partial - needs completion |
| | Permission cache system | Ready - Redis available |
| **Token Refresh** | Refresh token storage | Partial - Redis ready |
| | Refresh token rotation logic | Not implemented |
| | Graceful token expiry handling | Partial |
| **Credential Rotation** | Secret vault integration | Not started |
| | Automated rotation scheduler | Not started |
| | Zero-downtime rotation mechanism | Designed, not implemented |
| **SAML Support** | SAML metadata parser | Not started |
| | SAML assertion validator | Not started |
| | XML signature verification | Not started |

### Use Cases / Testing Scenarios

**Use Case 1: Basic JWT Issuance**
```
Test: Client requests token with valid credentials
Input:
  POST /oauth/v2/token
  client_id=cloudbridge-relay
  client_secret=xxx
  grant_type=client_credentials
  scope=openid profile custom:tenant_id

Expected Output:
  - JWT token with all claims
  - custom:tenant_id populated
  - exp = iat + 86400 (24 hours)
  - iss = https://zitadel.2gc.io/

Verification: jwt.io decode token, verify claims, check signature
```

**Use Case 2: Token Validation in DDoS Check**
```
Test: JWT validation before DDoS processing
Input:  JWT token from Step 1, DDoS module validates it
Expected Output:
  - Token signature validated against JWKS
  - Token not expired (exp > now)
  - custom:tenant_id extracted
  - token passed to Step 3: DDoS Protection

Verification: Compare token exp timestamp with system time
```

**Use Case 3: Multi-Tenant Isolation via Claims**
```
Test: Customer A's token only grants access to their tenant
Input:  Two clients: Customer A (tenant_id=UUID-A), Customer B (tenant_id=UUID-B)
Expected Output:
  - Customer A's token has custom:tenant_id=UUID-A
  - Customer B's token has custom:tenant_id=UUID-B
  - Each sees only their own data
  - Cross-tenant access denied

Verification: Query relay with Customer A's token for Customer B's data, confirm denial
```

**Use Case 4: Token Cache Performance**
```
Test: Repeated token validation uses cache
Input:  Same token validated multiple times within 1 hour
Expected Output:
  - First validation: 50-100ms (JWKS fetch + verify)
  - Subsequent validations: <5ms (Redis cache)
  - Cache hit rate > 95%

Verification: Time /oauth/v2/introspect calls, check Redis stats
```

**Use Case 5: Token Refresh (Future)**
```
Test: Token nearing expiry can be silently renewed
Input:  Token exp < now + 5 minutes (refresh window)
Expected Output:
  - Automatic refresh triggered
  - New token issued with fresh exp
  - Client transparently continues
  - Old token still valid during refresh window

Verification: Monitor token age, trigger refresh 5min before expiry
```

**Use Case 6: MFA Enforcement (Future)**
```
Test: User with MFA enabled must provide second factor
Input:  Client credentials + MFA challenge
Expected Output:
  - First request returns MFA challenge
  - Client provides TOTP/email code
  - Second request succeeds with MFA verified
  - Token contains mfa_verified: true claim

Verification: Enable MFA on test user, provide invalid code (fail), correct code (success)
```

### Dependencies

| Component | Required By | Status | Impact if Missing |
|-----------|---|---|---|
| Zitadel Instance | Token issuance | Ready | No authentication possible |
| Redis Sentinel | Token caching | Ready | Cache disabled, 100ms per validation |
| DNS (Step 1) | Client discovery | Ready | Can resolve Zitadel domain |
| DDoS Protection (Step 3) | Receives validated tokens | Ready | DDoS module can validate tokens |
| Relay (Step 4) | Uses tenant_id for isolation | Ready | No tenant separation |
| Monitoring (Step 5) | Logs auth events | Ready | Can collect metrics when configured |
| Policy Engine (Future RBAC) | Permission checks | **NOT STARTED** | Can't implement RBAC/ABAC until ready |

### Notes

- Current implementation has **75% completeness** - JWT generation and validation working
- **PAT (Personal Access Tokens)** status: Designed in Zitadel but not fully integrated with RelayManager
- **Token refresh** is stubbed - clients currently get single-use tokens without renewal
- **RBAC/ABAC** is designed but implementation is blocked until policy engine is selected (Casbin vs OPA)
- Token cache uses Redis Sentinel for HA - automatic failover configured

---

## 3. DDoS Protection Layer (Step 3)

### Component: DDoS Protection - ML + XDP/eBPF

**Current Implementation Status:** 20% complete (framework, Python stubs)
**Location:** `internal/ddos/*`, Python ML models in `ml/`

### Current Capabilities

- DDoS threat detection framework
- JWT token validation (receives from Step 2)
- ML model inference ready (framework in place)
- Attack pattern recognition (designed, partial implementation)
- Real-time traffic analysis capability
- XDP/eBPF kernel-space packet filtering (designed)

### Required Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| JWT Token | Signed JWT | Step 2: Control Plane | Yes |
| Tenant ID | UUID | JWT claim: custom:tenant_id | Yes |
| Request Metadata | IP, port, protocol, headers | Network packet metadata | Yes |
| Traffic Pattern | Packet stream | Network interface | Yes |
| Threat Rules | JSON rules | Control Plane policy push | Yes |

### Input Parameters (Configuration)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `ddos.enabled` | bool | `true` | Enable DDoS module |
| `ddos.ml_model_path` | string | `models/ddos/v1.pb` | TensorFlow model file |
| `ddos.inference_timeout_ms` | int | `100` | Max inference latency |
| `ddos.detection_threshold` | float | `0.85` | ML confidence threshold |
| `ddos.xdp_program_path` | string | `ebpf/ddos_filter.o` | XDP eBPF bytecode |
| `ddos.redis_sentinel_nodes` | list | `[]` | Redis for shared state |
| `ddos.block_duration_seconds` | int | `300` | IP block duration (5 min) |
| `ddos.enable_ml_learning` | bool | `false` | Continuous model improvement (Future) |
| `ddos.detection_mode` | string | `"block"` | "block", "alert", "test" |

**DDoS Detection Rules (Current):**
```
- Threshold: >10,000 RPS from single IP
- SYN flood detection: >1,000 SYN/sec
- UDP amplification: >5,000 pps
- HTTP slowloris: >100 slow connections
- Rate per tenant: configurable limits
```

### Output Specifications

| Output | Type | Format | Consumed By |
|--------|------|--------|-------------|
| Threat Detection Result | Boolean | Allow/Block decision | Step 4: Relay |
| Threat Score | Float | 0.0-1.0 confidence | Monitoring (Step 5) |
| Block Action | String | "allow" \| "block" \| "rate_limit" | Next step decision |
| Block Duration | Integer | Seconds | iptables/XDP rules |
| Threat Category | String | "ddos" \| "bot" \| "anomaly" \| "none" | Monitoring + Dashboard |
| Metrics | JSON | Request count, latency, threat count | Prometheus (Step 5) |

**Example Output:**
```json
{
  "allow": true,
  "threat_score": 0.12,
  "threat_category": "none",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_ip": "203.0.113.45",
  "decision_time_ms": 32,
  "applied_rules": ["rate_limit_tenant", "geo_whitelist"]
}
```

### Futures/Features Being Built

| Future Feature | Status | Target Completion | Priority | Why Needed |
|---|---|---|---|---|
| Real-time ML Model Updates | Designed | Q1 2026 | High | Detect new attack patterns |
| Botnet Detection | Framework | Q4 2025 | High | Identify bot traffic vs humans |
| Behavioral Anomaly Detection | Framework | Q1 2026 | Medium | Detect unusual usage patterns |
| Geo-IP Blocking | Stub | Q4 2025 | Medium | Block traffic from specific regions |
| Adaptive Rate Limiting | Designed | Q1 2026 | High | Per-customer dynamic thresholds |
| Layer 7 (HTTP) Attack Detection | Partial | Q4 2025 | High | Detect HTTP-specific attacks |
| Encrypted Traffic Analysis | Planned | Q2 2026 | Medium | Detect threats in encrypted flows |
| Predictive DDoS Detection | Research | Q2 2026 | Low | Block attacks before they start |

### Prerequisites for Futures

| Future | Blocking Prerequisites | Status |
|--------|---|---|
| **Real-time ML Updates** | Model training pipeline | Stub - needs `internal/ml/training/` |
| | New attack sample collection | Partial - needs data labeling workflow |
| | Model versioning system | Not started |
| | Zero-downtime model replacement | Designed, not implemented |
| **Botnet Detection** | Bot behavior dataset | Not started |
| | Bot fingerprint models | Framework ready |
| | Browser automation detection | Partial - needs JavaScript challenge |
| **Anomaly Detection** | Baseline establishment (30 days) | Not started |
| | Time-series analysis (Prophet/ARIMA) | Framework ready |
| | Tenant-specific baselines | Needs per-tenant learning |
| **Geo-IP Blocking** | MaxMind GeoIP2 integration | Not started |
| | Geo rules database | Not started |
| | Geo policy enforcement | Designed, not implemented |
| **Adaptive Rate Limiting** | Tenant usage history (90+ days) | Partial - metrics needed |
| | Dynamic threshold calculation | Designed, not implemented |
| | Per-endpoint rate limits | Needs configuration schema |
| **Layer 7 Detection** | HTTP request parser | Partial - Go libraries available |
| | Signature database | Not started |
| | Payload analysis models | Framework ready |
| **Encrypted Analysis** | TLS interception (mTLS) | Security review needed |
| | Encrypted fingerprinting | Research phase |
| **Predictive Detection** | Historical attack timeline | Needs data warehouse |
| | LSTM/Time-series models | Framework ready |

### Use Cases / Testing Scenarios

**Use Case 1: Clean Traffic - Allow Decision**
```
Test: Legitimate request passes DDoS check
Input:
  - Valid JWT token
  - Single request from IP 203.0.113.45
  - Normal HTTP headers
  - Request rate < 100 RPS

Expected Output:
  - allow: true
  - threat_score: 0.05 (very low)
  - threat_category: "none"
  - decision_time: <50ms
  - Request forwarded to Step 4: Relay

Verification: Monitor request flow-through, check threat scores in Prometheus
```

**Use Case 2: Volumetric DDoS - Block Decision**
```
Test: Detect volumetric attack
Input:
  - Incoming traffic: 500,000 RPS
  - Source: Multiple IPs (botnet pattern)
  - JWT tokens invalid or missing
  - SYN flood ratio > 90%

Expected Output:
  - allow: false
  - threat_score: 0.98 (very high)
  - threat_category: "ddos"
  - decision_time: <100ms
  - Block rule applied: "volumetric_ddos" (block 300 sec)

Verification: Traffic drops dramatically, attack source IPs added to block list
```

**Use Case 3: Rate Limiting - Gradual Throttle**
```
Test: Customer exceeds their rate limit
Input:
  - Valid JWT token, tenant_id=UUID-A
  - Request rate: 15,000 RPS (limit is 10,000 RPS)
  - Attack ratio: <5% (looks legitimate)

Expected Output:
  - allow: true (but rate-limited)
  - threat_score: 0.35 (moderate)
  - threat_category: "none" (not an attack, just over-limit)
  - decision_time: <50ms
  - Applied rules: ["rate_limit_tenant", "backpressure"]
  - New SYN cookies enabled
  - Response times increase (queue building)

Verification: Monitor response time increase, check rate limiter queue depth
```

**Use Case 4: Anomaly Detection (Future)**
```
Test: Unusual traffic pattern detected
Input:
  - Traffic pattern deviates from baseline
  - Example: Customer A usually gets 1,000 RPS, now gets 50,000 RPS
  - ML model trained on 30 days of baseline

Expected Output:
  - allow: false (anomaly too extreme)
  - threat_score: 0.72 (high)
  - threat_category: "anomaly"
  - decision_time: <100ms
  - Alert: "Anomalous spike detected, manual review required"

Verification: Check anomaly model output, verify against historical baseline
```

**Use Case 5: Geo-IP Blocking (Future)**
```
Test: Block traffic from sanctioned countries
Input:
  - Request from IP in Iran (sanctioned region)
  - Policy: block_countries = ["IR", "KP", "SY"]
  - Valid JWT token otherwise

Expected Output:
  - allow: false
  - threat_score: 0.0 (not a threat, just policy)
  - threat_category: "geo_blocked"
  - decision_time: <10ms
  - Reason: "Traffic source in blocked country"

Verification: Query GeoIP database, confirm country code matches policy
```

### Dependencies

| Component | Required By | Status | Impact if Missing |
|-----------|---|---|---|
| Control Plane (Step 2) | JWT validation | Ready | DDoS can't validate tokens |
| Redis Sentinel | Block list storage | Ready | In-memory block list only (no cluster sharing) |
| Relay (Step 4) | Sends allow/block decision | Ready | Can reject traffic if needed |
| Monitoring (Step 5) | Receives threat scores | Ready | Can create dashboards when ML ready |
| ML Training Pipeline | Real-time model updates (Future) | **STUB** | Blocks real-time learning feature |
| Prometheus | Metrics collection | Ready | Can collect stats when integrated |
| MaxMind GeoIP2 | Geo-blocking (Future) | Not started | Blocks geo feature |

### Notes

- Current **20% completeness** means framework is ready but ML models are stubs
- **Detection threshold** (0.85) is conservative - tunes false positive vs false negative ratio
- **XDP/eBPF kernel filtering** designed but not integrated with Go userspace yet
- **Real-time model updates** is blocked until model training pipeline is built
- Anomaly detection needs **30 days of baseline data** before it can detect anomalies (cold-start problem)

---

## 4. Scalable Relay - Data Transmission (Step 4)

### Component: Scalable Relay - QUIC + BBRv3 + P2P

**Current Implementation Status:** 35% complete (interface-driven, stubs)
**Location:** `internal/relay/*`, `internal/quic/*`, `internal/p2p/*`, `cmd/relay/`

### Current Capabilities

- QUIC protocol (RFC 9000) with 0-RTT resumption support
- BBRv3 congestion control (50% jitter reduction, 5.79× bufferbloat improvement)
- Multi-tenant peer isolation (Calico VRF-based)
- TLS 1.3 with mTLS for peer authentication
- NAT traversal with TURN server integration
- TCP/UDP forwarding (framework, stubs)

### Required Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| DDoS Allow Decision | Boolean | Step 3: DDoS | Yes |
| JWT Token | Signed JWT | Step 2: Control Plane | Yes |
| Tenant ID | UUID | JWT claim: custom:tenant_id | Yes |
| Client Data | Byte stream | Client (TCP/UDP/HTTP) | Yes |
| PoP Assignment | String | Step 1: DNS | Yes |
| Peer List | List of Peer objects | P2P network discovery | No |

### Input Parameters (Configuration)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `relay.enabled` | bool | `true` | Enable relay |
| `relay.listen_port` | int | `4433` | QUIC listen port |
| `relay.quic_initial_rtt_ms` | int | `100` | Initial RTT estimate |
| `relay.bbr_enabled` | bool | `true` | Use BBRv3 congestion control |
| `relay.cca` | string | `"bbrv3"` | Congestion control algorithm |
| `relay.max_idle_timeout_ms` | int | `30000` | Connection idle timeout |
| `relay.max_streams` | int | `1000` | Concurrent streams per conn |
| `relay.buffer_size` | int | `2097152` | 2MB send/recv buffers |
| `relay.enable_0rtt` | bool | `true` | Allow 0-RTT resumption |
| `relay.p2p_heartbeat_interval_sec` | int | `30` | Peer keepalive interval |
| `relay.wireguard_enabled` | bool | `false` | Enable WireGuard tunnel (Future) |
| `relay.mtu` | int | `1200` | Payload size (QUIC packet) |

**BBRv3 Configuration (Current):**
```yaml
bbr:
  probe_rtt_ms: 200        # Minimum RTT probing
  drain_window: 0.35       # Drain phase duration ratio
  startup_growth_rate: 2.0 # Startup phase CWND growth
  pacing_gain: 1.25        # Pacing gain (BBRv3)
  cwnd_gain: 2.0           # CWND gain for full pipe
```

### Output Specifications

| Output | Type | Format | Consumed By |
|--------|------|--------|-------------|
| Transmitted Data | Byte stream | QUIC packets (RFC 9000) | Peer Relay / Client |
| Transmission Status | Boolean | success/failure | Step 5: Monitoring |
| Latency | Integer | Milliseconds (measured) | Dashboard + AI (Step 6-8) |
| Throughput | Integer | Mbps (measured) | Dashboard |
| Jitter | Float | Milliseconds std dev | Dashboard + AI tuning |
| Packet Loss | Float | Percentage (0-100) | Dashboard |
| Congestion Signal | String | "normal" \| "congested" \| "probing" | Monitoring |
| Peer Status | String | "connected" \| "dropped" \| "reconnecting" | P2P coordination |

**Example Output Metrics:**
```json
{
  "status": "success",
  "latency_ms": 45.2,
  "throughput_mbps": 450.5,
  "jitter_ms": 0.12,
  "packet_loss_pct": 0.001,
  "bbr_state": "startup",
  "congestion_window": 45000,
  "bytes_sent": 1048576,
  "rtt_ms": 48.5
}
```

### Futures/Features Being Built

| Future Feature | Status | Target Completion | Priority | Why Needed |
|---|---|---|---|---|
| WireGuard Tunnel Integration | Designed | Q4 2025 | High | Encrypted P2P mesh |
| TCP to QUIC Protocol Conversion | Stub | Q4 2025 | High | Support legacy TCP clients |
| Tunnel Manager | Stub | Q4 2025 | High | Manage encrypted tunnels |
| Connection Pooling | Designed | Q1 2026 | Medium | Reduce connection overhead |
| Packet Pacing Refinements | Partial | Q4 2025 | Medium | Reduce buffer bloat further |
| Load Balancing (IPVS) | Planned | Q1 2026 | High | Distribute load across relays |
| Circuit Breaker Pattern | Designed | Q4 2025 | Medium | Fail gracefully under overload |
| Connection Migration | Partial | Q4 2025 | Medium | Client mobility support |

### Prerequisites for Futures

| Future | Blocking Prerequisites | Status |
|--------|---|---|
| **WireGuard Integration** | WireGuard kernel module setup | Ready (Linux) |
| | WireGuard Go library bindings | Ready (wireguard-go) |
| | Tunnel configuration management | Stub - `internal/wireguard/` |
| | Key exchange mechanism | Designed, needs implementation |
| **TCP→QUIC Conversion** | TCP socket listener | Stub - `internal/tcp/` |
| | QUIC stream multiplexing | Ready (quic-go) |
| | Protocol adaptation layer | Not implemented |
| **Tunnel Manager** | TunnelManager interface | Stub - `internal/tunnel/` |
| | Tunnel lifecycle management | Not implemented |
| | Encryption key management | Partial |
| **Connection Pooling** | Connection state tracking | Stub - `internal/pool/` |
| | Idle connection reuse logic | Not implemented |
| | Connection health monitoring | Partial |
| **Packet Pacing** | RTT measurement system | Ready (QUIC provides RTT) |
| | Pacing calculator refinement | Designed, needs tuning |
| | Feedback loop from packets | Partial |
| **Load Balancing (IPVS)** | IPVS kernel module | Ready (Linux) |
| | Health check integration | Stub - `internal/health/` |
| | Load distribution algorithm | Designed |
| **Circuit Breaker** | Error rate monitoring | Ready (Prometheus) |
| | Threshold configuration | Not implemented |
| | Recovery strategy | Designed |
| **Connection Migration** | QUIC migration support | Ready (quic-go v0.33+) |
| | Path validation | Designed, needs integration |
| | Connection ID mapping | Partial |

### Use Cases / Testing Scenarios

**Use Case 1: Basic QUIC Connection**
```
Test: Client connects via QUIC and sends data
Input:
  - Client connects to relay:4433
  - Valid JWT token
  - 1MB test data
  - DDoS check passed

Expected Output:
  - Connection established in <50ms (with 0-RTT resume)
  - Data transmitted over QUIC
  - Latency: 45-55ms (depending on PoP)
  - Throughput: >400 Mbps
  - Jitter: <1ms
  - Packet loss: <0.01%

Verification: Monitor packet capture, verify QUIC handshake, check metrics
```

**Use Case 2: BBRv3 Congestion Control**
```
Test: BBRv3 adapts to network congestion
Input:
  - Start with 500 Mbps available capacity
  - Network congestion increases (simulate packet loss to 5%)
  - Monitor congestion window (CWND) and pacing rate

Expected Output:
  - Phase 1 (Startup): CWND grows 2x each RTT
  - Phase 2 (Drain): CWND reduces back down
  - Phase 3 (Steady): CWND = fair_rate + pacing_gain
  - Under congestion: CWND reduced, packet loss decreases
  - Jitter improved by 50% vs BBRv2

Verification: tcpdump -i eth0, check RTT variance, measure actual jitter
```

**Use Case 3: Multi-Tenant Isolation via Calico**
```
Test: Customer A's traffic isolated from Customer B's
Input:
  - Customer A connects to relay (tenant_id=UUID-A)
  - Customer B connects to different relay PoP (tenant_id=UUID-B)
  - Network policy: A↔B traffic blocked via Calico VRF

Expected Output:
  - Customer A traffic uses VRF 1001
  - Customer B traffic uses VRF 1002
  - A cannot see or access B's traffic
  - Each has isolated throughput measurement
  - Each has isolated QoS settings

Verification: ip netns exec, check VRF assignment, verify routing table separation
```

**Use Case 4: 0-RTT Resume (Connection Cache)**
```
Test: Repeated connections reuse session key
Input:
  - First connection: Full TLS handshake
  - Client closes connection (graceful)
  - Client reconnects within 30 seconds
  - Same session key available

Expected Output:
  - First connection handshake: 100ms
  - Second connection (0-RTT): <5ms
  - 20x speed improvement
  - Data transmitted in first packet

Verification: Monitor handshake time, enable 0-RTT logging, measure connection setup
```

**Use Case 5: NAT Traversal with TURN**
```
Test: Client behind NAT/firewall connects successfully
Input:
  - Client behind symmetric NAT
  - Direct connection not possible
  - TURN server configured: turn.cloudbridge.io

Expected Output:
  - Connection fallback to TURN server
  - Data relayed through TURN
  - Latency increase: +20-50ms
  - Throughput maintained: >300 Mbps
  - Automatic discovery of TURN servers via ICE

Verification: Block outbound ports, verify TURN connection, monitor metrics
```

**Use Case 6: WireGuard Tunnel (Future)**
```
Test: Encrypted peer-to-peer tunnel between relays
Input:
  - Two relay PoPs: Moscow and Frankfurt
  - WireGuard tunnel established
  - Peer discovery: automatic via DNS

Expected Output:
  - Tunnel established in <5 seconds
  - End-to-end encryption (ChaCha20-Poly1305)
  - Throughput: >800 Mbps (tunnel overhead minimal)
  - Peer authentication via public keys
  - Automatic reconnection on network change

Verification: Monitor tunnel bandwidth, check WireGuard status, verify key rotation
```

### Dependencies

| Component | Required By | Status | Impact if Missing |
|-----------|---|---|---|
| DDoS Protection (Step 3) | Threat filtering | Ready | All traffic allowed (unsafe) |
| Control Plane (Step 2) | Tenant validation | Ready | Can't isolate tenants |
| DNS (Step 1) | PoP discovery | Ready | Manual PoP config only |
| Monitoring (Step 5) | Metrics collection | Partial | Limited observability |
| P2P Mesh (internal) | Peer discovery | Stub - `internal/p2p/` | Can't coordinate between relays |
| WireGuard (Future) | Encrypted tunnels | **NOT STARTED** | Blocks WireGuard feature |
| Tunnel Manager (Future) | Tunnel lifecycle | **STUB** | Blocks TCP→QUIC conversion |
| Health Check System (internal) | Peer health monitoring | **STUB** | Can't detect relay failures |

### Notes

- Current **35% completeness** means QUIC/BBRv3 framework is ready but actual data forwarding is stubbed
- **0-RTT optimization** is enabled and working (uses TLS 1.3 session resume)
- **Packet pacing** with BBRv3 is tuned for **26-35 pps** (packets per second) sweet spot to minimize bufferbloat
- **WireGuard integration** is blocked on `internal/wireguard/` module (not started)
- **TCP↔QUIC conversion** is blocked on `internal/tcp/` and protocol adaptation layer (not started)

---

## 5. Monitoring - Metrics Collection (Step 5)

### Component: Monitoring - Prometheus + Grafana

**Current Implementation Status:** 75% complete
**Location:** `internal/monitoring/*`, `deployments/prometheus/`, `deployments/grafana/`

### Current Capabilities

- Prometheus metrics collection (30+ metric types)
- Grafana dashboard visualization (8+ dashboards)
- Real-time alerting via Alertmanager
- Metrics retention: 15 days (configurable)
- Custom metric exposition (OpenMetrics format)
- Multi-tenant metric isolation

### Required Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| Response Time | Duration (ms) | Step 4: Relay | Yes |
| Threat Score | Float (0-1) | Step 3: DDoS | Yes |
| Throughput | Integer (Mbps) | Step 4: Relay | Yes |
| Jitter | Float (ms) | Step 4: Relay | No |
| Tenant ID | UUID | All steps | Yes |
| Token Validation Status | Boolean | Step 2: Control Plane | No |
| Error Messages | String | All components | No |
| System Metrics | CPU, Memory, Disk | Kubernetes nodes | Yes |

### Input Parameters (Configuration)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `monitoring.enabled` | bool | `true` | Enable Prometheus collection |
| `monitoring.scrape_interval_sec` | int | `15` | Prometheus scrape interval |
| `monitoring.retention_days` | int | `15` | Metrics retention (disk space) |
| `monitoring.metrics_port` | int | `9090` | Prometheus HTTP port |
| `monitoring.grafana_port` | int | `3000` | Grafana HTTP port |
| `monitoring.alertmanager_enabled` | bool | `true` | Enable alerting |
| `monitoring.alert_webhook_url` | string | `""` | Webhook for alerts (Slack, etc) |
| `monitoring.tenant_isolation` | bool | `true` | Separate metrics by tenant |
| `monitoring.enable_tracing` | bool | `false` | OpenTelemetry tracing (Future) |

**Metrics Currently Collected:**
```
- relay_throughput_mbps (gauge)
- relay_latency_ms (histogram)
- relay_jitter_ms (gauge)
- relay_packet_loss_pct (gauge)
- ddos_threat_score (histogram)
- ddos_blocked_requests_total (counter)
- auth_token_validations_total (counter)
- auth_cache_hits_total (counter)
- dns_query_latency_ms (histogram)
- connection_count (gauge)
- buffer_usage_pct (gauge)
- cpu_usage_pct (gauge)
- memory_usage_pct (gauge)
```

### Output Specifications

| Output | Type | Format | Consumed By |
|--------|------|--------|-------------|
| Metrics Data | Prometheus Time Series | Prometheus format (text) | Step 6: AI Service |
| Dashboard JSON | Grafana dashboards | Grafana JSON format | Dashboard (Step 8) |
| Alerts | Alert events | JSON webhooks | Alert handlers |
| SLO Status | Boolean | Pass/Fail per SLO | Dashboard |
| Audit Logs | JSON entries | 90-day retention | Compliance + Dashboard |

**Example Metrics Output:**
```
# HELP relay_latency_ms Relay transmission latency in milliseconds
# TYPE relay_latency_ms histogram
relay_latency_ms_bucket{le="10",tenant_id="550e..."} 45.0
relay_latency_ms_bucket{le="50",tenant_id="550e..."} 1200.0
relay_latency_ms_bucket{le="100",tenant_id="550e..."} 1450.0
relay_latency_ms_sum{tenant_id="550e..."} 62500.0
relay_latency_ms_count{tenant_id="550e..."} 1500.0
```

### Futures/Features Being Built

| Future Feature | Status | Target Completion | Priority | Why Needed |
|---|---|---|---|---|
| OpenTelemetry Distributed Tracing | Designed | Q4 2025 | High | End-to-end request tracing |
| Custom ML-Generated Alerts | Framework | Q1 2026 | High | Anomaly-based alerting |
| Metrics Query Language (PromQL) | Ready | Done | Done | Ad-hoc analysis |
| SLO Tracking & Burn Rate | Partial | Q4 2025 | High | Service reliability tracking |
| Long-term Metrics Archive | Designed | Q1 2026 | Medium | Data warehouse integration |
| Custom Metric Aggregation | Partial | Q4 2025 | Medium | Business KPI dashboards |
| Cost Attribution per Tenant | Planned | Q1 2026 | Medium | Billing data collection |
| Real-time Log Aggregation (ELK) | Designed | Q2 2026 | Medium | Centralized log searching |

### Prerequisites for Futures

| Future | Blocking Prerequisites | Status |
|--------|---|---|
| **OpenTelemetry Tracing** | Trace collector service | Not started |
| | Jaeger/Tempo backend | Not started |
| | Instrumentation in all components | Partial - needs completion |
| | Trace context propagation (W3C) | Not implemented |
| **ML-Generated Alerts** | ML model training (Step 6) | Framework ready |
| | Alert pattern detector | Needs implementation |
| | Historical anomaly dataset | Needs collection |
| **SLO Burn Rate** | SLO target definition | Partial - needs formalization |
| | Error budget calculation | Designed, not implemented |
| | Alert thresholds per SLO | Not defined |
| **Long-term Archive** | Data warehouse (BigQuery/Redshift) | Not started |
| | Metrics export pipeline | Designed, not implemented |
| | Cost-effective storage (S3/GCS) | Infrastructure ready |
| **Custom Aggregation** | Business KPI definitions | Not started |
| | Aggregation function library | Partial |
| | Dashboard template system | Partial |
| **Cost Attribution** | Resource tagging system | Partial - tenant tags ready |
| | Cost model definition | Not started |
| | Billing integration | Designed |
| **ELK Stack** | Elasticsearch cluster | Not started |
| | Logstash forwarders | Not started |
| | Kibana configuration | Not started |

### Use Cases / Testing Scenarios

**Use Case 1: Real-time Dashboard View**
```
Test: Monitor live traffic and system health
Input:  Grafana dashboard, auto-refresh every 5 seconds
Expected Output:
  - Latency histogram updated in real-time
  - Throughput gauge shows current Mbps
  - DDoS threat score visible
  - CPU/memory usage of relay nodes
  - Error rate of last hour

Verification: Open Grafana, verify metrics < 5s staleness
```

**Use Case 2: Alert on SLO Breach**
```
Test: System alerts when latency SLO breached
Input:
  - SLO target: P95 latency < 50ms
  - Actual P95 latency > 75ms for 5 minutes

Expected Output:
  - Alert rule triggered
  - Webhook sent to Slack/PagerDuty
  - Alert includes current metrics and graphs
  - On-call engineer notified

Verification: Check Alertmanager UI, confirm webhook delivery
```

**Use Case 3: Multi-tenant Metric Isolation**
```
Test: Customer A only sees their own metrics
Input:
  - Customer A logs into Grafana with tenant-scoped role
  - Customer A queries relay_throughput_mbps

Expected Output:
  - Only Customer A's metrics visible
  - Custom metrics filtered by tenant_id
  - Dashboard shows only their PoPs
  - Cannot access Customer B's data

Verification: Query Prometheus, verify tenant_id label filtering
```

**Use Case 4: Historical Trend Analysis**
```
Test: Analyze 7-day traffic pattern
Input:
  - Query: avg(relay_throughput_mbps) over 7 days
  - Granularity: 5-minute buckets

Expected Output:
  - 2016 data points (7 days × 24 hours × 12 buckets)
  - Graph shows weekly pattern
  - Peak hours identifiable (e.g., 8pm-11pm)
  - Capacity planning data available

Verification: Export data to CSV, plot in Excel, verify pattern matches business hours
```

**Use Case 5: OpenTelemetry Distributed Trace (Future)**
```
Test: Trace single request through entire system
Input:
  - Client request with trace_id = abc123
  - Trace spans collected from all 8 steps

Expected Output:
  - Trace graph: DNS (0-1ms) → Control (2-50ms) → DDoS (3-32ms) → Relay (4-45ms) → Monitoring (5-5ms)
  - Latency breakdown by component
  - Identify slowest component
  - Error traces included

Verification: Open Jaeger UI, search by trace_id, verify span hierarchy
```

### Dependencies

| Component | Required By | Status | Impact if Missing |
|-----------|---|---|---|
| DNS (Step 1) | Response time metrics | Ready | Can collect when ready |
| Control Plane (Step 2) | Auth validation metrics | Ready | Can collect when ready |
| DDoS (Step 3) | Threat score metrics | Ready | Can collect when ready |
| Relay (Step 4) | Latency/throughput metrics | Ready | Can collect when ready |
| Prometheus Server | Metrics storage | Ready (deployed) | No metrics history |
| Grafana | Visualization | Ready (deployed) | Can't visualize metrics |
| Alertmanager | Alert routing | Ready (configured) | Can't send alerts |
| OpenTelemetry Collector (Future) | Distributed tracing | **NOT STARTED** | Blocks tracing feature |

### Notes

- Current **75% completeness** means Prometheus/Grafana fully operational, missing distributed tracing
- **Metrics retention**: 15 days uses ~500GB disk for CloudBridge's typical 10,000 samples/sec throughput
- **SLO tracking** is partially done - metrics exist but error budget calculation not formalized
- **Tenant isolation**: Metrics properly labeled with `tenant_id` for per-customer views
- **OpenTelemetry**: Designed and ready to implement when tracing backend (Jaeger/Tempo) is deployed

---

## 6. AI Service - Traffic Analysis (Step 6)

### Component: AI Service - TensorFlow + PyTorch Models

**Current Implementation Status:** 20% complete (framework, model stubs)
**Location:** `ml/`, `internal/ai/`, Python microservice

### Current Capabilities

- ML inference framework ready (TensorFlow/PyTorch loaded)
- Traffic pattern classification capability
- Model versioning system (framework)
- Real-time inference (<100ms target)
- Multi-model inference pipeline
- GPU/TPU support (framework)

### Required Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| Metrics Data | Prometheus time series | Step 5: Monitoring | Yes |
| Historical Data | 7-30 days of metrics | Monitoring metrics DB | Yes |
| Network Trace Data | Packet metadata | Relay (PCAP logs) | No |
| Threat Scores | Float (0-1) | Step 3: DDoS | Yes |
| Tenant Configuration | JSON | Control Plane | No |
| Model Weights | TensorFlow .pb files | Model registry | Yes |

### Input Parameters (Configuration)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `ai.enabled` | bool | `true` | Enable AI service |
| `ai.inference_timeout_ms` | int | `100` | Max inference latency |
| `ai.model_path` | string | `models/ai/v1.pb` | TensorFlow model file |
| `ai.batch_size` | int | `32` | Batch size for inference |
| `ai.gpu_enabled` | bool | `true` | Use GPU if available |
| `ai.enable_training` | bool | `false` | Train models on new data (Future) |
| `ai.training_interval_hours` | int | `24` | Retrain frequency |
| `ai.min_training_samples` | int | `50000` | Min samples for training |
| `ai.model_confidence_threshold` | float | `0.75` | Prediction confidence threshold |

**ML Models Available:**
```
1. Traffic-Classification-v1.pb    (Classify: normal, bot, anomaly)
2. Capacity-Predictor-v1.pb        (Predict: peak hours, capacity needs)
3. Anomaly-Detector-v1.pb          (Detect: unusual patterns vs baseline)
4. Threat-Correlator-v1.pb         (Correlate: threats with infrastructure)
5. Optimization-Engine-v1.pb       (Recommend: tuning parameters)
```

### Output Specifications

| Output | Type | Format | Consumed By |
|--------|------|--------|-------------|
| Traffic Classification | String | "normal" \| "bot" \| "anomaly" | Dashboard + Control Plane |
| Confidence Score | Float | 0.0-1.0 | Dashboard |
| Optimization Recommendations | JSON | { param: value, reason: string } | Control Plane policy updates |
| Anomaly Reports | JSON | { anomaly: description, severity: 1-5 } | Dashboard + Alerts |
| Trend Prediction | JSON | { metric: value, timeframe: "1h"\|"24h" } | Dashboard (Step 8) |
| Resource Forecast | JSON | { cpu: pct, memory: pct, disk: pct } | Operations (capacity planning) |

**Example Output:**
```json
{
  "traffic_classification": "normal",
  "confidence": 0.92,
  "anomalies_detected": [
    {
      "type": "traffic_spike",
      "severity": 3,
      "description": "Throughput 40% above baseline at 15:45 UTC",
      "duration_minutes": 12
    }
  ],
  "recommendations": [
    {
      "component": "relay",
      "parameter": "buffer_size",
      "recommended_value": 4194304,
      "reason": "Reduce jitter under current load pattern",
      "expected_improvement_pct": 15
    }
  ],
  "forecast_24h": {
    "peak_throughput_mbps": 520,
    "peak_time_utc": "2025-11-04T20:00:00Z",
    "cpu_usage_peak_pct": 72
  }
}
```

### Futures/Features Being Built

| Future Feature | Status | Target Completion | Priority | Why Needed |
|---|---|---|---|---|
| Online Learning (Continuous Model Updates) | Framework | Q1 2026 | High | Adapt to new attack patterns |
| Federated Learning (Privacy-Preserving) | Designed | Q2 2026 | Medium | Train on multi-tenant data safely |
| Explainable AI (SHAP/LIME) | Planned | Q1 2026 | Medium | Understand model decisions |
| Reinforcement Learning for Tuning | Research | Q2 2026 | Low | Autonomous system optimization |
| Custom Model Training (Per-Tenant) | Designed | Q1 2026 | Medium | Tenant-specific baselines |
| Real-time Stream Processing (Spark) | Planned | Q1 2026 | High | Sub-second inference |
| Model Ensemble Methods | Partial | Q4 2025 | Medium | Improve prediction accuracy |
| Auto-scaling Recommendations | Framework | Q4 2025 | High | Predict when to scale |

### Prerequisites for Futures

| Future | Blocking Prerequisites | Status |
|--------|---|---|
| **Online Learning** | Continuous data pipeline | Partial - metrics exist |
| | Model versioning system | Ready - git-based versioning |
| | A/B testing framework | Not started |
| | Gradual model rollout | Designed, not implemented |
| **Federated Learning** | Privacy aggregation algorithm | Research phase |
| | Distributed training setup | Not started |
| | Model averaging mechanism | Not implemented |
| **Explainable AI** | SHAP library integration | Not started |
| | Feature importance ranking | Designed |
| | Decision explanation UI | Not started |
| **Reinforcement Learning** | Environment simulator | Not started |
| | Reward function definition | Designed |
| | Safe exploration strategies | Needs implementation |
| **Custom Per-Tenant Models** | Tenant data isolation | Ready (metrics labeled) |
| | Training data collection per tenant | Partial - needs 90 days |
| | Model storage per tenant | Designed, not implemented |
| **Stream Processing** | Apache Spark cluster | Not started |
| | Kafka topic configuration | Designed |
| | Real-time model serving (KServe) | Framework ready |
| **Ensemble Methods** | Model registry | Ready |
| | Ensemble voting logic | Designed, not implemented |
| | Diversity metrics | Not started |
| **Auto-scaling** | Horizontal pod autoscaling (HPA) | Ready (Kubernetes) |
| | Scaling decision rules | Designed, not implemented |
| | Cost-benefit analysis | Not started |

### Use Cases / Testing Scenarios

**Use Case 1: Classify Traffic as Normal**
```
Test: ML model identifies normal traffic
Input:
  - Metrics from step 5: 2000 RPS, 45ms latency, 0.05% loss
  - Historical baseline: avg 1800 RPS
  - Standard deviation: 200 RPS

Expected Output:
  - traffic_classification: "normal"
  - confidence: 0.96
  - anomalies_detected: []
  - recommendations: []

Verification: Model output confidence > 0.75, classification matches domain expert
```

**Use Case 2: Detect Bot Traffic**
```
Test: ML model identifies automated bot attacks
Input:
  - Metrics: 50,000 RPS, extremely uniform (std dev <5)
  - User-Agent analysis: All identical, non-browser headers
  - Geo pattern: All from 3 ASNs (botnet)

Expected Output:
  - traffic_classification: "bot"
  - confidence: 0.98
  - anomalies_detected: [{ type: "bot_detected", severity: 5 }]
  - recommendations: [{ component: "ddos", action: "tighten_detection_threshold" }]

Verification: Cross-check with DDoS module bot detector, verify ASN blacklist
```

**Use Case 3: Anomaly Detection - Unusual Spike**
```
Test: ML detects traffic anomaly outside baseline
Input:
  - Baseline (7 days): avg 1000 RPS, p95 1500 RPS
  - Current: 5000 RPS (5x normal, but legitimate)
  - Pattern: Different from bot signature

Expected Output:
  - traffic_classification: "anomaly"
  - confidence: 0.88
  - anomalies_detected: [{
      type: "traffic_spike",
      severity: 4,
      description: "5x normal capacity, sustained 15+ minutes",
      likely_cause: "legitimate traffic surge (viral content?)"
    }]
  - recommendations: [{ component: "relay", action: "scale_up" }]

Verification: Manual review confirms legitimate spike, model learned new pattern
```

**Use Case 4: Optimization Recommendation**
```
Test: AI recommends configuration changes
Input:
  - Current metrics: P95 latency 60ms, jitter 0.8ms
  - Traffic pattern: Bursty (high variance)
  - Hardware: RTT 48ms, available bandwidth 500 Mbps

Expected Output:
  - recommendations: [
      { param: "buffer_size", value: 4194304, benefit: "+20% jitter" },
      { param: "packet_pacing", value: "aggressive", benefit: "+10% throughput" },
      { param: "cwnd_gain", value: 2.5, benefit: "faster startup" }
    ]
  - priority: "high"
  - expected_improvement_pct: 28

Verification: Apply recommendations, measure actual improvement
```

**Use Case 5: Capacity Prediction (24-hour Forecast)**
```
Test: ML predicts peak load for next 24 hours
Input:
  - Historical 30 days of hourly throughput
  - Day of week: Tuesday (similar pattern to last Tuesday)
  - Seasonal factor: No holidays upcoming

Expected Output:
  - forecast_24h: {
      peak_throughput_mbps: 480,
      peak_time_utc: "2025-11-04T20:15:00Z",
      p95_latency_peak_ms: 65,
      cpu_peak_pct: 75
    }
  - confidence: 0.91
  - recommended_action: "Consider scaling 1 hour before peak"

Verification: Compare forecast to actual peak 24 hours later, measure MAPE
```

**Use Case 6: Online Learning - Continuous Update (Future)**
```
Test: ML model improves by learning from new data daily
Input:
  - 24 hours of new traffic data collected
  - Ground truth: Manual expert labeling of 500 samples
  - Current model accuracy: 92%

Expected Output:
  - New model trained with combined data (historical + new)
  - New model accuracy: 94-95%
  - A/B test: 50% traffic on old, 50% on new model
  - If new model better: Automatically promote to production

Verification: Monitor A/B test metrics, check model version history
```

### Dependencies

| Component | Required By | Status | Impact if Missing |
|-----------|---|---|---|
| Monitoring (Step 5) | Metrics input | Ready | No data to analyze |
| DDoS (Step 3) | Receives recommendations | Ready | AI suggestions ignored |
| Control Plane (Step 2) | Receives config recommendations | Ready | Can't auto-apply tuning |
| Relay (Step 4) | Performance optimization | Ready | Can't tune parameters |
| Dashboard (Step 8) | Visualize predictions | Ready | Can display when available |
| Training Data (90+ days) | Online learning (Future) | Partial - needs collection | Blocks continuous learning |
| Kubernetes GPU Nodes | GPU inference (optional) | Ready if available | CPU inference slower |
| Model Registry | Store model versions | Designed, not implemented | Can't version models |

### Notes

- Current **20% completeness** means ML framework loaded but models are stubs
- **Inference timeout**: 100ms is aggressive - models must return within 100ms or decision times out
- **Online learning** requires **90 days of baseline data** before training is accurate (cold-start problem)
- **Traffic classification** uses 5 input features: RPS uniformity, geo distribution, ASN count, user-agent diversity, request patterns
- **Anomaly detection** uses isolation forest on 15 metrics (latency, throughput, jitter, loss, etc.)

---

## 7. Dashboard - Operations Visibility (Step 7-8)

### Component: Dashboard - Next.js Frontend + Real-time Updates

**Current Implementation Status:** 50% complete (UI framework, API integration incomplete)
**Location:** `frontend/`, `deployments/dashboard/`

### Current Capabilities

- Next.js 14 web application framework
- Real-time metrics visualization (via Grafana JSON API)
- Multi-tenant role-based access control (RBAC)
- Responsive design (mobile/tablet/desktop)
- WebSocket support for real-time updates
- Authentication via Zitadel OIDC

### Required Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| Prometheus Metrics | Prometheus HTTP API | Step 5: Monitoring | Yes |
| Grafana Dashboards | Grafana HTTP API (JSON) | Step 5: Monitoring | Yes |
| Alertmanager Events | Alertmanager HTTP API | Step 5: Monitoring | No |
| AI Predictions | JSON API | Step 6: AI Service | No |
| User JWT Token | Signed JWT | Zitadel (Step 2) | Yes |
| Relay Status | JSON | Relay health API | No |
| System Logs | JSON | Log aggregation (Loki/ELK) | No |

### Input Parameters (Configuration)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `dashboard.enabled` | bool | `true` | Enable dashboard service |
| `dashboard.port` | int | `3000` | HTTP port |
| `dashboard.refresh_interval_sec` | int | `5` | Auto-refresh metrics |
| `dashboard.theme` | string | `"dark"` | "dark" \| "light" |
| `dashboard.enable_websocket` | bool | `true` | Real-time updates |
| `dashboard.metrics_lookback_hours` | int | `24` | Default time range |
| `dashboard.enable_custom_dashboards` | bool | `false` | User-created dashboards (Future) |
| `dashboard.export_format` | string | `"png,pdf,csv"` | Export options |

**Dashboard Views (Current):**
```
1. Overview - Summary of all 8 steps
2. Relay Performance - Latency, throughput, jitter metrics
3. DDoS Status - Threat scores, blocked requests
4. Tenant Dashboard - Per-customer view
5. Alerts - Current and historical alerts
6. System Health - CPU, memory, disk of all components
7. Cost Analytics - Resource usage per tenant (Future)
8. SLO Tracking - Service level objectives compliance
```

### Output Specifications

| Output | Type | Format | Consumed By |
|--------|------|--------|-------------|
| Dashboard HTML | Web page | HTML + CSS + JS | Browser |
| Metrics JSON | Data series | Prometheus JSON | Frontend charts |
| Alert Notifications | WebSocket events | JSON push events | Browser toast notifications |
| Export Data | File | CSV/PDF/PNG | User download |
| Log Entries | JSON | Structured logs | Dashboard console |

**Example Dashboard Response:**
```json
{
  "dashboard_name": "Overview",
  "refresh_interval_ms": 5000,
  "sections": [
    {
      "section": "DNS Performance",
      "metrics": [
        { "name": "query_latency_p95", "value": 0.8, "unit": "ms", "status": "good" },
        { "name": "resolution_rate", "value": 99.99, "unit": "%", "status": "excellent" }
      ]
    },
    {
      "section": "DDoS Status",
      "metrics": [
        { "name": "blocked_requests_1h", "value": 250000, "unit": "requests", "status": "normal" },
        { "name": "threat_score_avg", "value": 0.12, "unit": "score", "status": "low" }
      ]
    }
  ]
}
```

### Futures/Features Being Built

| Future Feature | Status | Target Completion | Priority | Why Needed |
|---|---|---|---|---|
| Custom Dashboard Builder | Designed | Q1 2026 | Medium | Users create own views |
| Real-time Log Search | Planned | Q1 2026 | Medium | Troubleshoot issues faster |
| Advanced Export (PDF Reports) | Partial | Q4 2025 | Low | Executive reporting |
| Dark Mode Toggle | Framework | Done | Done | User preference |
| Mobile App (React Native) | Designed | Q2 2026 | Low | Monitor from phone |
| Anomaly Visualization | Framework | Q1 2026 | High | Understand AI recommendations |
| Cost Attribution Dashboard | Designed | Q1 2026 | Medium | Show billing per customer |
| Slack/Teams Integration | Designed | Q4 2025 | Low | Receive alerts in chat |

### Prerequisites for Futures

| Future | Blocking Prerequisites | Status |
|--------|---|---|
| **Custom Dashboard Builder** | Drag-drop layout library | Ready (react-beautiful-dnd) |
| | Dashboard template schema | Designed, not implemented |
| | User dashboard storage | Needs database schema |
| **Real-time Log Search** | Elasticsearch/Loki integration | Not started |
| | Log query UI | Not implemented |
| | Log indexing pipeline | Not started |
| **PDF Reports** | Report template engine | Ready (ReportLab/PDFKit) |
| | Schedule report generation | Not implemented |
| | Email delivery | Designed |
| **Mobile App** | React Native setup | Designed, not started |
| | Mobile API backend | Partial - REST ready |
| | Offline sync | Not implemented |
| **Anomaly Visualization** | AI Step 6 integration | Framework ready |
| | Anomaly explanation UI | Not implemented |
| | Historical anomaly timeline | Not started |
| **Cost Dashboard** | Cost attribution system | Planned - needs metrics |
| | Per-tenant cost model | Not started |
| | Cost forecasting | Not started |
| **Slack Integration** | Slack webhook API | Ready |
| | Alert-to-Slack formatter | Not implemented |
| | Two-way sync (user actions) | Not implemented |

### Use Cases / Testing Scenarios

**Use Case 1: Monitor Live System Overview**
```
Test: Operations team views dashboard for system status
Input:
  - Load dashboard at https://dashboard.cloudbridge.io
  - Auto-refresh every 5 seconds
  - View all 8 components

Expected Output:
  - DNS: Query latency p95 = 0.8ms (green)
  - Control Plane: Auth validations 5k/min (green)
  - DDoS: Threat score avg = 0.15 (green, low)
  - Relay: Latency p95 = 48ms (green), throughput = 425 Mbps (green)
  - Monitoring: Uptime = 99.98% (green)
  - AI: Inference time p95 = 78ms (green)
  - Dashboard: Page load time = 450ms (yellow, acceptable)
  - All metrics auto-update every 5s

Verification: Check that all panels load, refresh rate is 5 seconds
```

**Use Case 2: Alert Notification Pop-up**
```
Test: Operations notified when SLO breached
Input:
  - Alertmanager triggers: "Latency P95 > 60ms"
  - WebSocket pushes alert event to browser

Expected Output:
  - Toast notification appears in dashboard corner
  - Alert includes: component, threshold, current value, time
  - Sound alert plays (configurable)
  - Alert logged in "Alerts" section
  - Dashboard highlights affected metric in red

Verification: Trigger alert rule manually, verify notification delivery
```

**Use Case 3: Per-Tenant Isolated View**
```
Test: Customer A only sees their own metrics
Input:
  - Customer A logs in with Zitadel OIDC token
  - tenant_id = UUID-A in JWT claims
  - Accesses "Tenant Dashboard"

Expected Output:
  - All metrics filtered to Customer A only
  - Shows only A's PoP data
  - Cannot access Customer B's graphs
  - Shows A's cost allocation (future)
  - RBAC enforced: read-only user can't change settings

Verification: Compare logged-in dashboard to Prometheus directly, verify filtering
```

**Use Case 4: Export Historical Data**
```
Test: Export 7-day performance report
Input:
  - User clicks "Export" on Relay Performance dashboard
  - Selects format: CSV
  - Date range: Last 7 days

Expected Output:
  - CSV file downloaded: relay_performance_7d.csv
  - Columns: timestamp, latency_ms, throughput_mbps, jitter_ms, packet_loss_pct
  - 2016 rows (7 days × 24 hours × 12 samples)
  - Can import into Excel for analysis

Verification: Open CSV, verify timestamp format, row count matches 7 days
```

**Use Case 5: AI Recommendations Visualization (Future)**
```
Test: Display AI recommendations on dashboard
Input:
  - AI Service (Step 6) generates optimization recommendations
  - Example: "Increase buffer size from 2MB to 4MB, expect +15% jitter reduction"

Expected Output:
  - "Recommendations" panel appears on dashboard
  - Shows: component, parameter, new value, expected benefit
  - User can "Apply" recommendation (if admin)
  - Before/after metrics comparison
  - 30-day tracking of applied recommendations

Verification: Apply recommendation, monitor improvement over 24 hours
```

### Dependencies

| Component | Required By | Status | Impact if Missing |
|-----------|---|---|---|
| Monitoring (Step 5) | Metrics API (Prometheus) | Ready | No metrics visible |
| Grafana | Dashboard API | Ready | Can import grafana.json configs |
| Zitadel (Step 2) | OIDC authentication | Ready | Can't log in |
| AI Service (Step 6) | Recommendations display | Framework ready | Can't show AI insights |
| Log Aggregation | Log search (Future) | **NOT STARTED** | Blocks log search feature |
| Elasticsearch/Loki | Log indexing (Future) | **NOT STARTED** | Blocks log search feature |

### Notes

- Current **50% completeness** means UI framework ready but API integrations partial
- **Real-time updates** use WebSocket - no polling needed, <1s latency for metric updates
- **RBAC** properly enforces tenant isolation via JWT `custom:tenant_id` claim
- **Mobile app** is designed but low priority - web dashboard is responsive to mobile browsers
- **Cost attribution** requires cost model definition (not started) before per-tenant billing display

---

## Summary Table: All Components

| Step | Component | Implementation Status | Current Capabilities | Blocking Futures | Timeline |
|------|-----------|---|---|---|---|
| 1 | DNS Network | 35% | GeoDNS, caching, multi-tenant | DNSSEC, Anycast DNS, failover | Q4-Q1 |
| 2 | Control Plane | 75% | OIDC, JWT, service accounts | MFA, PAT (testing), RBAC | Q4-Q1 |
| 3 | DDoS Protection | 20% | Framework, rule engine | Real-time learning, anomaly detection, geo-blocking | Q4-Q1 |
| 4 | Scalable Relay | 35% | QUIC, BBRv3, TLS 1.3 | WireGuard tunnel, TCP→QUIC, connection pooling | Q4-Q1 |
| 5 | Monitoring | 75% | Prometheus, Grafana, alerts | OpenTelemetry tracing, ELK logging | Q4-Q1 |
| 6 | AI Service | 20% | ML framework, inference ready | Online learning, federated learning, explainable AI | Q1-Q2 |
| 7-8 | Dashboard | 50% | Next.js UI, real-time updates | Custom dashboards, log search, cost attribution | Q4-Q1 |

---

## Implementation Roadmap

### Q4 2025 (This Quarter)

**Priority 1 - Production Readiness:**
- DNS: Implement health check system (failover support)
- Control Plane: Complete PAT token generation and testing
- DDoS: Layer 7 HTTP attack detection
- Relay: TCP↔QUIC protocol conversion, basic tunnel manager stub
- Monitoring: OpenTelemetry tracing design + pilot deployment
- AI: Complete bot detection model training
- Dashboard: Alert notification WebSocket integration

**Priority 2 - Feature Completion:**
- DNS: DNSSEC validation framework
- Control Plane: MFA design document + Zitadel integration
- DDoS: Geo-IP blocking framework
- Relay: Connection pooling design
- Monitoring: SLO burn rate calculation
- AI: Real-time model update pipeline design
- Dashboard: PDF export capability

### Q1 2026

**Priority 1 - Advanced Features:**
- DNS: Anycast DNS deployment on AS64512
- Control Plane: RBAC/ABAC policy engine selection
- DDoS: Adaptive rate limiting implementation
- Relay: WireGuard tunnel full integration
- Monitoring: OpenTelemetry Jaeger deployment
- AI: Online learning loop with A/B testing
- Dashboard: Custom dashboard builder

**Priority 2 - Optimization:**
- DNS: Geographic weighted distribution
- Control Plane: Credential rotation automation
- DDoS: Encrypted traffic analysis research
- Relay: Advanced packet pacing tuning
- Monitoring: Long-term metrics archive (data warehouse)
- AI: Federated learning pilot
- Dashboard: Real-time log search (Loki integration)

### Q2 2026+

- Reinforcement learning for autonomous tuning
- SAML/ADFS support for enterprise customers
- Predictive DDoS detection
- Mobile app (React Native)
- Cost attribution and billing integration

---

## How to Use This Matrix

**For Operations Teams:**
1. Find your component in the summary table above
2. Check "Current Capabilities" - what works now
3. Review "Use Cases" - how to test/verify
4. Check dependencies - what else must be ready
5. Monitor "Futures" - what's coming and when

**For Development Teams:**
1. Find the component you're implementing
2. Review "Required Inputs" - what data you need
3. Check "Prerequisites for Futures" - what blocks your feature
4. See "Dependencies" - what components to wait for
5. Use "Use Cases" as test scenarios

**For Product/Planning:**
1. Check "Futures/Features" timeline
2. Identify blocking prerequisites
3. Plan dependency coordination (e.g., Health Check system blocks 3 features)
4. Sequence features based on dependencies
5. Track in sprint planning

---

**Document Status:** COMPLETE
**Last Updated:** November 4, 2025
**Next Review:** When major feature completion occurs (quarterly)
