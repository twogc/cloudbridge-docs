# CloudBridge Relay Client - Architecture & Implementation Guide

**Version:** 1.0
**Date:** November 4, 2025
**Status:** Complete Reference Documentation
 

---

## Executive Summary

CloudBridge Relay Client is a production-ready, cross-platform P2P mesh networking client written in Go. It enables secure, distributed connectivity with enterprise-grade features including JWT/OIDC authentication, multi-protocol support (QUIC, gRPC, WebSocket, WireGuard), NAT traversal, and comprehensive observability.

**Key Capabilities:**
- P2P mesh networking with automatic peer discovery
- Secure tunneling (TCP port forwarding)
- L3-overlay networks with per-tenant IPAM
- Multi-transport fallback (QUIC → gRPC → WebSocket)
- Service integration (systemd, launchd, Windows Service)
- Production metrics and health checks
- Cross-platform deployment (Linux, macOS, Windows)

---

## Part 1: Client Architecture Overview

### 1.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  CloudBridge Relay Client                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    CLI Interface                        │  │
│  │  (cloudbridge-client init/join/p2p/tunnel/service)     │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │                                         │
│  ┌────────────────────▼────────────────────────────────────┐  │
│  │              Config Management                         │  │
│  │  (YAML loader, env vars, hot-reload, watcher)         │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │                                         │
│  ┌────────────────────▼────────────────────────────────────┐  │
│  │            Main Relay Client                           │  │
│  │  (Connect, Authenticate, CreateTunnel, Heartbeat)      │  │
│  │                                                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │ Auth     │ │ P2P      │ │ Tunnel   │ │ Metrics  │ │  │
│  │  │ Manager  │ │ Manager  │ │ Manager  │ │          │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │                                         │
│  ┌────────────────────▼────────────────────────────────────┐  │
│  │           Transport Layer Selection                    │  │
│  │  (Intelligent fallback: QUIC → gRPC → WebSocket)      │  │
│  └────────────────────┬────────────────────────────────────┘  │
│                       │                                         │
│   ┌───────┬───────┬───┴────┬────────┬─────────┐              │
│   │       │       │        │        │         │              │
│  ▼       ▼       ▼        ▼        ▼         ▼              │
│ ┌───┐ ┌────┐ ┌──────┐ ┌──────┐ ┌─────┐ ┌──────┐             │
│ │Q  │ │gRPC│ │WebSo │ │QUIC  │ │TURN │ │DERP  │             │
│ │U  │ │    │ │cket  │ │Strms │ │Rela │ │Fall  │             │
│ │I  │ │    │ │      │ │      │ │y    │ │back  │             │
│ │C  │ │    │ │      │ │      │ │     │ │      │             │
│ └───┘ └────┘ └──────┘ └──────┘ └─────┘ └──────┘             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Network Layer (NAT Traversal)                │  │
│  │  ICE, STUN, TURN, DERP - Pion Library               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Platform Services                            │  │
│  │  systemd / launchd / Windows Service                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘

                        ▼
                  Relay Server
                (Step 4 in architecture)
```

### 1.2 Component Hierarchy

```
cloudbridge-client (CLI)
├── cmd/
│   ├── init        → Interactive setup wizard
│   ├── join        → Invite-based onboarding
│   ├── p2p         → Start P2P mesh networking
│   ├── tunnel      → Create port forwarding tunnels
│   ├── service     → Manage systemd/launchd/Windows services
│   ├── wireguard   → L3-overlay network management
│   ├── health      → Health checks & diagnostics
│   └── version     → Display version info
│
└── pkg/
    ├── relay/      → Main relay client
    ├── auth/       → JWT + OIDC authentication
    ├── config/     → Configuration system
    ├── p2p/        → P2P mesh management
    ├── quic/       → QUIC transport
    ├── grpc/       → gRPC services
    ├── websocket/  → WebSocket fallback
    ├── tunnel/     → TCP tunneling & port forwarding
    ├── heartbeat/  → Keepalive & monitoring
    ├── metrics/    → Prometheus observability
    ├── types/      → Core type definitions
    ├── errors/     → Error handling & retry logic
    ├── service/    → OS service integration
    ├── wizard/     → Interactive setup
    ├── api/        → HTTP API for P2P operations
    └── util/       → Utilities and helpers
```

---

## Part 2: Core Components

### 2.1 Client Type (Main Orchestrator)

**Location:** `pkg/relay/client.go`

**Responsibility:** Orchestrate all connectivity operations

```go
type Client struct {
    config            *Config
    authManager       *AuthManager
    p2pManager        *P2PManager
    tunnelManager     *TunnelManager
    heartbeatManager  *HeartbeatManager
    transport         Transport
    metrics           *Metrics
    logger            *Logger
    ctx               context.Context
    cancel            context.CancelFunc
}

// Main methods:
func (c *Client) Connect() error                    // Connect to relay
func (c *Client) Authenticate() error               // Validate JWT
func (c *Client) CreateTunnel(...) (Tunnel, error)  // Create port forwarding
func (c *Client) StartHeartbeat() error             // Start keepalive
func (c *Client) SetTransportMode(t TransportMode) // Switch protocol
func (c *Client) Close() error                      // Graceful shutdown
```

**Lifecycle:**
1. Initialize with config
2. Load and validate configuration
3. Establish connection to relay (with auto-retry)
4. Authenticate with JWT or OIDC
5. Start heartbeat for keepalive
6. Create tunnels/P2P mesh as needed
7. Monitor and report metrics
8. Gracefully shutdown on demand

### 2.2 Configuration System

**Location:** `pkg/config/` and `pkg/types/types.go`

**Configuration Structure:**

```yaml
relay:
  host: "edge.2gc.ru"
  ports:
    quic: 5553
    stun: 19302
    turn: 3478
    derp: 3479
    masque: 8443

