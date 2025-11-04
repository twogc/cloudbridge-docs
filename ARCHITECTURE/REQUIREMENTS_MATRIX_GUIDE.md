# Requirements Matrix - Quick Navigation Guide

**Purpose:** Find what you need in the Requirements Matrix with this index.

---

## By Role

### Operations/SRE
Need to understand: What components are working? What might break? How do I monitor?

**Read these sections first:**
1. **Summary Table** (all components at a glance)
2. **Current Capabilities** (each component) - what works now
3. **Use Cases** (each component) - how to test it's working
4. **Dependencies** - what other components must be ready
5. **Futures** - what's coming and when

**Example:** To understand Relay performance:
- Go to "Section 4: Scalable Relay"
- Check "Current Capabilities" - QUIC, BBRv3 working
- Review "Use Cases" - test QUIC connection, test BBRv3 congestion control
- Check "Dependencies" - DDoS protection must be ready
- Note "Futures" - WireGuard tunnel coming Q4 2025

### Developers/Engineers
Need to understand: What must my component take as input? What must I output? What's blocking my feature?

**Read these sections first:**
1. **Required Inputs** (your component) - what data you need
2. **Input Parameters** (your component) - configuration needed
3. **Output Specifications** (your component) - what to produce
4. **Prerequisites for Futures** (your feature) - what blocks you
5. **Dependencies** - what components must exist first

**Example:** Implementing BBRv3 in Relay:
- See "Section 4: Scalable Relay"
- Check "Required Inputs" - DDoS allow decision, JWT token, client data
- Review "Input Parameters" - `relay.cca = "bbrv3"`, BBR tuning params
- Check "Output Specifications" - latency, throughput, jitter metrics
- See "Prerequisites" for congestion control refinements feature
- Verify DDoS module (Step 3) is ready

### Product/Planning
Need to understand: What features are coming? What dependencies? What timeline?

**Read these sections first:**
1. **Futures/Features** (all components) - what's being built
2. **Prerequisites for Futures** (blocking items) - what unblocks features
3. **Implementation Roadmap** (end of document) - timeline and sequencing
4. **Summary Table** - status of all components

**Example:** Planning Q1 2026 release:
- See "Futures" column in Summary Table
- RBAC/ABAC in Control Plane blocked by "Policy Engine not started"
- Online Learning in AI blocked by "90+ days baseline data"
- WireGuard Tunnel blocked by `internal/wireguard/` not started
- Identify critical path blockers, start earliest items first

---

## By Component (Client + 8-Step Pipeline)

### Step 0: CloudBridge Relay Client
**See:** **CLIENT ARCHITECTURE** document

**Quick Questions:**
- Q: How does client connect to relay? → Check "Part 3: Protocol Support"
- Q: How does client authenticate? → Check "Part 4: Authentication & Security"
- Q: What protocols does client use? → Check "Part 3: Protocol Stack"
- Q: How is multi-tenancy enforced? → Check "Part 4.3: Multi-Tenancy & Isolation"
- Q: What are available commands? → Check "Part 6: Usage Examples"
- Q: How do I troubleshoot? → Check "Part 12: Troubleshooting & Diagnostics"

**Key Figures:**
 - Status: ~95% complete (some features partial)
- Platforms: Linux, macOS, Windows
- Protocols: QUIC, gRPC, WebSocket (auto-fallback)

**Client Role in Pipeline:**
```
User/Application → Client (authenticates, discovers, connects)
                    ↓
                 Step 1: DNS (find relay)
                    ↓
                 Step 2: Control Plane (validate JWT)
                    ↓
                 Step 3: DDoS (threat check)
                    ↓
                 Step 4: Relay (transmit data)
                    ↓
                 Steps 5-8: Observe & optimize
```

---

### Step 1: DNS Network
**See:** **REQUIREMENTS MATRIX** → Section 1

**Quick Questions:**
- Q: Is DNS working? → Check "Current Capabilities"
- Q: What does DNS need from me? → Check "Required Inputs"
- Q: What does DNS output? → Check "Output Specifications"
- Q: When will failover work? → Check "Futures" (Q4 2025)

**Key Figures:**
 - Status: 35% complete
- Response Time Target: <100ms
- PoPs: 3 (Moscow, Frankfurt, Amsterdam)

**Use Case to Test:**
```bash
dig relay.cloudbridge.io +short
# Expected: 3 A records (Moscow, Frankfurt, Amsterdam)
# Expected time: <100ms
```

### Step 2: Control Plane - Zitadel
**See:** **REQUIREMENTS MATRIX** → Section 2

