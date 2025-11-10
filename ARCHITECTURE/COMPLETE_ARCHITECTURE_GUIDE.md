# CloudBridge Complete Architecture Guide

**Version:** 3.1
**Updated:** November 10, 2025
**Status:** Complete Reference with Implementation Details

---

## Table of Contents

1. Architecture Overview
2. Request Processing Pipeline
3. Component Interaction
4. Multi-Tenancy and Isolation
5. Network Architecture
6. Security Model

---

## Architecture Overview

CloudBridge is an enterprise-grade P2P mesh networking platform built on 8 integrated components, spanning 7 OSI layers, with 5 distinct isolation layers for multi-tenancy. See **[Architecture Flow](ARCHITECTURE_FLOW.md)** for detailed request processing flow and **[Project Overview](PROJECT_OVERVIEW.md)** for component descriptions.

### Request Processing Pipeline

```
Client Request
  |
  v
Step 1: DNS Resolution (GeoDNS)
  ├─ Input: relay.cloudbridge.global query
  ├─ Process: Locate nearest PoP by geography
  ├─ Output: Anycast IP of nearest PoP
  ├─ Component: CloudBridge DNS Network
  │  └─ See: [DNS Network Architecture](DNS_NETWORK_ARCHITECTURE.md)
  └─ Latency: < 1ms

  |
  v
Step 2: Credential Validation (Control Plane)
  ├─ Input: Client credentials
  ├─ Process: Validate via Zitadel OIDC
  ├─ Output: JWT token with tenant_id claim
  ├─ Component: CloudBridge Control Plane
  └─ Latency: < 100ms

  |
  v
Step 3: Threat Detection (DDoS Protection)
  ├─ Input: JWT token + incoming traffic
  ├─ Process: ML-based anomaly detection
  ├─ Output: Clean traffic approved or blocked
  ├─ Component: CloudBridge DDoS Protection
  ├─ Capacity: 800,000 RPS
  └─ Latency: < 100ms

  |
  v
Step 4: Data Transmission (Relay PoPs)
  ├─ Input: Clean traffic with valid JWT
  ├─ Process: QUIC + BBRv3 + tenant isolation
  ├─ Output: Data transmitted securely
  ├─ Component: CloudBridge Scalable Relay
  │  └─ See: [Protocol Stack](PROTOCOL_STACK.md), [Network Layers OSI Model](NETWORK_LAYERS_OSI_MODEL.md)
  ├─ Throughput: 100 Gbps per PoP
  └─ Latency: < 5ms (via 1 PoP)

  |
  v
Step 5: Metrics Collection (Monitoring)
  ├─ Input: Connection statistics
  ├─ Process: Collect 300+ metrics per PoP
  ├─ Output: Time-series data to Prometheus
  ├─ Component: CloudBridge Monitoring
  │  └─ See: [Data Sources](DATA_SOURCES.md), [Requirements Matrix](REQUIREMENTS_MATRIX.md)
  └─ Collection Interval: 15 seconds

  |
  v
Step 6: Traffic Analysis (AI Service)
  ├─ Input: Real-time metrics
  ├─ Process: ML-based optimization
  ├─ Output: Route hints, predictions
  ├─ Component: CloudBridge AI Service
  ├─ Framework: TensorFlow 2.12 + PyTorch 2.0
  └─ Latency: < 100ms inference

  |
  v
Step 7: Optimization Feedback (Control Plane)
  ├─ Input: AI recommendations
  ├─ Process: Update policies + routes
  ├─ Output: New configurations pushed
  ├─ Component: CloudBridge Control Plane
  └─ Latency: < 5 seconds

  |
  v
Step 8: Visibility (Dashboard)
  ├─ Input: All system data
  ├─ Process: Real-time visualization
  ├─ Output: Operations team sees status
  ├─ Component: CloudBridge Dashboard
  ├─ Update Interval: 5 seconds real-time
  └─ Latency: < 2 seconds page load

  |
  v
End-to-End Latency: 215ms from client request to full observability
```

### Component Documentation Links

**Step 1 - DNS Resolution:**
- **[DNS Network Architecture](DNS_NETWORK_ARCHITECTURE.md)** - DNS design, anycast, DNSSEC implementation