auth:
  type: "jwt"  # or "oidc"
  token: "eyJ..."
  oidc:
    issuer_url: "https://zitadel.example.com"
    audience: "cloudbridge-client"
    scopes: ["openid", "profile", "email"]

p2p:
  heartbeat_interval: 30s
  peer_discovery_interval: 30s
  max_connections: 100
  fallback_enabled: true
  mesh_config:
    peerIP: "10.0.0.x"
    tenantCIDR: "10.0.0.0/24"
    wireguardConfig:
      privateKey: "xxx"
      address: "10.0.0.1/32"

transport:
  mode: "auto"  # "auto", "quic", "grpc", "websocket"
  prefer_protocol: "quic"
  fallback_enabled: true
  timeout_ms: 5000

metrics:
  enabled: true
  prometheus_port: 9090
  pushgateway:
    enabled: true
    push_url: "http://pushgateway:9091"
    push_interval: 15s

logging:
  level: "info"  # "debug", "info", "warn", "error"
  format: "json"
  output: "stdout"

performance:
  buffer_size: 65536
  max_concurrent_tunnels: 100
  quic_packet_loss_threshold: 0.05
```

**Configuration Priority (highest to lowest):**
1. CLI flags (--config, --token, --verbose)
2. Environment variables (CLOUDBRIDGE_*)
3. Config file (YAML)
4. Default values

**Hot-Reload:**
```go
// Config file can be watched for changes
watcher.Watch(configFile, func() {
    newConfig = LoadConfig()
    client.UpdateConfig(newConfig)  // Applied without restart
})
```

### 2.3 Authentication Manager

**Location:** `pkg/auth/auth.go`

**Supported Methods:**

**1. JWT (JSON Web Tokens)**
```go
func (am *AuthManager) ValidateJWT(token string) (*Claims, error) {
    // Parse and validate token
    // Extract claims: sub, tenant_id, permissions, etc.
    // Return parsed claims
}

type Claims struct {
    Subject      string   `json:"sub"`
    TenantID     string   `json:"custom:tenant_id"`
    Permissions  []string `json:"custom:permissions"`
    MeshConfig   string   `json:"custom:mesh_config"`
    NetworkConfig string  `json:"custom:network_config"`
    IssuedAt     int64    `json:"iat"`
    ExpiresAt    int64    `json:"exp"`
    NotBefore    int64    `json:"nbf"`
}
```

**2. OIDC (OpenID Connect) with Zitadel**
```go
func (am *AuthManager) ValidateOIDC(token string) (*Claims, error) {
    // 1. Fetch JWKS from issuer (cached 1 hour)
    jwks := am.fetchJWKS(issuerURL)

    // 2. Validate JWT signature against JWKS keys
    claims := validateSignature(token, jwks)

    // 3. Verify claims: issuer, audience, expiration
    verifyIssuer(claims, expectedIssuer)
    verifyAudience(claims, expectedAudience)
    verifyExpiration(claims)

    // 4. Return validated claims
    return claims, nil
}
```

**3. OS Keyring Integration**
```go
// Securely store and retrieve tokens from OS storage:

// Windows: Credential Manager
// macOS: Keychain
// Linux: libsecret (GNOME Secret Service / KDE Wallet)

token := am.GetFromKeyring("cloudbridge-token")
am.SaveToKeyring("cloudbridge-token", token)
am.DeleteFromKeyring("cloudbridge-token")
```

**Authentication Flow:**
```
1. Load token from config/env/keyring
2. Validate token signature (JWT) or issuer (OIDC)
3. Check expiration
4. Extract claims (tenant_id, permissions, etc.)
5. Apply claims to client context
6. Use tenant_id for isolation in all operations
```

### 2.4 P2P Manager

**Location:** `pkg/p2p/manager.go`

**Responsibilities:**
- Mesh network topology management
- Peer discovery (via relay or mDNS)
- NAT traversal (ICE, STUN, TURN, DERP)
- L3-overlay network configuration
- Per-tenant IPAM (IP Address Management)

**Mesh Network Features:**

```go
type P2PManager struct {
    peers           map[string]*Peer     // Discovered peers
    discoveryMgr    *DiscoveryManager    // Peer discovery
    iceAgent        *ice.Agent           // ICE for NAT traversal
    meshConfig      *MeshConfig          // Topology config
    wireguardMgr    *WireGuardManager    // L3 overlay
    ipamMgr         *IPAMManager         // IP allocation
}

type Peer struct {
    ID              string
    TenantID        string
    PublicIP        string
    PrivateIPs      []string
    TransportMode   TransportMode
    ConnectionState ConnectionState
    LastSeen        time.Time
    Metrics         *PeerMetrics
}

type MeshConfig struct {
    PeerIP       string      // e.g., "10.0.0.5"
    TenantCIDR   string      // e.g., "10.0.0.0/24"
    WireGuard    WGConfig    // L3 overlay details
}
```

**NAT Traversal Stack:**
```
Priority 1: Direct peer-to-peer (no NAT)
Priority 2: STUN (discover public IP:port)
Priority 3: TURN relay (if direct fails)
Priority 4: DERP fallback (encrypted relay)
```

**Peer Discovery:**
```
1. Query relay server for peer list (gRPC)
2. Filter by tenant_id (isolation)
3. Filter by current location/region (optimization)
4. Attempt direct connection
5. If fails, use TURN relay
6. If TURN fails, use DERP fallback
7. Periodic re-discovery every 30 seconds
```

**L3 Overlay Network:**
```
WireGuard tunnel per tenant:
├── Interface: wg0 (or wgtenant)
├── Private Key: tenant-specific
├── Address: 10.0.0.X/32 (from IPAM)
├── Peers: All other tenants' endpoints
└── Routes: Tenant CIDR → wg0