**Quick Questions:**
- Q: Can I get a token? → Check "Current Capabilities"
- Q: What client info do I need? → Check "Required Inputs"
- Q: What's in my token? → Check "Output Specifications" (JWT example)
- Q: When will MFA work? → Check "Futures" (Q4 2025)
- Q: What blocks RBAC? → Check "Prerequisites" (Policy engine)

**Key Figures:**
 - Status: 75% complete
- Token Cache TTL: 3600 seconds
- Zitadel Domain: zitadel.2gc.io

**Use Case to Test:**
```bash
# Get token
curl -X POST https://zitadel.2gc.io/oauth/v2/token \
  -d "client_id=cloudbridge-relay&client_secret=xxx&grant_type=client_credentials"

# Decode to see claims
jwt.io # paste token here

# Check custom:tenant_id claim exists
```

### Step 3: DDoS Protection
**See:** **REQUIREMENTS MATRIX** → Section 3

**Quick Questions:**
- Q: Is DDoS working? → Check "Current Capabilities"
- Q: What metrics does DDoS use? → Check "Required Inputs"
- Q: What's my threat score? → Check "Output Specifications"
- Q: When will anomaly detection work? → Check "Futures" (Q1 2026)
- Q: What blocks real-time learning? → Check "Prerequisites" (ML training pipeline)

**Key Figures:**
 - Status: 20% complete
- Detection Threshold: 0.85 confidence
- Block Duration: 300 seconds

**Use Case to Test:**
```bash
# Monitor threat scores in Prometheus
curl http://localhost:9090/api/v1/query?query=ddos_threat_score
# Expected: values between 0.0 and 1.0

# Monitor blocked requests
curl http://localhost:9090/api/v1/query?query=ddos_blocked_requests_total
```

### Step 4: Scalable Relay - QUIC + BBRv3
**See:** **REQUIREMENTS MATRIX** → Section 4

**Quick Questions:**
- Q: Can I connect via QUIC? → Check "Current Capabilities"
- Q: What data must I provide? → Check "Required Inputs"
- Q: How fast is it? → Check "Output Specifications" (latency, throughput)
- Q: When will WireGuard work? → Check "Futures" (Q4 2025)
- Q: What blocks TCP→QUIC? → Check "Prerequisites" (Tunnel Manager not started)

**Key Figures:**
 - Status: 35% complete
- QUIC Listen Port: 4433
- BBRv3 Jitter Improvement: 50% reduction
- Throughput Improvement: +0.2%

**Use Case to Test:**
```bash
# Test QUIC connection
quic-client https://relay.cloudbridge.io:4433

# Monitor latency
dig @relay.cloudbridge.io any example.com

# Check BBRv3 stats
ss -t | grep -i bbr
# or netstat -tnp | grep bbrv3
```

### Step 5: Monitoring - Prometheus + Grafana
**See:** **REQUIREMENTS MATRIX** → Section 5

**Quick Questions:**
- Q: Where are my metrics? → Check "Current Capabilities"
- Q: What metrics exist? → Check Input/Output Specifications
- Q: When will tracing work? → Check "Futures" (Q4 2025)
- Q: What blocks ELK logging? → Check "Prerequisites" (Elasticsearch not started)

**Key Figures:**
 - Status: 75% complete
- Metrics Port: 9090 (Prometheus)
- Grafana Port: 3000
- Retention: 15 days

**Access:**
```bash
# Prometheus
http://localhost:9090/graph

# Grafana
http://localhost:3000/
# Login with default creds or Zitadel OIDC
```

### Step 6: AI Service - ML Models
**See:** **REQUIREMENTS MATRIX** → Section 6

**Quick Questions:**
- Q: What AI is running? → Check "Current Capabilities"
- Q: What data does AI need? → Check "Required Inputs"
- Q: What predictions does AI make? → Check "Output Specifications"
- Q: When will continuous learning work? → Check "Futures" (Q1 2026)
- Q: What blocks federated learning? → Check "Prerequisites" (Not started)

**Key Figures:**
 - Status: 20% complete (framework ready, models stub)
- Inference Timeout: 100ms
- Confidence Threshold: 0.75

**Models Available:**
1. Traffic-Classification-v1.pb
2. Capacity-Predictor-v1.pb
3. Anomaly-Detector-v1.pb
4. Threat-Correlator-v1.pb
5. Optimization-Engine-v1.pb

### Step 7-8: Dashboard
**See:** **REQUIREMENTS MATRIX** → Section 7

**Quick Questions:**
- Q: Can I see the dashboard? → Check "Current Capabilities"
- Q: What data can I view? → Check "Required Inputs"
- Q: What exports are available? → Check "Output Specifications"
- Q: When will custom dashboards work? → Check "Futures" (Q1 2026)
- Q: What blocks log search? → Check "Prerequisites" (Loki not started)