**Step 2 - Credential Validation:**
- **[Tenant Isolation Architecture](TENANT_ISOLATION_ARCHITECTURE.md)** - JWT authentication and multi-tenancy
- **[Requirements Matrix](REQUIREMENTS_MATRIX.md)** - Control Plane specifications

**Step 3 - Threat Detection:**
- **[Requirements Matrix](REQUIREMENTS_MATRIX.md)** - DDoS Protection capabilities

**Step 4 - Data Transmission:**
- **[Protocol Stack](PROTOCOL_STACK.md)** - Complete protocol layer specifications
- **[Network Layers OSI Model](NETWORK_LAYERS_OSI_MODEL.md)** - L1-L7 implementation details
- **[Project Overview](PROJECT_OVERVIEW.md)** - Scalable Relay component

**Step 5 - Metrics Collection:**
- **[Data Sources](DATA_SOURCES.md)** - Metric definitions and verification
- **[Requirements Matrix](REQUIREMENTS_MATRIX.md)** - Monitoring specifications

**Step 6 - Traffic Analysis:**
- **[Requirements Matrix](REQUIREMENTS_MATRIX.md)** - AI Service capabilities

**Step 7-8 - Optimization & Visibility:**
- **[Requirements Matrix](REQUIREMENTS_MATRIX.md)** - Control Plane and Dashboard specifications

---

## Component Interaction Chain

### Full Request Flow with Isolation

```
CLIENT
  |
  +---> DNS Network (Step 1)
  |       └─ Query: relay.cloudbridge.global
  |       └─ Returns: PoP IP nearest to client
  |       └─ Isolation: Anycast distribution
  |
  +---> Control Plane (Step 2)
  |       ├─ Input: Client credentials
  |       ├─ Process: Zitadel OIDC validation
  |       ├─ Output: JWT with tenant_id claim
  |       └─ Isolation: Tenant extracted to context
  |
  +---> DDoS Protection (Step 3)
  |       ├─ Input: JWT token + traffic
  |       ├─ Process: Validate tenant context
  |       ├─ Process: Check for attacks
  |       ├─ Output: Clean traffic approved
  |       └─ Isolation: Tenant-specific rate limits applied
  |
  +---> Relay PoP (Step 4)
  |       ├─ Input: Clean traffic + valid JWT
  |       ├─ Process: QUIC connection + encryption
  |       ├─ Process: BBRv3 congestion control
  |       ├─ Output: Secure P2P connection
  |       └─ Isolation: Tenant VRF + subnet (10.x.0.0/24)
  |
  +---> Monitoring (Step 5)
  |       ├─ Input: Connection metrics
  |       ├─ Process: Aggregate statistics
  |       ├─ Output: Push to Prometheus
  |       └─ Isolation: Metrics labeled with tenant_id
  |
  +---> AI Service (Step 6)
  |       ├─ Input: Traffic patterns
  |       ├─ Process: ML analysis
  |       ├─ Output: Optimization recommendations
  |       └─ Isolation: Analysis per tenant only
  |
  +---> Control Plane (Step 7)
  |       ├─ Input: AI recommendations
  |       ├─ Process: Update policies
  |       ├─ Output: Deploy new configuration
  |       └─ Isolation: Policies applied per tenant
  |
  +---> Dashboard (Step 8)
  |       ├─ Input: System status
  |       ├─ Process: Real-time visualization
  |       ├─ Output: Visibility to operations
  |       └─ Isolation: RBAC per tenant access
  |
  v
DATA DELIVERED SECURELY AND ISOLATED
```

---

## Multi-Tenancy Architecture

See **[Tenant Isolation Architecture](TENANT_ISOLATION_ARCHITECTURE.md)** for complete multi-tenancy deep dive.

### Five Isolation Layers

#### Layer 1: Network Isolation

Tenants are isolated at the network layer via Kubernetes NetworkPolicies and Calico.

**Kubernetes NetworkPolicy:**
- Default-deny all ingress and egress
- Allow ingress only from same-tenant pods
- Allow egress only to Control Plane
- DNS globally accessible (exception)