IPAM (IP Address Management):
├── Per-tenant subnet allocation
├── Persistent assignment (sticky IPs)
├── Conflict detection & resolution
└── Automatic cleanup on peer removal
```

### 2.5 Tunnel Manager

**Location:** `pkg/tunnel/manager.go`

**Purpose:** Local port forwarding via relay

```go
type TunnelManager struct {
    tunnels         map[string]*Tunnel
    bufferPool      *sync.Pool           // Reusable buffers
    statistics      *TunnelStatistics
}

type Tunnel struct {
    ID              string
    LocalAddr       string               // 127.0.0.1:3389
    RemoteAddr      string               // remote.example.com:3389
    Transport       net.Conn
    BytesSent       atomic.Int64
    BytesReceived   atomic.Int64
    CreatedAt       time.Time
    LastActivity    time.Time
}

func (tm *TunnelManager) CreateTunnel(
    localPort int,
    remoteHost string,
    remotePort int,
) (*Tunnel, error) {
    // Create listener on local port
    listener, _ := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", localPort))

    // For each incoming connection:
    // 1. Dial remote via relay
    // 2. Forward bidirectional traffic
    // 3. Track bytes sent/received
    // 4. Update statistics
}

// Statistics:
type TunnelStatistics struct {
    TotalConnections    int64
    ActiveConnections   int32
    BytesSent           int64
    BytesReceived       int64
    AvgLatency          float64
    ErrorCount          int64
}
```

**Tunnel Features:**
- Multiple concurrent tunnels
- Buffer pooling for efficiency
- Per-tunnel statistics
- Automatic cleanup on connection drop
- Rate limiting per tunnel

### 2.6 Heartbeat Manager

**Location:** `pkg/heartbeat/manager.go`

**Purpose:** Keep-alive and connectivity monitoring

```go
type HeartbeatManager struct {
    client          *Client
    interval        time.Duration      // Default: 30 seconds
    timeout         time.Duration      // Default: 10 seconds
    maxRetries      int                // Default: 3
    backoffConfig   *BackoffConfig     // Exponential backoff
}

type BackoffConfig struct {
    InitialDelay time.Duration    // 1 second
    Multiplier   float64          // 2.0 (double each retry)
    MaxDelay     time.Duration    // 60 seconds
    Jitter       bool             // Prevent thundering herd
}

func (hm *HeartbeatManager) Start(ctx context.Context) error {
    ticker := time.NewTicker(hm.interval)

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-ticker.C:
            // Send heartbeat to relay
            if err := hm.sendHeartbeat(); err != nil {
                // Retry with exponential backoff
                delay := hm.calculateBackoff(attempt)
                time.Sleep(delay)
                continue
            }
            // Reset retry counter on success
            attempt = 0
        }
    }
}

func (hm *HeartbeatManager) calculateBackoff(attempt int) time.Duration {
    delay := hm.backoffConfig.InitialDelay *
             time.Duration(math.Pow(hm.backoffConfig.Multiplier, float64(attempt)))

    if delay > hm.backoffConfig.MaxDelay {
        delay = hm.backoffConfig.MaxDelay
    }

    if hm.backoffConfig.Jitter {
        jitter := time.Duration(rand.Int63n(int64(delay)))
        return delay + jitter
    }
    return delay
}
```

**Heartbeat Flow:**
```
1. Every 30 seconds (configurable)
2. Send lightweight "ping" to relay
3. Wait for "pong" (timeout: 10 seconds)
4. If fails: retry with exponential backoff (1s, 2s, 4s, 8s... max 60s)
5. If all retries fail: trigger reconnection
6. Resume normal heartbeat on success
```

**Metrics Collected:**
```
heartbeat_latency_ms (histogram)
heartbeat_failures_total (counter)
heartbeat_success_total (counter)
connection_state (gauge)  # "connected", "reconnecting", "disconnected"
```

---

## Part 3: Protocol Support & Transport Layer

### 3.1 Protocol Stack

**Primary Transport: QUIC (RFC 9000)**
```
QUIC (HTTP/3)
├── Connection ID: For connection migration
├── TLS 1.3: Built-in encryption
├── Streams: Multiplexed bidirectional channels
├── Datagram: Unreliable datagrams (DNS, etc.)
└── BBRv3: Congestion control (from relay)

Features:
• 0-RTT resumption (fast reconnection)
• Connection migration (IP/port change)
• Packet loss recovery (FEC optional)
• Flow control per stream
```

**Fallback Transport 1: gRPC + Protocol Buffers**
```
gRPC Services:
├── ControlService (authentication, heartbeat)
├── TunnelService (port forwarding)
├── P2PService (mesh peer operations)
├── MetricsService (observability)
└── HealthService (health checks)

Transport: HTTP/2 over TLS 1.3
```

**Fallback Transport 2: WebSocket (wss://)**
```
WebSocket over HTTPS:
├── For restricted networks (corporate proxies)
├── Fallback when QUIC unavailable
├── Manual heartbeat (no QUIC-style keep-alive)
└── Higher latency than QUIC
```

**NAT Traversal: ICE (Interactive Connectivity Establishment)**
```
ICE Agents (via Pion library):
├── Host Candidates: Local private IPs
├── Server Reflexive: STUN-discovered public IP
├── Peer Reflexive: Discovered during connectivity check
├── Relay Candidates: TURN-discovered addresses
└── Fallback: DERP (Encrypted relay)