**Key Figures:**
 - Status: 50% complete
- Port: 3000
- Refresh Interval: 5 seconds (default)
- Theme: Dark (default)

**Access:**
```bash
http://localhost:3000/
# Login with Zitadel OIDC
```

---

## By Feature (What's Being Built)

### Q4 2025 Priorities

**DNS:**
- Health check system → Enables: failover support
- DNSSEC validation framework → Enables: DNS spoofing protection

**Control Plane:**
- PAT token generation → Enables: service-to-service auth (testing phase)
- MFA design → Enables: enterprise security (design phase)

**DDoS:**
- Layer 7 attack detection → Enables: HTTP-specific attack blocking
- Geo-IP blocking framework → Enables: region-based access control

**Relay:**
- TCP→QUIC conversion → Enables: legacy client support
- Tunnel manager stub → Enables: encrypted P2P mesh

**Monitoring:**
- OpenTelemetry tracing → Enables: distributed tracing across components
- SLO burn rate → Enables: error budget tracking

**AI:**
- Bot detection model training → Enables: identify automated traffic
- Real-time update pipeline design → Enables: model improvements

**Dashboard:**
- Alert WebSocket integration → Enables: real-time notifications
- PDF export capability → Enables: reports

### Q1 2026 Priorities

See Implementation Roadmap section at end of **REQUIREMENTS MATRIX**

---

## Finding Blocking Dependencies

**Question:** My feature is blocked. What needs to be done first?

**Process:**
1. Find your feature in the component's "Futures" section
2. Check "Prerequisites for Futures" row
3. If status is "Not started" or "Stub" → That's your blocker
4. Create task to implement the blocker first
5. Parallelize with other teams if possible

**Example:**

Feature: Real-time Model Updates (AI Service, Q1 2026)
Prerequisites:
- Model training pipeline (Not started) ← BLOCKER
- New attack sample collection (Partial) ← BLOCKER
- Model versioning system (Not started) ← BLOCKER
- Metrics collection pipeline (Ready)

→ Can't start this feature until 3 blockers are resolved.

**Another Example:**

Feature: WireGuard Tunnel Integration (Relay, Q4 2025)
Prerequisites:
- WireGuard kernel module (Ready)
- WireGuard Go library (Ready)
- Tunnel configuration management (Stub) ← BLOCKER
- Key exchange mechanism (Designed, not implemented) ← BLOCKER

→ Can start in parallel: WireGuard setup while implementing Tunnel config.

---

## Key Statistics

### Component Readiness

| Component | Status | Complete % | Team Impact |
|-----------|--------|-----------|------------|
| Control Plane | PRODUCTIVE | 75% | Most features working, MFA/RBAC pending |
| Monitoring | PRODUCTIVE | 75% | Metrics collected, tracing pending |
| DNS Network | USABLE | 35% | Basic DNS working, failover pending |
| Relay | USABLE | 35% | QUIC/BBRv3 working, tunneling pending |
| DDoS Protection | FRAMEWORK | 20% | Framework ready, models need training |
| AI Service | FRAMEWORK | 20% | Framework loaded, models need training |
| Dashboard | PARTIAL | 50% | UI working, APIs integrating |

### Blocking Items (Fix These First)

1. **Health Check System** (Step 1, 3, 4)
   - Blocks: DNS failover, DDoS health checks, relay health monitoring
   - Location: `internal/health/` (STUB)
   - Effort: 2-3 days
   - Priority: HIGH

2. **Tunnel Manager** (Step 4)
   - Blocks: WireGuard integration, TCP→QUIC conversion
   - Location: `internal/tunnel/` (STUB)
   - Effort: 5-7 days
   - Priority: HIGH

3. **Policy Engine (RBAC/ABAC)** (Step 2)
   - Blocks: Fine-grained access control
   - Choices: Casbin vs OPA (not decided)
   - Effort: 10-14 days
   - Priority: HIGH

4. **ML Training Pipeline** (Step 6)
   - Blocks: Real-time model updates, online learning
   - Location: `ml/training/` (NOT STARTED)
   - Effort: 15-20 days
   - Priority: HIGH

5. **Model Registry** (Step 6)
   - Blocks: Model versioning, A/B testing
   - Location: `ml/registry/` (NOT STARTED)
   - Effort: 5-7 days
   - Priority: MEDIUM

6. **Elasticsearch/Loki** (Step 5, 8)
   - Blocks: Log search, log aggregation
   - Location: Infrastructure (NOT STARTED)
   - Effort: 3-5 days setup
   - Priority: MEDIUM

---