**Calico Virtual Routing and Forwarding (VRF):**
- Each tenant gets unique VRF ID (1001, 1002, etc.)
- Each VRF has isolated routing table
- Packets cannot cross VRF boundaries
- Per-tenant subnet assigned from 10.0.0.0/8

**Inheritance Model:**
- NetworkPolicy inherited by all pods in tenant namespace
- VRF inherited by all routes in tenant context
- Default-deny inherited, explicit whitelist required

#### Layer 2: Application-Level Isolation

Tenants are isolated via Zitadel OIDC and JWT tokens.

**JWT Token Structure:**
```
{
  "tenant_id": "tenant-a",
  "sub": "peer-a1",
  "exp": 1699107600,
  "aud": ["cloudbridge"],
  "permissions": {...}
}
```

**Validation at Every Step:**
1. Client sends JWT with request
2. Relay validates JWT signature
3. Relay extracts tenant_id from claims
4. All operations filtered by tenant_id
5. Request rejected if tenant mismatch

**Inheritance Model:**
- Tenant context inherited from JWT to all services
- Permissions inherited from JWT claims
- Service-to-service mTLS carries tenant context
- All API calls must include valid tenant context

#### Layer 3: Resource Isolation

Tenants are isolated via Kubernetes ResourceQuotas and rate limiting.

**Kubernetes ResourceQuota per Tenant:**
- CPU: 100m per tenant
- Memory: 256Mi per tenant
- Max pods: 50 per tenant
- Violations prevent pod creation

**Rate Limiting per Tenant:**
- Max RPS: Configurable (10k for Tenant A, 5k for Tenant B)
- Burst capacity: 1.5x baseline
- Token bucket algorithm
- Circuit breaker for failures

**Inheritance Model:**
- Quota inherited by all pods in namespace
- Rate limits inherited by all services
- Burst capacity cascaded to child services
- Cleanup rules inherited by retention policies

#### Layer 4: Data Isolation

Tenants are isolated at the data layer via IPAM and database filtering.

**IPAM (IP Address Management):**
- Deterministic subnet allocation: SHA256(tenantID + salt)
- Per-tenant subnet: /24 (252 usable IPs)
- Example:
  - Tenant A: 10.1.0.0/24
  - Tenant B: 10.2.0.0/24
  - Tenant C: 10.3.0.0/24

**Per-Peer IP Allocation:**
- SERIALIZABLE transactions prevent race conditions
- Each peer allocated IP from tenant subnet
- IP reused on reconnection if available
- Freed after 24-hour grace period

**Database Row-Level Security:**
- All queries filtered by tenant_id
- Database RLS policies prevent cross-tenant reads
- SERIALIZABLE isolation prevents concurrency issues

**Inheritance Model:**
- Subnet inherited by all peers of tenant
- IP allocation inherits tenant restrictions
- Permissions inherited from tenant config
- Cleanup rules inherited by data items

#### Layer 5: Operational Isolation

Tenants are isolated via audit logging and metrics.

**Audit Logging (90-day retention):**
- All events logged with tenant_id
- Cross-tenant access attempts logged
- Violations trigger immediate alerts
- Immutable audit trail

**Metrics Isolation:**
- All metrics labeled with tenant_id
- Grafana dashboards RBAC enforced
- Per-tenant metric cardinality limits
- Separate alert groups per tenant

**Inheritance Model:**
- Audit log filters inherited
- Metrics labels cascaded to all series
- Retention policies inherited
- Cleanup triggers inherited from tenant config

---

## Isolation Attributes and Inheritance

### Network Layer Attributes

| Attribute | Value | Inheritance | Enforcement |
|-----------|-------|-------------|------------|
| VRF ID | Per-tenant (1001+) | Cascaded to routes | Kernel-level routing |
| Subnet | Per-tenant (/24) | Cascaded to peers | Calico policies |
| Default-Deny | All pods | Inherited by pods | iptables rules |
| DNS Exception | Globally allowed | Inherited by all | Port 53 whitelist |

### Authentication Layer Attributes