Candidate Prioritization:
1. Host candidates (direct, lowest latency)
2. Server reflexive (p2p through NAT)
3. Peer reflexive (peer discovered)
4. Relay candidates (TURN, higher latency)
5. DERP fallback (as last resort)
```

### 3.2 Transport Selection Logic

**Automatic Fallback Algorithm:**

```go
func (c *Client) SelectTransport() Transport {
    // Try in order of preference:

    // 1. QUIC (preferred)
    if quic := tryQUIC(); quic != nil && quic.isHealthy() {
        return quic
    }

    // 2. gRPC (reliable, but higher latency)
    if grpc := tryGRPC(); grpc != nil && grpc.isHealthy() {
        return grpc
    }

    // 3. WebSocket (restricted networks)
    if ws := tryWebSocket(); ws != nil {
        return ws
    }

    // 4. Error: no transport available
    return nil, ErrNoTransportAvailable
}

// Continuous health monitoring:
go func() {
    for range time.Tick(30 * time.Second) {
        if currentTransport.LatencyMs() > 200 {
            // Switch to faster transport if available
            if alt := findBetterTransport(); alt != nil {
                currentTransport = alt
                logTransportSwitch()
            }
        }
    }
}()
```

**Latency & Timeout Configuration:**

| Transport | Latency | Timeout | Packet Loss Tolerance |
|-----------|---------|---------|----------------------|
| QUIC | 10-50ms | 5s | 10% (recoverable) |
| gRPC | 50-100ms | 10s | 0% (failed req) |
| WebSocket | 100-200ms | 15s | 0% (reconnect) |

---

## Part 4: Authentication & Security

### 4.1 JWT Token Structure

**Example CloudBridge JWT:**

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-2025-11-04"
  },
  "payload": {
    "iss": "https://zitadel.2gc.io/",
    "sub": "user123@example.com",
    "aud": "cloudbridge-client",
    "iat": 1730688000,
    "exp": 1730774400,
    "nbf": 1730688000,
    "custom:tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "custom:permissions": [
      "relay:connect",
      "p2p:mesh",
      "tunnel:create",
      "metrics:read"
    ],
    "custom:mesh_config": "{\"peerIP\":\"10.0.0.5\",\"tenantCIDR\":\"10.0.0.0/24\"}",
    "custom:network_config": "{\"quic_enabled\":true,\"bbr\":true,\"mtu\":1200}",
    "email": "user@example.com",
    "email_verified": true
  },
  "signature": "..." // RS256 signed with Zitadel's private key
}
```

**Claims Explained:**

| Claim | Type | Purpose |
|-------|------|---------|
| iss | string | Issuer (Zitadel instance) |
| sub | string | Subject (user ID) |
| aud | string | Audience (client app) |
| iat | int64 | Issued at (timestamp) |
| exp | int64 | Expires at (timestamp) |
| nbf | int64 | Not before (timestamp) |
| custom:tenant_id | UUID | Tenant isolation |
| custom:permissions | []string | Authorization |
| custom:mesh_config | JSON | P2P mesh settings |
| custom:network_config | JSON | Protocol settings |

### 4.2 Validation Flow

**JWT Validation Process:**

```
1. Extract token from config/env/keyring
   ↓
2. Parse JWT header (alg, kid)
   ↓
3. Fetch signing key (JWKS cache)
   ↓
4. Validate signature
   ↓
5. Check expiration (exp < now)
   ↓
6. Check not-before (nbf > now)
   ↓
7. Verify issuer matches expected
   ↓
8. Verify audience matches expected
   ↓
9. Extract claims for use
   ↓
10. Cache token (1 hour) to reduce JWKS fetches
```

**OIDC Discovery (Zitadel):**

```
GET https://zitadel.2gc.io/.well-known/openid-configuration
{
  "issuer": "https://zitadel.2gc.io/",
  "authorization_endpoint": "https://zitadel.2gc.io/oauth/v2/authorize",
  "token_endpoint": "https://zitadel.2gc.io/oauth/v2/token",
  "jwks_uri": "https://zitadel.2gc.io/oauth/v2/keys"
}

Then fetch JWKS:
GET https://zitadel.2gc.io/oauth/v2/keys
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "key-2025-11-04",
      "use": "sig",
      "alg": "RS256",
      "n": "...",  // public key modulus
      "e": "AQAB"  // public key exponent
    }
  ]
}
```

### 4.3 Multi-Tenancy & Isolation

**Tenant Isolation via JWT Claims:**

```go
type Client struct {
    TenantID string  // From JWT: custom:tenant_id
    MeshConfig MeshConfig  // From JWT: custom:mesh_config
    NetworkConfig NetworkConfig  // From JWT: custom:network_config
}

// Every operation includes tenant context:

func (c *Client) CreateTunnel(...) error {
    // All tunnel operations scoped to c.TenantID
    // Network policies enforce tenant separation
    // Metrics labeled with c.TenantID
    // P2P mesh peers filtered by c.TenantID
}

func (c *Client) DiscoverPeers() ([]Peer, error) {
    // Only return peers with same c.TenantID
    // Prevent cross-tenant peer discovery
    // Isolated mesh networks per tenant
}
```

**Network Isolation:**
```
Per-tenant WireGuard interface:
├── Interface name: wgtenant_<tenant_id>
├── Private subnet: 10.0.0.0/24 (tenant-specific)
├── Peer routes: Only peers with same tenant_id
├── Firewall rules: Tenant↔Tenant blocked
└── Audit logging: All access tagged with tenant_id
```

---

## Part 5: Features & Capabilities

### 5.1 Implemented Features

**Complete & Production-Ready:**