## How the Sections Are Organized

Each component section follows this structure:

```
1. Component Name & Status
   - Implementation %: Shows completeness (20-75%)
   - LOC: Lines of code in this component
   - Location: File paths to find the code

2. Current Capabilities
   - What works today
   - What you can use now
   - What's production-ready

3. Required Inputs
   - Data this component needs
   - Sources of that data
   - Required vs optional

4. Input Parameters
   - Configuration options
   - Default values
   - Example configuration

5. Output Specifications
   - What this component produces
   - Data formats
   - Example outputs

6. Futures/Features
   - What's being built
   - When it's expected
   - Priority level
   - Why it's needed

7. Prerequisites for Futures
   - What blocks each future feature
   - Status of dependencies
   - Implementation effort

8. Use Cases / Testing Scenarios
   - How to test this component
   - Example commands
   - Expected outputs
   - Verification steps

9. Dependencies
   - What other components needed
   - Status (Ready, Partial, Stub, Not Started)
   - Impact if missing

10. Notes
   - Important details
   - Edge cases
   - Limitations
   - Known issues
```

---

## Examples: How to Use This Document

### Example 1: Troubleshooting High Latency

**Problem:** Relay latency is 200ms (SLO is <50ms P95)

**Investigation Steps:**

1. Check Control Plane (Step 2) - Token validation might be slow
   - Go to "Section 2: Control Plane"
   - Check "Output Specifications" - token validation time
   - Review "Use Cases" - "Token Cache Performance" test

2. Check DDoS (Step 3) - Threat detection taking too long
   - Go to "Section 3: DDoS Protection"
   - Check "Use Cases" - verify threat score response time <100ms

3. Check Relay (Step 4) - Congestion or buffering issues
   - Go to "Section 4: Scalable Relay"
   - Check "Use Cases" - "BBRv3 Congestion Control" test
   - Review "Output Specifications" - check BBR state (startup/drain/steady)

4. Check Monitoring (Step 5) - Is data being collected?
   - Go to "Section 5: Monitoring"
   - Verify Prometheus scraping latency metrics

### Example 2: Implementing a New Feature

**Task:** Add token refresh mechanism (JWT auto-renewal)

**Steps Using This Matrix:**

1. Find the feature in Section 2: Control Plane
   - Under "Futures/Features" → "Token Refresh Mechanism"
   - Status: Stub
   - Target: Q4 2025
   - Why needed: Seamless token renewal

2. Check what blocks it
   - Go to "Prerequisites for Futures"
   - Find "Token Refresh Mechanism" row
   - Check: Refresh token storage (Partial - Redis ready)
   - Check: Refresh token rotation logic (Not implemented) ← YOU DO THIS
   - Check: Graceful token expiry handling (Partial)

3. Understand inputs and outputs
   - Check "Required Inputs" for Control Plane
   - Check "Output Specifications" for token format

4. Review how to test it
   - Find "Use Case 5: Token Refresh (Future)" in Section 2
   - Follow test scenario to verify implementation

5. Check dependencies
   - Ensure Redis Sentinel is ready (it is)
   - Ensure token validation works (it does)
   - Confirm Zitadel supports refresh tokens (check prerequisites)

### Example 3: Capacity Planning for Q1 2026

**Question:** Which features can we ship? What's the timeline?

**Steps:**

1. Check Implementation Roadmap (end of **REQUIREMENTS MATRIX**)
2. For Q1 2026 Priority 1 items, check "Prerequisites for Futures"
3. Identify items with "Not started" status - these need 4+ weeks
4. Identify items with "Partial" status - these might be 2-3 weeks
5. Sequence work: blockers first, then dependent features in parallel

**Example Q1 Plan:**
- **Critical Path:** Tunnel Manager (blocker for relay) → Start week 1
- **Parallel Track:** Policy engine decision (blocker for RBAC) → Start week 1
- **Follow-up:** WireGuard integration (waits for Tunnel Manager) → Start week 4
- **Follow-up:** RBAC implementation (waits for policy engine) → Start week 4

---

## Notes

- This matrix was built from source code analysis on November 4, 2025
- Component status percentages reflect code implementation, not feature completeness
- All timelines assume 4-person team, typical complexity
- "Prerequisites" are hard blockers - can't ship feature without completing them
- Dependencies are soft blockers - can develop in parallel, test requires all ready

**For Questions:**
- Operations: See "By Role" section above, then find your component
- Development: See "By Component" section above, then follow the Prerequisites
- Planning: See "Implementation Roadmap" and "Blocking Items" sections

---

**Document Status:** COMPLETE
**Last Updated:** November 4, 2025
**Created From:** Source code analysis + architecture documentation