| Attribute | Value | Inheritance | Enforcement |
|-----------|-------|-------------|------------|
| JWT Token | Per-peer with tenant claim | Cascaded to services | HMAC signature |
| Token TTL | 1 hour default | Inherited by renewals | Token expiry check |
| Tenant Claim | Extracted from JWT | Cascaded to all operations | Per-request validation |
| Permissions | JWT claims object | Inherited by services | Permission checks |

### Resource Layer Attributes

| Attribute | Value | Inheritance | Enforcement |
|-----------|-------|-------------|------------|
| CPU Quota | 100m per tenant | Inherited by pods | Kubernetes enforcer |
| Memory Quota | 256Mi per tenant | Inherited by pods | Kubernetes enforcer |
| RPS Limit | Per-tenant config | Cascaded to services | Token bucket |
| Burst | 1.5x baseline | Inherited by all | Queue backpressure |

### Data Layer Attributes

| Attribute | Value | Inheritance | Enforcement |
|-----------|-------|-------------|------------|
| Subnet | Deterministic (SHA256) | Inherited by peers | IPAM allocation |
| IP Allocation | Per-peer, tenant-isolated | Inherited by services | Database constraint |
| IP Reuse | On reconnection | Inherited by protocol | Allocation logic |
| Retention | Per-tenant policy | Inherited by cleanup | Scheduled job |

### Operational Layer Attributes

| Attribute | Value | Inheritance | Enforcement |
|-----------|-------|-------------|------------|
| Audit Level | Per-tenant config | Inherited by all events | Filter at write |
| Retention | 90 days (tiered) | Applied to all logs | Rotation schedule |
| Metrics Labels | tenant_id + dimensions | Cascaded to all series | Label validation |
| Cardinality | 100k per tenant | Enforced by scraper | Rate limiting |

---

## Network Layers (OSI L1-L7)

See **[Network Layers OSI Model](NETWORK_LAYERS_OSI_MODEL.md)** and **[Protocol Stack](PROTOCOL_STACK.md)** for detailed protocol specifications.

### L1: Physical Layer
- VPC infrastructure in 3 PoPs (Moscow, Frankfurt, Amsterdam)
- Fiber optic backbone connectivity
- Link aggregation for redundancy

### L2: Data Link Layer
- Ethernet switching
- VLAN tagging for tenant segmentation
- VXLAN overlay networks

### L3: Network Layer
- BGP routing (AS64512) with anycast distribution
- XDP/eBPF programmable forwarding
- Calico CNI with tenant-aware policies

### L4: Transport Layer
- QUIC protocol (RFC 9000) with 0-RTT
- BBRv3 congestion control (50% jitter reduction)
- Connection multiplexing

### L5: Session Layer
- MASQUE tunneling (RFC 9297)
- WireGuard VPN tunnels
- Seamless connection migration

### L6: Presentation Layer
- TLS 1.3 encryption (1-RTT)
- Mutual TLS (mTLS) for service-to-service
- JWT token validation

### L7: Application Layer
- gRPC services
- REST APIs
- Zitadel OIDC authentication
- Web Dashboard UI

---

## Security Architecture

### Defense in Depth

1. Network Layer
   - Default-deny policies
   - VRF isolation
   - BGP authentication
   - DDoS at edge

2. Transport Layer
   - TLS 1.3 encryption
   - QUIC built-in security
   - Perfect Forward Secrecy

3. Application Layer
   - Zitadel OIDC
   - JWT token validation
   - RBAC + ABAC
   - Rate limiting

4. Data Layer
   - Row-level security
   - SERIALIZABLE transactions
   - Encrypted connections
   - Audit logging

5. Operational Layer
   - 90-day audit trail
   - Anomaly detection
   - Violation alerts
   - Incident response

---

## Performance Characteristics

### Latency Budget (Per Request)
- DNS resolution: < 1ms
- Credential validation: < 100ms
- DDoS check: < 100ms
- Data transmission (via 1 PoP): < 5ms
- Metrics collection: 15 seconds (async)
- AI analysis: < 100ms (async)
- Dashboard update: 5 seconds (real-time)

**Total End-to-End:** 215ms