✅ **JWT Authentication**
- Token validation with RS256 signature
- Custom claims extraction
- Token caching (1 hour)
- Expiration checking

✅ **OIDC Integration (Zitadel)**
- JWKS discovery and caching
- Issuer verification
- Audience validation
- Scope support

✅ **P2P Mesh Networking**
- Automatic peer discovery
- Multi-protocol connectivity (QUIC/gRPC/WebSocket)
- ICE/STUN/TURN/DERP fallback
- L3-overlay with WireGuard

✅ **Tunnel Mode (Port Forwarding)**
- TCP port forwarding
- Local port binding
- Remote address proxying
- Per-tunnel statistics

✅ **Heartbeat & Keep-Alive**
- Periodic heartbeat to relay
- Exponential backoff on failure
- Jitter to prevent thundering herd
- Automatic reconnection

✅ **Configuration System**
- YAML-based configuration
- Environment variable overrides
- CLI flag overrides
- Hot-reload support

✅ **Prometheus Metrics**
- Client connection metrics
- P2P session statistics
- Transport mode tracking
- Latency histograms
- Error counters

✅ **Service Integration**
- systemd (Linux)
- launchd (macOS)
- Windows Service

✅ **Error Handling**
- Classified error codes
- Retry strategies per error type
- Exponential backoff
- Circuit breaker pattern

✅ **Cross-Platform Support**
- Linux (x86_64, ARM64, i386)
- macOS (x86_64, ARM64)
- Windows (x86_64, i386)

✅ **OS Keyring Integration**
- Windows Credential Manager
- macOS Keychain
- Linux libsecret

✅ **Interactive Setup**
- Step-by-step configuration wizard
- Validation of each setting
- Guided relay selection
- Token setup

✅ **Health Checks**
- Network connectivity testing
- Configuration validation
- Authentication status
- Performance metrics

### 5.2 Partial/In-Progress Features

⏳ **MASQUE Protocol (40% complete)**
- HTTP/3 tunneling
- Proxy support for restricted networks
- Ongoing integration with QUIC layer

⏳ **SLO Controller (30% complete)**
- Service level objective tracking
- SLA monitoring
- Alert generation

⏳ **Synthetic Probes (30% complete)**
- Network diagnostics
- Latency measurement
- Packet loss testing
- Jitter analysis

⏳ **Dashboard Integration (50% complete)**
- Client metrics reporting
- Connection visualization
- Performance graphs

### 5.3 Not Implemented

❌ **Mobile SDKs**
- iOS support
- Android support

❌ **Advanced Analytics**
- Machine learning on client metrics
- Anomaly detection

❌ **Hardware TPM**
- TPM 2.0 support for key storage

---

## Part 6: Usage Examples

### 6.1 Basic Connection

**Step 1: Initialize Configuration**

```bash
# Interactive setup wizard
./cloudbridge-client init

# Or manually create config.yaml
cat > config.yaml << 'EOF'
relay:
  host: "edge.2gc.ru"
  ports:
    quic: 5553
auth:
  type: "jwt"
  token: "eyJ..."
EOF
```

**Step 2: Connect**

```bash
./cloudbridge-client p2p --config config.yaml

# Output:
# Connected to relay at edge.2gc.ru:5553
# Authenticated as user123@example.com
# Tenant: 550e8400-e29b-41d4-a716-446655440000
# P2P mesh started, 5 peers discovered
# Metrics available at http://127.0.0.1:9090
```

### 6.2 Tunneling Example

**RDP over CloudBridge Tunnel:**

```bash
# Forward local 3389 → remote.example.com:3389
./cloudbridge-client tunnel \
  --config config.yaml \
  --local-port 3389 \
  --remote-host remote.example.com \
  --remote-port 3389

# Connect via RDP:
mstsc /v:127.0.0.1:3389
```

### 6.3 Service Installation

**Linux (systemd):**

```bash
sudo ./cloudbridge-client service install \
  --config /etc/cloudbridge/config.yaml \
  --token "$JWT_TOKEN"

sudo systemctl start cloudbridge-client
sudo systemctl status cloudbridge-client

# View logs:
sudo journalctl -u cloudbridge-client -f
```

**Windows:**

```powershell
# Run as Administrator
.\cloudbridge-client.exe service install `
  -config C:\ProgramData\CloudBridge\config.yaml `
  -token $env:JWT_TOKEN

# Start service:
Start-Service -Name CloudBridgeClient
Get-Service -Name CloudBridgeClient
```

**macOS (launchd):**

```bash
./cloudbridge-client service install \
  --config /etc/cloudbridge/config.yaml \
  --token "$JWT_TOKEN"

# Start service:
launchctl start com.2gc.cloudbridge-client

# View logs:
log stream --predicate 'process == "cloudbridge-client"'
```

### 6.4 Invite-Based Onboarding

```bash
# Click link from email:
./cloudbridge-client join \
  "https://edge.2gc.ru/join?token=eyJ...&tenant_id=550e..."

# Process:
# 1. Fetches configuration from relay
# 2. Extracts token from URL
# 3. Validates token with relay
# 4. Creates local config.yaml
# 5. Starts P2P mesh
```

### 6.5 Health Check

```bash
./cloudbridge-client health --config config.yaml --format json

# Output:
{
  "timestamp": "2025-11-04T15:30:00Z",
  "status": "healthy",
  "details": {
    "network_connectivity": {
      "status": "ok",
      "latency_ms": 45.2
    },
    "authentication": {
      "status": "ok",
      "token_expires_in_seconds": 86390
    },
    "relay_connection": {
      "status": "connected",
      "transport": "quic",
      "latency_ms": 42.5
    },
    "p2p_mesh": {
      "status": "ok",
      "peers_discovered": 5,
      "peers_connected": 5
    },
    "performance": {
      "avg_latency_ms": 43.8,
      "packet_loss_percent": 0.001,
      "throughput_mbps": 450.5
    }
  }
}
```

