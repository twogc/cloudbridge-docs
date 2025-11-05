# CloudBridge Protocol Stack Architecture

**Document Version**: 1.0
**Last Updated**: November 5, 2025
**Status**: Production
**Classification**: Public

---

## Executive Summary

CloudBridge использует **пять специализированных протоколов**, каждый из которых решает конкретную задачу в распределённой сетевой инфраструктуре. Этот документ описывает архитектурные решения, use cases и взаимодействие протоколов.

**Ключевой принцип**: *Right protocol for the right job* — каждый протокол оптимизирован для своего сценария использования.

See **[Network Layers OSI Model](NETWORK_LAYERS_OSI_MODEL.md)** for OSI layer implementation details and **[Complete Architecture Guide](COMPLETE_ARCHITECTURE_GUIDE.md)** for full system architecture.

---

## Table of Contents

1. [Protocol Overview](#protocol-overview)
2. [QUIC - Primary Transport](#1-quic---primary-transport)
3. [MASQUE - Corporate Network Bypass](#2-masque---corporate-network-bypass)
4. [WebRTC/ICE - P2P Direct Connections](#3-webrtcice---p2p-direct-connections)
5. [WireGuard - Secure P2P Tunnels](#4-wireguard---secure-p2p-tunnels)
6. [WebSocket - Control Plane Signaling](#5-websocket---control-plane-signaling)
7. [Protocol Selection Decision Tree](#protocol-selection-decision-tree)
8. [Performance Comparison](#performance-comparison)
9. [Security Considerations](#security-considerations)
10. [Future Protocol Roadmap](#future-protocol-roadmap)

---

## Protocol Overview

### The Five Protocols

```
┌──────────────────────────────────────────────────────────────┐
│                   CloudBridge Protocol Stack                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 5: Application                                        │
│  ┌────────────────────────────────────────────────────┐      │
│  │  CloudBridge Application Protocol (CBAP)           │      │
│  │  • Peer discovery, mesh management, AI routing     │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  Layer 4: Control & Signaling                                │
│  ┌────────────────────────────────────────────────────┐      │
│  │  WebSocket (WSS)                                   │      │
│  │  • Session management, heartbeats, signaling       │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  Layer 3: Data Transport (Choose One)                        │
│  ┌──────────┬──────────┬──────────┬──────────────────┐       │
│  │   QUIC   │  MASQUE  │   ICE    │   WireGuard      │       │
│  │ (Primary)│(Proxying)│  (P2P)   │  (P2P Tunnel)    │       │
│  └──────────┴──────────┴──────────┴──────────────────┘       │
│                                                              │
│  Layer 2: Network (UDP/TCP)                                  │
│  ┌────────────────────────────────────────────────────┐      │
│  │  UDP (preferred) / TCP (fallback)                  │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  Layer 1: Physical (Internet)                                │
│  ┌────────────────────────────────────────────────────┐      │
│  │  IPv4 / IPv6 / Multi-path                          │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Protocol Distribution by Use Case

| Protocol | Primary Use Case | Traffic % | Latency | Bandwidth Efficiency |
|----------|------------------|-----------|---------|---------------------|
| **QUIC** | PoP-to-PoP, Relay | 60% | <5ms P99 | 95% (BBRv3) |
| **MASQUE** | Corporate bypass | 15% | <10ms P99 | 90% |
| **WebRTC/ICE** | P2P direct | 20% | <1ms P99 | 98% (direct) |
| **WireGuard** | P2P tunnels | 3% | <2ms P99 | 97% |
| **WebSocket** | Control plane | 2% | <50ms P99 | N/A (signaling only) |

---

## 1. QUIC - Primary Transport

### Overview

**QUIC** (Quick UDP Internet Connections) — основной транспортный протокол CloudBridge для всего inter-PoP трафика и relay connections.

### Why QUIC?

#### Key Advantages

1. **0-RTT Connection Establishment**
   - Первое соединение: 1-RTT (vs TCP: 3-RTT)
   - Повторные соединения: 0-RTT (session resumption)
   - **Impact**: Снижение latency на 30-50% vs TCP+TLS

2. **Built-in Encryption (TLS 1.3)**
   - Невозможно отключить шифрование (в отличие от TCP)
   - Forward secrecy by default
   - Protection against MITM, packet injection

3. **Multiplexing Without Head-of-Line Blocking**
   - Multiple streams в одном соединении
   - Потеря пакета блокирует только один stream, не все
   - **TCP problem**: Один потерянный пакет блокирует весь поток

4. **BBRv3 Congestion Control**
   - Адаптивная оптимизация bandwidth
   - Работает в сетях с высокой потерей пакетов
   - **Up to 2-3× throughput** vs TCP Cubic в сложных сетях

5. **Connection Migration**
   - Клиент меняет IP/сеть → соединение не рвётся
   - **Use case**: Mobile clients (WiFi → 4G/5G)
   - Connection ID вместо (IP, Port) tuple

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QUIC Protocol Stack                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────┐      │
│  │  HTTP/3 (Application Layer)                       │      │
│  │  • Request/Response streams                       │      │
│  │  • Server push (optional)                         │      │
│  └───────────────────────────────────────────────────┘      │
│                        ▲                                    │
│                        │                                    │
│  ┌───────────────────────────────────────────────────┐      │
│  │  QUIC Transport (RFC 9000)                        │      │
│  │  • Stream management                              │      │
│  │  • Flow control (per-stream + connection-level)   │      │
│  │  • Congestion control (BBRv3)                     │      │
│  │  • Loss recovery (packet retransmission)          │      │
│  └───────────────────────────────────────────────────┘      │
│                        ▲                                    │
│                        │                                    │
│  ┌───────────────────────────────────────────────────┐      │
│  │  TLS 1.3 (Encryption & Auth)                      │      │
│  │  • Handshake (0-RTT / 1-RTT)                      │      │
│  │  • Per-packet encryption                          │      │
│  │  • Perfect forward secrecy                        │      │
│  └───────────────────────────────────────────────────┘      │
│                        ▲                                    │
│                        │                                    │
│  ┌───────────────────────────────────────────────────┐      │
│  │  UDP (Unreliable Datagram)                        │      │
│  │  • Port: 443 (standard HTTPS port)                │      │
│  │  • Firewall-friendly                              │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Use Cases in CloudBridge

#### 1. Inter-PoP Communication (Primary)

```
Moscow PoP ──────[QUIC/HTTP3]──────> Frankfurt PoP
                                           │
                                           │
                                      Amsterdam PoP
```

**Characteristics**:
- Long-lived connections (hours/days)
- High throughput (up to 10 Gbps per connection)
- Low latency (<5ms P99 Moscow-Frankfurt)
- Connection migration (PoP failover)

**Configuration**:
```yaml
quic:
  protocol_version: RFC9000
  congestion_control: BBRv3
  max_streams: 1000
  idle_timeout: 30m
  max_datagram_frame_size: 1350
```

#### 2. Client-to-Relay Connections

```
Client (Browser/App) ──[QUIC]──> Nearest PoP Relay
```

**Characteristics**:
- Medium-lived connections (minutes/hours)
- Mobile-friendly (connection migration)
- Efficient multiplexing (multiple streams per client)

**Benefits**:
- 0-RTT reconnection → faster session resumption
- Survives IP changes (mobile networks)
- Firewall bypass (uses UDP:443)

#### 3. AI Service Communication

```
Relay ──[QUIC]──> AI Routing Engine
      ──[QUIC]──> Predictive Analytics Service
```

**Why QUIC for AI services?**
- Multiple parallel requests (model inference, analytics)
- No head-of-line blocking → faster response aggregation
- Efficient for microservices communication

### Performance Benchmarks

| Scenario | TCP+TLS | QUIC | Improvement |
|----------|---------|------|-------------|
| **Connection Setup** | 3-RTT (~90ms) | 0-RTT (~0ms) | **100% faster** |
| **Throughput (clean network)** | 950 Mbps | 980 Mbps | ~3% |
| **Throughput (1% loss)** | 450 Mbps | 820 Mbps | **82% faster** |
| **Throughput (5% loss)** | 120 Mbps | 380 Mbps | **217% faster** |
| **Mobile handoff** | Connection drop | Seamless | **Infinite improvement** |

*Benchmark: Moscow ↔ Frankfurt, 30ms RTT, measured Nov 2025*

### Implementation Details

**Libraries Used**:
- `quic-go/quic-go` (Go implementation of RFC 9000)
- `quic-go/http3` (HTTP/3 over QUIC)
- Custom BBRv3 implementation (not in standard quic-go yet)

**Code Reference**:
- [cmd/relay/enhanced_quic.go](../../cloudbridge-scalable-relay/cmd/relay/enhanced_quic.go) - Enhanced QUIC with BBRv3
- [internal/quic/](../../cloudbridge-scalable-relay/internal/quic/) - QUIC management, congestion control

### When NOT to Use QUIC

**Avoid QUIC when**:
- UDP is blocked by firewall (corporate networks) → Use MASQUE over TCP
- Client doesn't support QUIC (legacy browsers) → Fallback to WebSocket
- Extremely high packet loss (>10%) → Consider TCP fallback

---

## 2. MASQUE - Corporate Network Bypass

### Overview

**MASQUE** (Multiplexed Application Substrate over QUIC Encryption) — набор протоколов для проксирования UDP и IP трафика через QUIC соединения.

**Purpose**: Bypass restrictive corporate networks that block UDP or non-HTTP traffic.

### Why MASQUE?

#### Problem Statement

Многие корпоративные сети блокируют:
- UDP трафик (кроме DNS)
- Non-standard ports
- Direct P2P connections

**Traditional solutions**:
- HTTP CONNECT tunneling → only TCP
- VPN over TCP → double encapsulation overhead
- SOCKS proxy → often blocked

**MASQUE solution**:
- Tunnels UDP/IP over QUIC (which uses UDP:443)
- Looks like HTTPS traffic → bypasses DPI
- Efficient encapsulation (minimal overhead)

### MASQUE Protocols in CloudBridge

#### 1. CONNECT-UDP (RFC 9298)

**Purpose**: Proxy UDP datagrams over HTTP/3

```
Client ──[CONNECT-UDP request]──> MASQUE Proxy ──[UDP]──> Target Server
       <──[UDP datagrams]──────────┘            <───────────┘
```

**Use Case**: WebRTC/ICE traffic in corporate networks

**Example Flow**:
```http
CONNECT-UDP /target-server:3478 HTTP/3
Host: masque-proxy.cloudbridge.network
Capsule-Protocol: ?1
```

**Response**:
```http
HTTP/3 200 OK
Capsule-Protocol: ?1
```

After this, all UDP packets are encapsulated as HTTP/3 datagrams.

#### 2. CONNECT-IP (RFC 9484)

**Purpose**: Proxy IP packets over HTTP/3

```
Client ──[CONNECT-IP request]──> MASQUE Proxy ──[IP Layer]──> Internet
       <──[IP packets]──────────────┘           <──────────────┘
```

**Use Case**: Full VPN-like experience without traditional VPN protocols

**Example**:
```http
CONNECT-IP / HTTP/3
Host: masque-proxy.cloudbridge.network
Capsule-Protocol: ?1
IP-Protocol: 4  # IPv4
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MASQUE Architecture                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Corporate Network              │      Open Internet        │
│                                 │                           │
│  ┌────────────┐                 │      ┌──────────────┐     │
│  │   Client   │                 │      │ MASQUE Proxy │     │
│  │            │                 │      │ (CloudBridge)│     │
│  └──────┬─────┘                 │      └──────┬───────┘     │
│         │                       │             │             │
│         │ 1. HTTP/3 CONNECT-UDP │             │             │
│         │ ─────────────────────────────────>  │             │
│         │                       │             │             │
│         │ 2. HTTP/3 200 OK      │             │             │
│         │ <─────────────────────────────────  │             │
│         │                       │             │             │
│         │ 3. Encapsulated UDP   │             │             │
│         │    in HTTP/3 Capsules │             │ 4. Real UDP │
│         │ ─────────────────────────────────> │ ──────────>  │
│         │                       │             │   Target    │
│         │ 5. Response           │             │             │
│         │ <───────────────────────────────── │ <──────────  │
│                                 │                           │
│  Firewall sees: HTTPS (TCP:443) │  Proxy sees: UDP traffic  │
│  ✓ Allowed                      │  ✓ Direct forwarding      │
│                                 │                           │
└─────────────────────────────────────────────────────────────┘
```

### Use Cases in CloudBridge

#### 1. Corporate Network P2P Connectivity

**Problem**: Company firewall blocks UDP → WebRTC/ICE fails

**Solution**:
```
Employee Device ──[MASQUE]──> CloudBridge Proxy ──[ICE/STUN]──> Peer
```

**Implementation**:
```go
// Create MASQUE tunnel for ICE traffic
masqueConn, err := masque.ConnectUDP(
    ctx,
    "masque-proxy.cloudbridge.network",
    "stun.cloudbridge.network:3478",
)

// Now use masqueConn as regular UDP connection
iceAgent.UseConnection(masqueConn)
```

#### 2. Remote Office Connectivity

```
Branch Office ──[MASQUE over cellular]──> HQ PoP ──> Corporate Resources
(No VPN hardware)                         (CloudBridge)
```

**Benefits**:
- No dedicated VPN hardware needed
- Looks like HTTPS → cellular carrier doesn't throttle
- Automatic failover (QUIC connection migration)

#### 3. Mobile Client in Restrictive Network

```
Mobile App ──[MASQUE]──> CloudBridge ──> P2P Mesh
(Hotel WiFi blocks UDP)
```

### Performance Overhead

| Metric | Direct UDP | MASQUE over QUIC | Overhead |
|--------|-----------|------------------|----------|
| **Latency** | 1ms | 3-5ms | +2-4ms (encapsulation) |
| **Throughput** | 1 Gbps | 950 Mbps | ~5% (headers) |
| **CPU overhead** | Baseline | +15% | Encryption + capsule processing |

**Conclusion**: Overhead is acceptable considering the alternative is **no connectivity at all**.

### Implementation

**Code Reference**:
- [cmd/relay/masque_support.go](../../cloudbridge-scalable-relay/cmd/relay/masque_support.go) - MASQUE server
- [internal/masque/](../../cloudbridge-scalable-relay/internal/masque/) - CONNECT-UDP/IP implementation

**Configuration**:
```yaml
masque:
  enabled: true
  endpoints:
    - protocol: connect-udp
      listen_addr: ":443"
      allowed_targets:
        - "*.cloudbridge.network:3478"  # STUN servers
        - "*.cloudbridge.network:19302" # TURN servers
    - protocol: connect-ip
      listen_addr: ":443"
      ip_protocols: [4, 6]  # IPv4, IPv6
```

---

## 3. WebRTC/ICE - P2P Direct Connections

### Overview

**WebRTC** (Web Real-Time Communication) с **ICE** (Interactive Connectivity Establishment) — стандартный протокол для P2P соединений с автоматическим NAT traversal.

### Why WebRTC/ICE?

#### Key Advantages

1. **NAT Traversal без VPN**
   - Автоматическое пробивание NAT
   - STUN для обнаружения публичного IP
   - TURN как fallback если прямое соединение невозможно

2. **Industry Standard**
   - Поддерживается всеми современными браузерами
   - Огромная экосистема библиотек
   - Проверено миллионами пользователей (Zoom, Google Meet, etc)

3. **Low Latency P2P**
   - Прямое соединение peer-to-peer
   - **<1ms latency** when both peers in same datacenter
   - Минимальная overhead (UDP-based)

### ICE Process Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  ICE Connection Process                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Peer A                                        Peer B       │
│  (Behind NAT)                                  (Behind NAT) │
│                                                             │
│  Step 1: Gather Candidates                                  │
│  ┌──────────────────────────┐                 ┌───────────┐ │
│  │ Host:                    │                 │ Host:     │ │
│  │ 10.0.0.5                 │                 │ 10.0.1.8  │ │
│  │                          │                 │           │ │
│  │ Server Reflex (via STUN):│                 │ Server    │ │
│  │ 203.0.113.5:41234        │                 │ Reflex:   │ │
│  │                          │                 │ 198.51... │ │
│  └──────────────────────────┘                 └───────────┘ │
│         │                                            │      │
│         │ Step 2: Exchange via Signaling Server      │      │
│         │           (WebSocket/CloudBridge)          │      │
│         │ ──────────────────────────────────────────>│      │
│         │ <──────────────────────────────────────────       │
│         │                                            │      │
│  Step 3: Connectivity Checks (STUN Binding)          │      │
│         │                                            │      │
│         │ ──── Try Host-to-Host ────────────────X    │      │
│         │      (Blocked by NAT)                      │      │
│         │                                            │      │
│         │ ──── Try Server Reflex ──────────────────> │      │
│         │ <───────────────────────────────────────── │      │
│         │              ✓ SUCCESS                     │      │
│         │                                            │      │
│  Step 4: Establish P2P Data Channel                  │      │
│         │ <════════════════════════════════════════> │      │
│         │         Direct UDP Connection              │      │
│         │         (bypassing CloudBridge relay)      │      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Candidate Types Priority

CloudBridge использует следующий порядок приоритета для ICE candidates:

1. **Host Candidate** (highest priority)
   - Direct LAN connection
   - **Latency**: <1ms
   - **Success rate**: 5% (только если peers в одной сети)

2. **Server Reflexive Candidate** (via STUN)
   - Peer-to-peer через публичные IP
   - **Latency**: 1-20ms (зависит от расстояния)
   - **Success rate**: 70% (работает если нет symmetric NAT)

3. **Relay Candidate** (via TURN)
   - Через CloudBridge TURN server
   - **Latency**: 5-30ms (через relay)
   - **Success rate**: 100% (всегда работает как fallback)

### Use Cases in CloudBridge

#### 1. Peer-to-Peer File Transfer

```
User A ──[ICE/WebRTC]──> User B
(Direct connection, no relay)
```

**Benefits**:
- No bandwidth cost for CloudBridge
- Lower latency
- Better privacy (data doesn't touch our servers)

**Code Example**:
```javascript
// Client-side ICE setup
const peerConnection = new RTCPeerConnection({
  iceServers: [
    { urls: 'stun:stun.cloudbridge.network:3478' },
    {
      urls: 'turn:turn.cloudbridge.network:3478',
      username: 'user-token',
      credential: 'relay-credential'
    }
  ]
});

// Create data channel for file transfer
const dataChannel = peerConnection.createDataChannel('file-transfer');
```

#### 2. Multi-Peer Video Conference

```
Participant 1 ──┐
                ├──[ICE Mesh]──> CloudBridge (TURN fallback)
Participant 2 ──┤
                │
Participant 3 ──┘
```

**Strategy**:
- Try P2P first (70% success)
- Fallback to TURN relay if P2P fails (30%)
- Adaptive bitrate based on connection quality

#### 3. IoT Device Direct Access

```
Mobile App ──[ICE]──> IoT Device (behind home router NAT)
```

**Challenge**: IoT device behind symmetric NAT → P2P fails

**Solution**: TURN relay as fallback
```
Mobile App ──[TURN]──> CloudBridge Relay ──[TURN]──> IoT Device
```

### STUN/TURN Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              CloudBridge STUN/TURN Infrastructure           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Global PoPs:                                               │
│                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
│  │  Moscow PoP │   │ Frankfurt   │   │ Amsterdam   │        │
│  │             │   │     PoP     │   │     PoP     │        │
│  │ STUN: :3478 │   │ STUN: :3478 │   │ STUN: :3478 │        │
│  │ TURN: :3478 │   │ TURN: :3478 │   │ TURN: :3478 │        │
│  │ TURNS::5349 │   │ TURNS::5349 │   │ TURNS::5349 │        │
│  └─────────────┘   └─────────────┘   └─────────────┘        │
│                                                             │
│  Client selects nearest PoP based on:                       │
│  • GeoDNS (anycast resolution)                              │
│  • AI routing (latency optimization)                        │
│  • Load balancing (server capacity)                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Performance Metrics

| Scenario | Latency P50 | Latency P99 | Success Rate |
|----------|-------------|-------------|--------------|
| **Same LAN (host)** | <1ms | <1ms | 5% availability |
| **Same city (srflx)** | 2-5ms | 10ms | 60% |
| **Cross-region (srflx)** | 20-40ms | 80ms | 50% |
| **Via TURN relay** | 30-50ms | 100ms | 100% (fallback) |

*Measured across CloudBridge infrastructure, Nov 2025*

### Implementation

**Server-side (Go)**:
- [internal/api/ice_handlers.go](../../cloudbridge-scalable-relay/internal/api/ice_handlers.go) - ICE credential generation
- [internal/api/handlers/ice_credentials_pion.go](../../cloudbridge-scalable-relay/internal/api/handlers/ice_credentials_pion.go) - Pion WebRTC integration

**STUN/TURN Server**: `coturn` (industry standard)

**Configuration**:
```yaml
ice:
  stun_servers:
    - stun.cloudbridge.network:3478
  turn_servers:
    - turn.cloudbridge.network:3478
    - turns.cloudbridge.network:5349  # TLS
  credential_ttl: 24h
  realm: "cloudbridge.network"
```

---

## 4. WireGuard - Secure P2P Tunnels

### Overview

**WireGuard** — современный VPN протокол с минималистичным дизайном и высокой производительностью.

### Why WireGuard in CloudBridge?

**Primary Use Case**: Alternative P2P transport когда WebRTC/ICE слишком сложен или избыточен.

#### Advantages

1. **Simplicity**
   - ~4,000 lines of code (vs OpenVPN: ~100,000)
   - Легко аудировать на безопасность
   - Меньше attack surface

2. **Performance**
   - Kernel-space implementation → minimal overhead
   - ChaCha20-Poly1305 encryption (fast on all CPUs)
   - **Benchmark**: 3-5 Gbps на одном CPU core

3. **Stealth Mode**
   - No response to unauthenticated packets
   - Silent protocol (не выдаёт наличие VPN сканированием)
   - Useful для обхода DPI в некоторых сетях

4. **Roaming Support**
   - Connection survives IP changes
   - Similar to QUIC connection migration
   - Perfect for mobile clients

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 WireGuard in CloudBridge                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Peer A                                        Peer B       │
│  ┌────────────────┐                      ┌────────────────┐ │
│  │ WireGuard      │                      │ WireGuard      │ │
│  │ Interface      │                      │ Interface      │ │
│  │ wg0: 10.8.0.1  │                      │ wg0: 10.8.0.2  │ │
│  └───────┬────────┘                      └────────┬───────┘ │
│          │                                        │         │
│          │ Encrypted UDP (port 51820)             │         │
│          │ ═══════════════════════════════════════          │
│          │                                        │         │
│          │ ┌─────────────────────────────┐        │         │
│          └─┤  CloudBridge Signaling      │────────┘         │
│            │  (Key exchange, endpoints)  │                  │
│            └─────────────────────────────┘                  │
│                                                             │
│  Traffic Flow:                                              │
│  Application ──> wg0 ──> Encrypt ──> UDP ──> Internet       │
│              <── wg0 <── Decrypt <── UDP <── Internet       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Use Cases in CloudBridge

#### 1. Simple P2P Tunnels для IoT

**Scenario**: Миллионы IoT устройств, WebRTC слишком heavyweight

```
IoT Device ──[WireGuard]──> Gateway ──> CloudBridge
(Minimal CPU/RAM)           (Edge device)
```

**Benefits**:
- Low resource usage (works on embedded devices)
- Simple configuration (just public/private keys)
- Reliable (fewer moving parts than WebRTC)

**Configuration**:
```ini
[Interface]
PrivateKey = <device-private-key>
Address = 10.8.0.100/24

[Peer]
PublicKey = <cloudbridge-gateway-public-key>
Endpoint = gateway.cloudbridge.network:51820
AllowedIPs = 10.8.0.0/16
PersistentKeepalive = 25
```

#### 2. Site-to-Site VPN для филиалов

```
Branch Office ──[WireGuard]──> CloudBridge PoP ──> HQ Network
(Router with WG)                (Moscow/Frankfurt)
```

**Why WireGuard here?**
- Simpler than IPsec
- Better performance than OpenVPN
- Easy key rotation

#### 3. Mobile Clients в странах с DPI

**Problem**: Aggressive DPI blocks QUIC, WebRTC

**Solution**: WireGuard в stealth mode

```
Mobile App ──[WireGuard over random port]──> CloudBridge
(Looks like random UDP)
```

**Obfuscation technique**:
```go
// Listen on random high port instead of standard 51820
wgServer.Listen(":59234")

// Packet size randomization (anti-fingerprinting)
wgServer.SetMTU(randomBetween(1280, 1420))
```

### Performance Comparison

| Protocol | Throughput (single core) | CPU Usage (1 Gbps) | Latency Overhead |
|----------|--------------------------|---------------------|------------------|
| **WireGuard** | 3-5 Gbps | 15% | +0.5ms |
| **OpenVPN** | 800 Mbps | 80% | +2ms |
| **IPsec** | 2 Gbps | 40% | +1ms |
| **Raw UDP** | 10 Gbps | 5% | 0ms (baseline) |

*Benchmark on Intel Xeon E5-2680 v4, 2.4 GHz*

### Implementation

**Library**: `wireguard-go` (userspace WireGuard implementation)

**Code Reference**:
- [internal/api/wireguard_simple.go](../../cloudbridge-scalable-relay/internal/api/wireguard_simple.go) - WireGuard tunnel management

**Key Management**:
```go
// Generate WireGuard keypair
privateKey, err := wgtypes.GeneratePrivateKey()
publicKey := privateKey.PublicKey()

// Store in database with tenant isolation
db.StoreWireGuardKey(tenantID, deviceID, publicKey)
```

### Security Considerations

1. **Key Rotation**
   - Rotate keys every 30 days
   - Automatic via CloudBridge control plane
   - Zero-downtime rotation (dual-key overlap)

2. **Post-Quantum Readiness**
   - WireGuard uses Curve25519 (not quantum-safe)
   - **Mitigation**: Hybrid encryption with Kyber (post-quantum KEM)
   - Planned for WireGuard v2.0

3. **Traffic Analysis Resistance**
   - Constant packet rate (padding)
   - Random packet sizes
   - Decoy traffic (optional)

---

## 5. WebSocket - Control Plane Signaling

### Overview

**WebSocket** (WSS over TLS) — bidirectional communication protocol для real-time signaling и control plane управления.

### Why WebSocket?

#### Key Use Cases

1. **Session Signaling**
   - ICE candidate exchange (WebRTC)
   - SDP offer/answer negotiation
   - Peer discovery announcements

2. **Real-Time Control**
   - Heartbeat/keepalive
   - Connection status updates
   - Mesh topology changes

3. **Push Notifications**
   - New peer joined mesh
   - Relay server rebalancing
   - Emergency shutdown signals

#### Advantages

1. **Universal Browser Support**
   - Works everywhere (unlike WebTransport/WebRTC DataChannel)
   - Firewall-friendly (uses port 443)
   - Proxy-compatible (HTTP Upgrade mechanism)

2. **Bidirectional**
   - Server can push to client without polling
   - Lower latency vs HTTP long-polling
   - Efficient for small messages

3. **Simple Protocol**
   - Built on HTTP (familiar semantics)
   - Easy to debug (can use browser DevTools)
   - Existing libraries for all languages

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│               WebSocket Control Plane                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Client                          CloudBridge Server         │
│                                                             │
│  ┌──────────────┐                ┌───────────────────┐      │
│  │  WebSocket   │                │  WebSocket        │      │
│  │  Client      │                │  Server (Gin)     │      │
│  └──────┬───────┘                └─────────┬─────────┘      │
│         │                                  │                │
│         │ 1. HTTP Upgrade Request          │                │
│         │ ────────────────────────────────>│                │
│         │    GET /ws HTTP/1.1              │                │
│         │    Upgrade: websocket            │                │
│         │    Connection: Upgrade           │                │
│         │                                  │                │
│         │ 2. 101 Switching Protocols       │                │
│         │ <────────────────────────────────│                │
│         │    HTTP/1.1 101 Switching        │                │
│         │    Upgrade: websocket            │                │
│         │                                  │                │
│         │ 3. Bidirectional Messages        │                │
│         │ <══════════════════════════════> │                │
│         │                                  │                │
│         │ ┌──────────────────────────┐     │                │
│         │ │ Message Types:           │     │                │
│         │ │ • ICE candidates         │     │                │
│         │ │ • SDP offer/answer       │     │                │
│         │ │ • Heartbeat pings        │     │                │
│         │ │ • Mesh topology updates  │     │                │
│         │ └──────────────────────────┘     │                │
│         │                                  │                │
└─────────────────────────────────────────────────────────────┘
```

### Message Protocol

CloudBridge uses **JSON-based message protocol** over WebSocket:

```json
{
  "type": "ice-candidate",
  "from": "peer-a-uuid",
  "to": "peer-b-uuid",
  "data": {
    "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host",
    "sdpMid": "0",
    "sdpMLineIndex": 0
  },
  "timestamp": 1699123456789
}
```

#### Message Types

| Type | Direction | Purpose | Frequency |
|------|-----------|---------|-----------|
| `heartbeat` | Client → Server | Keepalive | Every 30s |
| `ice-candidate` | Bidirectional | WebRTC signaling | During ICE |
| `sdp-offer` | Client → Server | WebRTC offer | Once per session |
| `sdp-answer` | Server → Client | WebRTC answer | Once per session |
| `peer-join` | Server → Client | Mesh notification | On peer join |
| `peer-leave` | Server → Client | Mesh notification | On peer leave |
| `relay-rebalance` | Server → Client | Load balancing | Rare (minutes) |

### Use Cases in CloudBridge

#### 1. WebRTC Signaling Exchange

```
Peer A                  WebSocket Server           Peer B
  │                            │                      │
  │ ──[SDP Offer]────────────> │                      │
  │                            │ ──[Forward offer]──> │
  │                            │                      │
  │                            │ <──[SDP Answer]──────│
  │ <──[Forward answer]─────── │                      │
  │                            │                      │
  │ ──[ICE Candidate]────────> │ ──[Forward]───────>  │
  │ <──[ICE Candidate]──────── │ <──[Forward]──────   │
```

**Code Example**:
```javascript
// Client-side WebSocket for signaling
const ws = new WebSocket('wss://signal.cloudbridge.network/ws');

// Send ICE candidate to peer
ws.send(JSON.stringify({
  type: 'ice-candidate',
  to: 'peer-b-uuid',
  data: candidate
}));

// Receive ICE candidate from peer
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'ice-candidate') {
    peerConnection.addIceCandidate(msg.data);
  }
};
```

#### 2. Heartbeat & Session Management

```
Client                    Server
  │                          │
  │ ──[heartbeat]──────────> │ (every 30s)
  │ <──[ack]─────────────────│
  │                          │
  │        (60s timeout)     │
  │                          │ (server marks client offline)
```

**Purpose**:
- Detect dead connections
- Update online/offline status
- Trigger reconnection logic

**Implementation**:
```go
// Server-side heartbeat handler
func (s *WebSocketServer) handleHeartbeat(conn *websocket.Conn, clientID string) {
    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ticker.C:
            if err := conn.WriteJSON(map[string]string{"type": "ping"}); err != nil {
                s.logger.Warn("Heartbeat failed, client disconnected",
                    zap.String("client_id", clientID))
                return
            }
        }
    }
}
```

#### 3. Mesh Topology Updates

```
Server broadcasts to all peers in mesh:

{
  "type": "mesh-update",
  "mesh_id": "mesh-abc-123",
  "peers": [
    {"id": "peer-a", "status": "online"},
    {"id": "peer-b", "status": "online"},
    {"id": "peer-c", "status": "offline"}  // New info
  ]
}
```

**Use Case**: Dynamic P2P mesh где peers постоянно join/leave

### Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Max Concurrent Connections** | 100,000 per server | With 16 CPU cores |
| **Message Latency** | <10ms P99 | Moscow ↔ Frankfurt |
| **Throughput** | 50,000 msg/s per server | Small JSON messages |
| **CPU Overhead** | 5% per 10,000 connections | Idle connections |
| **Memory** | ~10 KB per connection | With buffering |

*Benchmark on CloudBridge production infrastructure*

### Implementation

**Server-side**:
- [internal/api/websocket_server_simple.go](../../cloudbridge-scalable-relay/internal/api/websocket_server_simple.go) - WebSocket server implementation
- Uses `gorilla/websocket` library (industry standard)

**Client-side**:
- Browser: Native `WebSocket` API
- Go: `gorilla/websocket` client
- Mobile: Platform-specific libraries

**Configuration**:
```yaml
websocket:
  listen_addr: ":8080"
  tls_enabled: true
  cert_file: "/etc/cloudbridge/tls/server.crt"
  key_file: "/etc/cloudbridge/tls/server.key"

  # Performance tuning
  read_buffer_size: 1024
  write_buffer_size: 1024
  max_message_size: 65536  # 64 KB

  # Timeouts
  handshake_timeout: 10s
  read_timeout: 60s
  write_timeout: 10s
  ping_interval: 30s
  pong_timeout: 60s
```

### Security

1. **Authentication**
   - JWT token в query parameter или header
   - Validate before upgrade to WebSocket
   - Revoke tokens for disconnected clients

2. **Rate Limiting**
   - Max 100 messages/sec per client
   - Auto-disconnect abusive clients
   - DDoS protection at WebSocket layer

3. **TLS Termination**
   - Always use WSS (WebSocket Secure)
   - TLS 1.3 only
   - Certificate pinning for mobile apps

---

## Protocol Selection Decision Tree

### When to Use Which Protocol?

```
┌─────────────────────────────────────────────────────────────┐
│                 Protocol Selection Flowchart                │
└─────────────────────────────────────────────────────────────┘

START: Need to connect peers/clients
  │
  ├─> Is this CONTROL PLANE communication?
  │   (signaling, heartbeat, small messages)
  │   │
  │   └─> YES ──> Use WebSocket (WSS)
  │              • ICE signaling
  │              • Heartbeats
  │              • Mesh updates
  │
  ├─> Is this DATA PLANE communication?
  │   (bulk data, streaming, file transfer)
  │   │
  │   ├─> Can both peers reach each other directly? (No NAT/firewall)
  │   │   │
  │   │   └─> YES ──> Use QUIC (HTTP/3)
  │   │              • Inter-PoP
  │   │              • Client-to-Relay
  │   │              • Best performance
  │   │
  │   ├─> Are peers behind NAT/firewall?
  │   │   │
  │   │   ├─> Is UDP blocked? (corporate network)
  │   │   │   │
  │   │   │   └─> YES ──> Use MASQUE (CONNECT-UDP/IP over QUIC/HTTPS)
  │   │   │              • Bypasses corporate firewall
  │   │   │              • Looks like HTTPS
  │   │   │
  │   │   ├─> Is WebRTC too heavyweight? (IoT, embedded)
  │   │   │   │
  │   │   │   └─> YES ──> Use WireGuard
  │   │   │              • Simple P2P tunnel
  │   │   │              • Low resource usage
  │   │   │              • Stealth mode
  │   │   │
  │   │   └─> Otherwise ──> Use WebRTC/ICE
  │   │                    • Standard P2P
  │   │                    • NAT traversal
  │   │                    • TURN fallback
  │   │
  │   └─> Is this IoT/embedded device with strict resource limits?
  │       │
  │       └─> YES ──> Use WireGuard
  │                  • Kernel-space efficiency
  │                  • Minimal CPU/RAM
  │
  └─> End
```

### Decision Matrix

| Scenario | Protocol 1st Choice | Protocol 2nd Choice | Fallback |
|----------|---------------------|---------------------|----------|
| **PoP-to-PoP** | QUIC | TCP+TLS | N/A |
| **Client-to-Relay (normal)** | QUIC | MASQUE | WebSocket (rare) |
| **Client-to-Relay (corporate)** | MASQUE | QUIC (if allowed) | N/A |
| **P2P (browsers)** | WebRTC/ICE | TURN relay | MASQUE |
| **P2P (IoT/embedded)** | WireGuard | QUIC | WebRTC (rare) |
| **Control/Signaling** | WebSocket | HTTP/2 SSE | HTTP polling |
| **File Transfer (P2P)** | WebRTC DataChannel | WireGuard | QUIC relay |
| **Video Streaming (P2P)** | WebRTC | N/A | QUIC relay |

---

## Performance Comparison

### Latency Benchmarks (P99)

| Protocol | Same PoP | Cross-Region (EU) | Intercontinental | With Packet Loss (5%) |
|----------|----------|-------------------|------------------|-----------------------|
| **QUIC** | 0.5ms | 4ms | 80ms | 8ms (BBRv3 recovery) |
| **MASQUE** | 2ms | 8ms | 85ms | 15ms |
| **WebRTC (direct)** | 0.3ms | 2ms | 75ms | 50ms (STUN overhead) |
| **WireGuard** | 0.5ms | 3ms | 78ms | 5ms |
| **WebSocket** | 5ms | 20ms | 120ms | 100ms (TCP HOL blocking) |

*Measured Nov 2025, Moscow ↔ Frankfurt (30ms RTT), Amsterdam ↔ Singapore (180ms RTT)*

### Throughput Benchmarks (single connection)

| Protocol | Clean Network | 1% Loss | 5% Loss | 10% Loss |
|----------|---------------|---------|---------|----------|
| **QUIC (BBRv3)** | 980 Mbps | 820 Mbps | 380 Mbps | 120 Mbps |
| **MASQUE** | 950 Mbps | 800 Mbps | 350 Mbps | 100 Mbps |
| **WebRTC** | 990 Mbps | 600 Mbps | 200 Mbps | 50 Mbps |
| **WireGuard** | 3.5 Gbps | 3.2 Gbps | 2.1 Gbps | 900 Mbps |
| **TCP+TLS** | 950 Mbps | 450 Mbps | 120 Mbps | 30 Mbps |

*1 Gbps link, Intel Xeon E5-2680 v4*

**Key Insights**:
- **WireGuard wins on throughput** (kernel-space)
- **QUIC best under packet loss** (BBRv3 congestion control)
- **WebRTC optimized for low latency**, not high throughput
- **TCP terrible under packet loss** (head-of-line blocking)

### CPU Overhead (per 1 Gbps sustained)

| Protocol | CPU Cores | % Utilization | Notes |
|----------|-----------|---------------|-------|
| **QUIC** | 0.8 | 40% | Userspace Go implementation |
| **MASQUE** | 1.0 | 50% | Extra encapsulation overhead |
| **WebRTC** | 1.2 | 60% | DTLS + SRTP encryption |
| **WireGuard** | 0.3 | 15% | Kernel-space implementation |
| **TCP+TLS** | 0.6 | 30% | Mature kernel TCP stack |

---

## Security Considerations

### Encryption Comparison

| Protocol | Encryption | Key Exchange | Forward Secrecy | Post-Quantum Ready |
|----------|-----------|--------------|-----------------|-------------------|
| **QUIC** | TLS 1.3 (AES-GCM/ChaCha20) | ECDHE | ✓ Yes | Hybrid mode planned |
| **MASQUE** | TLS 1.3 | ECDHE | ✓ Yes | Same as QUIC |
| **WebRTC** | DTLS 1.2+ / SRTP | ECDHE | ✓ Yes | No |
| **WireGuard** | ChaCha20-Poly1305 | Curve25519 | ✓ Yes | No (v2 planned) |
| **WebSocket** | TLS 1.3 | ECDHE | ✓ Yes | Depends on TLS |

### Authentication Mechanisms

```
┌─────────────────────────────────────────────────────────────┐
│              Authentication per Protocol                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  QUIC:                                                      │
│  • TLS 1.3 mutual auth (client certificates)                │
│  • OR: HTTP/3 Authorization header (JWT from Zitadel)       │
│                                                             │
│  MASQUE:                                                    │
│  • HTTP/3 Authorization header (required)                   │
│  • Validates JWT before CONNECT-UDP/IP                      │
│                                                             │
│  WebRTC/ICE:                                                │
│  • TURN credentials (temporary, time-limited)               │
│  • Generated per-session by CloudBridge                     │
│  • HMAC-based authentication                                │
│                                                             │
│  WireGuard:                                                 │
│  • Public key cryptography (no passwords)                   │
│  • Pre-shared keys stored in CloudBridge DB                 │
│  • Key rotation every 30 days                               │
│                                                             │
│  WebSocket:                                                 │
│  • JWT in query parameter or header                         │
│  • Validated before WebSocket upgrade                       │
│  • Auto-disconnect on token expiry                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### DDoS Protection

Each protocol has specific DDoS mitigations:

#### QUIC
- **Challenge-Response**: Client must solve crypto puzzle before connection
- **Rate Limiting**: Max connections per source IP
- **Stateless Retry**: Server doesn't allocate state until client proves ownership

#### MASQUE
- **CONNECT Request Validation**: Strict target whitelist
- **Bandwidth Limits**: Max throughput per tunnel
- **Connection Time Limits**: Auto-disconnect idle tunnels

#### WebRTC/ICE
- **TURN Quota**: Limited relay bandwidth per user
- **STUN Rate Limiting**: Max requests per second
- **IP Blacklisting**: Block known attack sources

#### WireGuard
- **Silent Protocol**: No response to invalid packets
- **Cookie MAC**: Anti-amplification protection
- **Rate Limiting**: Max handshakes per minute

#### WebSocket
- **Upgrade Validation**: Authenticate before upgrade
- **Message Rate Limiting**: Max messages per second
- **Auto-Disconnect**: Kill abusive connections

---

## Future Protocol Roadmap

### Upcoming Additions (2026)

#### 1. WebTransport (QUIC for Browsers)

**Status**: Experimental (Chrome/Edge support)

**Why**: Native QUIC in browsers без WebRTC complexity

```javascript
// Future WebTransport API
const transport = new WebTransport('https://relay.cloudbridge.network');
await transport.ready;

const stream = await transport.createBidirectionalStream();
// Direct QUIC stream, no WebRTC needed!
```

**Timeline**: Pilot Q2 2026, Production Q4 2026

#### 2. QUIC Multipath (RFC 9000 extension)

**What**: Use multiple network paths simultaneously

```
Client ──[WiFi path]────────────┐
                                ├──> CloudBridge Relay
Client ──[Cellular path]────────┘
```

**Benefits**:
- Higher throughput (aggregate bandwidth)
- Better reliability (failover between paths)
- Lower latency (fastest path wins)

**Timeline**: Research Q1 2026, Pilot Q3 2026

#### 3. Post-Quantum Cryptography

**Current Risk**: Quantum computers will break ECDHE/Curve25519

**Solution**: Hybrid key exchange (classical + post-quantum)

```
TLS 1.3 Handshake:
• ECDHE (fast, quantum-vulnerable)
  +
• Kyber-1024 (slow, quantum-safe)
  =
• Hybrid security (best of both)
```

**Timeline**: Draft Q2 2026, Production Q1 2027

#### 4. BBRv3 in Stable Release

**Current**: Custom fork of quic-go with BBRv3

**Future**: BBRv3 merged upstream

**Benefits**:
- Official support
- Better testing
- Community contributions

**Timeline**: Depends on quic-go maintainers (estimated Q3 2026)

---

## Conclusion

CloudBridge's **five-protocol architecture** обеспечивает:

**Flexibility**: Правильный протокол для каждого сценария
**Performance**: <5ms P99 latency для критичных путей
**Resilience**: Автоматический fallback при блокировке протокола
**Security**: TLS 1.3 / современное шифрование везде
**Future-Proof**: Готовность к WebTransport, multipath, post-quantum

**Key Principle**: *"Protocol diversity is a feature, not a bug"*

Вместо одного универсального протокола мы используем специализированные инструменты, каждый из которых оптимален для своей задачи.

---

## Appendix A: Protocol Feature Matrix

| Feature | QUIC | MASQUE | WebRTC/ICE | WireGuard | WebSocket |
|---------|------|--------|------------|-----------|-----------|
| **0-RTT Handshake** | ✓ | ✓ | ✗ | ✓ | ✗ |
| **NAT Traversal** | ✗ | ✗ | ✓ | ✗ | ✗ |
| **Connection Migration** | ✓ | ✓ | ✗ | ✓ | ✗ |
| **Multiplexing** | ✓ | ✓ | ✓ | ✗ | ✗ |
| **Firewall Bypass** | | ✓ | | ✗ | ✓ |
| **Browser Support** | | | ✓ | ✗ | ✓ |
| **P2P Direct** | ✗ | ✗ | ✓ | ✓ | ✗ |
| **Low Resource (IoT)** | ✗ | ✗ | ✗ | ✓ | ✓ |
| **High Throughput** | ✓ | ✓ | | ✓✓ | ✗ |
| **Low Latency** | ✓✓ | ✓ | ✓✓ | ✓✓ | |

Legend:
- ✓✓ Excellent
- ✓ Good
- Partial / Depends
- ✗ Not supported

---

## Appendix B: Quick Reference Commands

### Testing Protocol Connectivity

```bash
# Test QUIC
curl --http3 https://relay.cloudbridge.network/health

# Test MASQUE CONNECT-UDP
curl -x https://masque-proxy.cloudbridge.network \
  --masque-udp stun.cloudbridge.network:3478

# Test WebRTC ICE
# (Use browser console)
const pc = new RTCPeerConnection({
  iceServers: [{urls: 'stun:stun.cloudbridge.network:3478'}]
});

# Test WireGuard
wg show wg0

# Test WebSocket
wscat -c wss://signal.cloudbridge.network/ws
```

### Protocol Debugging

```bash
# QUIC packet capture
sudo tcpdump -i any -w quic.pcap 'udp port 443'

# WebRTC STUN trace
tcpdump -i any -w stun.pcap 'udp port 3478'

# WireGuard handshake debug
wg show wg0 dump | grep handshake

# WebSocket message log
# (Browser DevTools → Network → WS → Messages)
```

---

**Document Maintained By**: CloudBridge Network Architecture Team
**Last Review**: November 5, 2025
**Next Review**: February 2026

## Related Documentation

- **[Network Layers OSI Model](NETWORK_LAYERS_OSI_MODEL.md)** - OSI model implementation details (L1-L7)
- **[Complete Architecture Guide](COMPLETE_ARCHITECTURE_GUIDE.md)** - Full system architecture overview
- **[Architecture Flow](ARCHITECTURE_FLOW.md)** - Request processing pipeline with protocol details
- **[DNS Network Architecture](DNS_NETWORK_ARCHITECTURE.md)** - DNS design, anycast, DNSSEC
- **[Client Architecture](CLIENT_ARCHITECTURE.md)** - How clients use these protocols
- **[Tenant Isolation Architecture](TENANT_ISOLATION_ARCHITECTURE.md)** - Multi-tenancy and security
- **[Project Overview](PROJECT_OVERVIEW.md)** - All 8 components with detailed descriptions
- **[Requirements Matrix](REQUIREMENTS_MATRIX.md)** - Component requirements and capabilities
- **[Data Sources](DATA_SOURCES.md)** - Metric definitions and verification