### Throughput
- Per PoP: 100 Gbps
- Per tenant (Tenant A): 10k RPS with 15k burst
- Per tenant (Tenant B): 5k RPS with 7.5k burst
- Global capacity: 300 Gbps

### Reliability
- P2P success rate: 94%
- Failover time: < 500ms
- Availability SLO: 99.99%
- Data loss: None (persistent acknowledgment)

---

## Deployment Topology

### Three Global PoPs

Each PoP contains:
- DNS servers (2 instances, anycast)
- Relay instances (8 containers)
- DDoS filters (2 containers, XDP/eBPF)
- Credential cache (2 instances per tenant)

PoP Locations:
- Moscow (RU-MOW): Eastern Europe
- Frankfurt (EU-FRA): Central Europe
- Amsterdam (EU-AMS): Western Europe

### Central Services

- Control Plane (3-node cluster): Zitadel OIDC, Cadence orchestration
- Monitoring (Prometheus + Grafana): 300+ metrics
- AI Service (TensorFlow): 2.3M LOC
- Dashboard (Next.js): 1.5M LOC
- Database (PostgreSQL): Central state store
- Cache (Redis): Session storage

---

## Technology Stack Summary

| Layer | Component | Technology | LOC |
|-------|-----------|-----------|-----|
| Transport | Scalable Relay | QUIC + BBRv3 | 116,598 |
| Discovery | DNS Network | GeoDNS | 84,063 |
| Auth | Control Plane | Zitadel OIDC | 8,272 |
| Protection | DDoS | ML + XDP/eBPF | 2,160,672 |
| Intelligence | AI Service | TensorFlow + PyTorch | 2,314,799 |
| Observability | Monitoring | Prometheus + Grafana | 8,097 |
| Management | Dashboard | Next.js + React | 1,491,639 |
| **Total** | **All Components** | **Mixed** | **4,263,341** |

---

## Compliance and Standards

### Isolation Ensures

- GDPR: Data isolation, encryption, audit logs
- HIPAA: Data segmentation, access control
- PCI-DSS: Network isolation, monitoring
- SOC 2: Security, availability, integrity

### Network Standards

- QUIC: RFC 9000
- MASQUE: RFC 9297
- TLS: RFC 8446 (1.3)
- BGP: RFC 4271
- Calico: Linux kernel VRF
- Kubernetes: 1.28+

---

---

## Related Documentation

### Architecture & Design Documents
- **[INDEX](INDEX.md)** - Complete documentation index and navigation guide
- **[Architecture Flow](ARCHITECTURE_FLOW.md)** - Detailed 8-step request processing pipeline
- **[Project Overview](PROJECT_OVERVIEW.md)** - All 8 components with detailed descriptions
- **[Tenant Isolation Architecture](TENANT_ISOLATION_ARCHITECTURE.md)** - Complete 5-layer isolation model
- **[Protocol Stack](PROTOCOL_STACK.md)** - Complete protocol layer specifications
- **[Network Layers OSI Model](NETWORK_LAYERS_OSI_MODEL.md)** - L1-L7 implementation details
- **[DNS Network Architecture](DNS_NETWORK_ARCHITECTURE.md)** - DNS design, anycast, DNSSEC
- **[Client Architecture](CLIENT_ARCHITECTURE.md)** - CloudBridge Relay Client documentation

### Implementation Reference (For Developers)
- **INTEGRATION_COMPLETE.md** - Summary of enterprise mesh implementation (see root directory)
- **IMPLEMENTATION_SUMMARY.md** - Detailed architecture and design decisions (see root directory)
- **TESTING_GUIDE.md** - Testing procedures and validation (see root directory)
- **IMPLEMENTATION_CHECKLIST.md** - Implementation verification checklist (see root directory)

### Reference & Data
- **[Requirements Matrix](REQUIREMENTS_MATRIX.md)** - Component requirements and capabilities
- **[Data Sources](DATA_SOURCES.md)** - Metric definitions and verification

---

**Document Status:** Current and Complete
**Last Verified:** November 10, 2025
**Audience:** All technical roles
**Implementation Status:** Enterprise mesh integration complete (see Implementation Reference section)