---

## Part 7: Error Handling & Retry Logic

### 7.1 Classified Errors

**Error Categories:**

| Error | Retryable | Retry Delay | Use Case |
|-------|-----------|-------------|----------|
| ErrInvalidToken | No | — | JWT validation failed |
| ErrTokenExpired | No | — | Token lifetime exceeded |
| ErrUnauthorized | No | — | Insufficient permissions |
| ErrRateLimitExceeded | Yes | 5s | Too many requests |
| ErrServerUnavailable | Yes | 10s | Relay offline |
| ErrConnectionTimeout | Yes | 3s | Network timeout |
| ErrHeartbeatFailed | Yes | 2s | Keep-alive failed |
| ErrP2PConnectionFailed | Yes | 5s | Peer unreachable |
| ErrTunnelClosed | No | — | Port forward closed |

### 7.2 Retry Strategy

**Exponential Backoff Algorithm:**

```go
delay = initialDelay × (multiplier ^ attemptNumber)
      = min(delay, maxDelay)
      = delay + random(0, jitter)

// Default values:
initialDelay = 1 second
multiplier = 2.0
maxDelay = 60 seconds
jitter = enabled (prevent thundering herd)

// Example sequence:
Attempt 1: wait 1s
Attempt 2: wait 2s
Attempt 3: wait 4s
Attempt 4: wait 8s
Attempt 5: wait 16s
Attempt 6: wait 32s
Attempt 7: wait 60s (capped)
...
```

**Per-Error Retry Configuration:**

```yaml
retry:
  rate_limit_exceeded:
    max_retries: 5
    initial_delay_ms: 5000
    jitter: true

  server_unavailable:
    max_retries: 10
    initial_delay_ms: 10000
    jitter: true

  connection_timeout:
    max_retries: 3
    initial_delay_ms: 3000
    jitter: true
```

---

## Part 8: Metrics & Observability

### 8.1 Prometheus Metrics

**Connection Metrics:**

```
cloudbridge_client_bytes_total{direction="sent"}
cloudbridge_client_bytes_total{direction="received"}
cloudbridge_client_connections_active
cloudbridge_client_tunnels_active
cloudbridge_client_heartbeat_latency_ms (histogram)
cloudbridge_client_p2p_sessions
cloudbridge_client_transport_mode{mode="quic|grpc|websocket"}
```

**Error Metrics:**

```
cloudbridge_client_errors_total{error_type="invalid_token|rate_limit|timeout|..."}
cloudbridge_client_connection_failures_total
cloudbridge_client_heartbeat_failures_total
cloudbridge_client_reconnection_attempts_total
```

**Performance Metrics:**

```
cloudbridge_client_latency_ms (histogram, percentiles: p50, p95, p99)
cloudbridge_client_throughput_mbps
cloudbridge_client_packet_loss_percent
cloudbridge_client_jitter_ms
```

### 8.2 Structured Logging

**Log Format:**

```json
{
  "timestamp": "2025-11-04T15:30:00.123Z",
  "level": "info",
  "component": "relay.client",
  "event": "connected",
  "relay_host": "edge.2gc.ru",
  "transport": "quic",
  "latency_ms": 42.5,
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_id": "req-12345",
  "duration_ms": 2500
}
```

**Log Levels:**

```
DEBUG: Detailed diagnostic info
  → Used for troubleshooting connection issues

INFO: Operational events
  → Connected, authenticated, peer discovered, tunnel created

WARN: Potentially problematic conditions
  → High latency, packet loss detected, retry in progress

ERROR: Error conditions requiring attention
  → Connection failed, auth error, tunnel closed
```

---

## Part 9: Integration with Architecture

### 9.1 Client in 8-Step Pipeline

The CloudBridge Client operates primarily as the **initiator** for the 8-step architecture:

```
Client System              CloudBridge Architecture

┌──────────────────┐
│  Client App      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐  Step 1 ──→  DNS Network
│  Client Config   │            (Discover relay)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐  Step 2 ──→  Control Plane
│  JWT/OIDC Auth   │            (Validate token)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐  Step 3 ──→  DDoS Protection
│  Connect Relay   │            (Threat check)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐  Step 4 ──→  Scalable Relay
│  P2P Mesh / Tun  │            (Data transmission)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐  Step 5 ──→  Monitoring
│  Metrics Report  │            (Collect metrics)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐  Step 6 ──→  AI Service
│  View Dashboard  │            (Analyze traffic)
└──────────────────┘
                    Step 7-8 ──→  Dashboard
                                (Visualize)
```

### 9.2 Client-Relay Communication

**Interaction Model:**

```
Client                          Relay (Step 4)
├─ Send: JWT token
│  ├─ Validate: Control Plane (Step 2)
│  └─ Extract: tenant_id, permissions
│
├─ Threat Check
│  └─ DDoS Protection (Step 3)
│     └─ ML inference: allow/block
│
├─ Data Transmission
│  ├─ QUIC (primary)
│  ├─ Fallback: gRPC, WebSocket
│  └─ NAT Traversal: ICE/STUN/TURN
│
├─ Heartbeat
│  └─ Every 30 seconds
│     └─ Exponential backoff on failure
│
├─ P2P Mesh
│  ├─ Discover peers
│  ├─ WireGuard overlay
│  └─ Tenant isolation
│
└─ Metrics
   ├─ Report to Monitoring (Step 5)
   └─ Dashboard (Step 7-8)
```

### 9.3 Tenant Isolation in Client

**Client enforces multi-tenancy at every level:**

```
1. Authentication
   └─ JWT contains custom:tenant_id claim

2. Configuration
   └─ Mesh networks per tenant
   └─ L3 overlay via WireGuard per tenant

3. Peer Discovery
   └─ Only discover peers with same tenant_id
   └─ Filter P2P results by tenant

4. Networking
   └─ WireGuard interface per tenant
   └─ Private CIDR per tenant (10.0.0.0/24)

5. Metrics
   └─ All metrics tagged with tenant_id
   └─ Isolated Prometheus scrape endpoints

6. Audit Logging
   └─ All actions logged with tenant context
   └─ 90-day retention per tenant
```

---

## Part 10: Configuration Reference

### 10.1 Complete Configuration Example

```yaml
# Relay server configuration
relay:
  host: "edge.2gc.ru"
  scheme: "https"
  ports:
    quic: 5553
    grpc: 5554
    websocket: 5555
    stun: 19302
    turn: 3478
    derp: 3479
    masque: 8443

  # Connection parameters
  tls:
    enabled: true
    min_version: "1.3"
    verify_cert: true
    ca_file: "/etc/ssl/certs/ca-bundle.crt"

  # Connection timeout and retry
  connect_timeout_ms: 5000
  read_timeout_ms: 10000
  write_timeout_ms: 10000

# Authentication configuration
auth:
  type: "jwt"  # or "oidc"

  # For JWT direct:
  token: "${CLOUDBRIDGE_TOKEN}"  # From env var

  # For OIDC (Zitadel):
  oidc:
    issuer_url: "https://zitadel.2gc.io"
    client_id: "cloudbridge-client"
    client_secret: "${ZITADEL_SECRET}"
    audience: "cloudbridge-client"
    scopes: ["openid", "profile", "email"]
    redirect_uri: "http://localhost:8080/callback"

  # Token storage
  token_storage: "keyring"  # or "file"
  keyring_service: "cloudbridge"

# P2P mesh networking
p2p:
  enabled: true
  heartbeat_interval: 30s
  peer_discovery_interval: 30s
  max_connections: 100

  # ICE/NAT traversal
  ice:
    stun_servers:
      - "stun:edge.2gc.ru:19302"
      - "stun:stun.l.google.com:19302"

    turn_servers:
      - url: "turn:edge.2gc.ru:3478"
        username: "${TURN_USER}"
        credential: "${TURN_PASS}"

    derp_servers:
      - "edge.2gc.ru:3479"

  # Mesh configuration
  mesh_config:
    peerIP: "10.0.0.5"
    tenantCIDR: "10.0.0.0/24"
    wireguard:
      private_key: "${WG_PRIVATE_KEY}"
      address: "10.0.0.5/32"
      mtu: 1420

# Transport configuration
transport:
  mode: "auto"  # "auto", "quic", "grpc", "websocket"
  prefer_protocol: "quic"
  fallback_enabled: true
  health_check_interval: 30s

  # QUIC-specific
  quic:
    initial_rtt_ms: 100
    max_idle_timeout_ms: 30000
    packet_loss_threshold: 0.05

# Tunnel (port forwarding)
tunnels: []
  # - local_port: 3389
  #   remote_host: "remote.example.com"
  #   remote_port: 3389

# Metrics and observability
metrics:
  enabled: true
  prometheus_port: 9090

  pushgateway:
    enabled: true
    push_url: "http://localhost:9091"
    push_interval: 15s

  # Tag metrics with tenant
  tenant_labels: true

# Logging configuration
logging:
  level: "info"  # "debug", "info", "warn", "error"
  format: "json"  # or "text"
  output: "stdout"  # or file path

  # Log rotation (if file output)
  max_size_mb: 100
  max_backups: 5
  max_age_days: 30

# Performance tuning
performance:
  buffer_size: 65536
  max_concurrent_tunnels: 100
  socket_send_buffer: 2097152
  socket_recv_buffer: 2097152

  # Connection pooling
  connection_pool:
    max_idle_conns: 100
    max_idle_conns_per_host: 10
    idle_conn_timeout_seconds: 60

# Service configuration
service:
  name: "cloudbridge-client"
  description: "CloudBridge Relay Client"

  # Auto-restart on failure
  auto_restart: true
  restart_delay_seconds: 5

  # User to run as (systemd/launchd)
  user: "cloudbridge"
  group: "cloudbridge"
```

---

## Part 11: Deployment Scenarios

### 11.1 Individual User Tunnel

```
User Laptop            Relay           Remote Server
    │                   │                    │
    ├─ RDP to 127.0.0.1:3389
    │  (client tunnel)
    └─────────────────→ │ (QUIC)
                        │
                        ├─ Threat check (DDoS)
                        │
                        ├─ Forward to remote:3389
                        │                    │
                        │←─── RDP traffic ───┤
                        │
    ←───────────────────┤
    Display remote desktop
```

### 11.2 Company Network Mesh

```
Office (Tenant A)      Relay          Remote Office (Tenant A)
    ├─ Client A1          │                ├─ Client A2
    ├─ Client A2          │                ├─ Client A3
    └─ Client A3          │                └─ Client A4
         │                 │                    │
         └─────────────────┼────────────────────┘
                        P2P Mesh
                   (All in Tenant A)
                   Isolated from B

Branch (Tenant B)
    ├─ Client B1          │
    ├─ Client B2          │
    └─ Client B3          │
         │                 │
         └─────────────────┼──────────┐
                        P2P Mesh
                   (All in Tenant B)
                   Isolated from A
```

### 11.3 Mobile Device + Enterprise Network

```
Mobile Device          Relay         Enterprise Network
  (Cellular)            │                    │
     │                   │                    │
     ├─ QUIC attempt     │                    │
     │  (usually blocked)│
     │                   │
     ├─ Fallback:        │
     │  WebSocket over   │
     │  HTTPS (port 443) │
     │  (usually allowed)│
     │                   │
     ├─ via TURN relay   │
     │  (if direct fails)│
     │                   │
     └──────wss://───────┼────────→ Enterprise VPN
                        │           or Tunnel
         Connects to    │
         office P2P mesh
```

---

## Part 12: Troubleshooting & Diagnostics

### 12.1 Common Issues & Solutions

**Issue 1: Connection Timeout**

```
Error: ErrConnectionTimeout
       No response from relay after 5 seconds

Diagnosis:
1. Check relay availability
   $ dig edge.2gc.ru
   $ nc -zv edge.2gc.ru 5553

2. Check firewall rules
   $ sudo iptables -L -n | grep 5553

3. Check DNS resolution
   $ nslookup edge.2gc.ru

4. Increase timeout
   $ cloudbridge-client \
     --connect-timeout 15000 \
     p2p --config config.yaml
```

**Issue 2: Authentication Failed**

```
Error: ErrInvalidToken
       Token validation failed

Diagnosis:
1. Check token validity
   $ echo $CLOUDBRIDGE_TOKEN | cut -d. -f2 | base64 -d | jq .

2. Check expiration
   $ echo $CLOUDBRIDGE_TOKEN | cut -d. -f2 | base64 -d | jq .exp
   $ date +%s  # Current timestamp

3. Verify issuer
   $ echo $CLOUDBRIDGE_TOKEN | cut -d. -f2 | base64 -d | jq .iss

4. Re-authenticate
   $ cloudbridge-client init --reauth
```

**Issue 3: No Peers Discovered**

```
Error: P2P mesh started, 0 peers discovered

Diagnosis:
1. Check relay is healthy
   $ cloudbridge-client health --config config.yaml

2. Check tenant isolation
   $ echo $CLOUDBRIDGE_TOKEN | cut -d. -f2 | base64 -d | jq .custom

3. Enable debug logging
   $ cloudbridge-client \
     --log-level debug \
     p2p --config config.yaml

4. Check if other peers are online
   $ # Query relay via health check endpoint
```

### 12.2 Debug Mode

```bash
# Enable debug logging
./cloudbridge-client \
  --log-level debug \
  --verbose \
  p2p --config config.yaml

# Output detailed logs including:
# - Network stack details
# - Protocol handshakes
# - ICE candidate gathering
# - Peer discovery process
# - Metrics collection

# Save logs to file
./cloudbridge-client \
  --log-level debug \
  --log-file /tmp/cloudbridge.log \
  p2p --config config.yaml
```

---

## Part 13: Client Status & Roadmap

### 13.1 Implementation Status Summary

| Component | Status | Completeness |
|-----------|--------|--------------|
| Relay Client Core | Complete | 100% |
| JWT Authentication | Complete | 100% |
| OIDC (Zitadel) | Complete | 100% |
| P2P Mesh | Complete | 100% |
| QUIC Transport | Complete | 100% |
| gRPC Fallback | Complete | 100% |
| WebSocket Fallback | Complete | 100% |
| WireGuard L3 Overlay | Complete | 100% |
| TCP Tunneling | Complete | 100% |
| Heartbeat/Keep-Alive | Complete | 100% |
| Configuration System | Complete | 100% |
| Metrics Collection | Complete | 100% |
| Error Handling | Complete | 100% |
| Service Integration | Complete | 100% |
| Cross-Platform | Complete | 100% |
| OS Keyring | Complete | 100% |
| Health Checks | Complete | 100% |
| MASQUE Protocol | Partial | 40% |
| SLO Controller | Partial | 30% |
| Synthetic Probes | Partial | 30% |
| Dashboard Integration | Partial | 50% |

### 13.2 Future Roadmap

**Q4 2025:**
- Complete MASQUE protocol integration
- Add more diagnostic capabilities
- Enhanced error messages and troubleshooting guides

**Q1 2026:**
- Complete SLO tracking and monitoring
- Synthetic probes for network diagnostics
- Full dashboard integration

**Q2 2026:**
- Mobile SDK (iOS/Android)
- Advanced analytics on client metrics
- Hardware TPM support

---

## References & Integration Points

### Architectural References

1. **Control Plane (Step 2):** Client authenticates here with JWT
2. **DDoS Protection (Step 3):** Threat check happens before data transmission
3. **Scalable Relay (Step 4):** Main endpoint for P2P and tunneling
4. **Monitoring (Step 5):** Client reports metrics here
5. **AI Service (Step 6):** Analyzes client traffic patterns
6. **Dashboard (Step 7-8):** Displays client metrics and status

### Configuration References

- JWT format: See **REQUIREMENTS MATRIX** → Section 2: Control Plane → Output Specifications
- P2P mesh: See **TENANT ISOLATION ARCHITECTURE** → Layer 1: Network Isolation
- Metrics: See **REQUIREMENTS MATRIX** → Section 5: Monitoring
- Multi-tenancy: See **TENANT ISOLATION ARCHITECTURE** → Complete isolation model

### External Standards

- RFC 9000: QUIC protocol
- RFC 8446: TLS 1.3
- RFC 3394: ICE (Interactive Connectivity Establishment)
- OpenID Connect Core: OIDC specification
- Prometheus Exposition Format: Metrics standard

---

**Document Status:** COMPLETE
**Last Updated:** November 4, 2025
**Next Review:** When client features are released (quarterly)
**Audience:** Operations, developers, architects
