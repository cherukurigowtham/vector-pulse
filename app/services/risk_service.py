import asyncio
import time
import hashlib
import logging
import datetime
import vector_pulse
import json
import math
from app.core.config import RISK_CONFIG, EMERGENCY_KILL_SWITCH
from app.models import Order
from app.core.redis import r, rk
from app.services.webhook_dispatcher import dispatch_alert
from app.core.geoip import GEO_READER
from app.db.database import AUDIT_STORE
from app.services.graph_service import link_identity
from app.services.vector_service import generate_semantic_hash, check_vector_cluster
from app.services.action_engine import ActionEngine
from app.services.behavioral_service import analyze_session_behavior
from app.services.telemetry_service import telemetry_service
from app.services.governance_service import governance_service

_engine = ActionEngine(r)

async def _log_audit_event(risk_id: str, email: str, context: dict, decision: str, shadow: bool):
    try:
        payload = {
            "risk_id": risk_id,
            "uid": context["uid"],
            "email": email,
            "team_id": context.get("team_id"),
            "risk_score": context["score"],
            "decision": decision,
            "shadow_mode": 1 if shadow else 0,
            "reasons": ",".join(context["flags"]),
            "metrics": json.dumps(context["metrics"]),
            "timestamp": context["timestamp"],
        }
        await AUDIT_STORE.insert_risk_audit(payload)
    except Exception as e:
        logging.error(f"Audit log failed: {e}")

def _merchant_scope(key_hash: str | None) -> str:
    return key_hash or "anonymous"

def _merchant_state_key(key_hash: str | None, kind: str, suffix: str) -> str:
    return rk(f"{kind}:{_merchant_scope(key_hash)}:{suffix}")

def _ip_prefix(ip: str) -> str:
    if ":" in ip:
        return ":".join(ip.split(":")[:4])
    parts = ip.split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3])
    return ip

async def _check_global_velocity(ip: str, risk_config: dict) -> bool:
    try:
        now = time.time()
        window_start = now - risk_config["velocity_window_secs"]
        vel_key = rk(f"global:velocity:ip:{ip}")
        async with r.pipeline() as pipe:
            pipe.zadd(vel_key, {str(now): now})
            pipe.zremrangebyscore(vel_key, 0, window_start)
            pipe.zcard(vel_key)
            pipe.expire(vel_key, risk_config["velocity_window_secs"] * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"] * 10
    except Exception as e:
        logging.error(f"Global Velocity Check Failed: {e}")
        return False

async def _check_global_sybil(uid: str, address: str, risk_config: dict) -> bool:
    try:
        address_hash = hashlib.sha256(vector_pulse.address_fingerprint(address).encode()).hexdigest()
        key = rk(f"global:sybil:addr:{address_hash}")
        async with r.pipeline() as pipe:
            pipe.sadd(key, uid)
            pipe.scard(key)
            pipe.expire(key, 86400 * 7)
            res = await pipe.execute()
        return res[1] > risk_config["sybil_address_limit"] * 2
    except Exception as e:
        logging.error(f"Global Sybil Check Failed: {e}")
        return False

async def _check_device_velocity(uid: str, device_hash: str | None, risk_config: dict) -> bool:
    if not device_hash:
        return False
    try:
        now = time.time()
        window_start = now - risk_config["velocity_window_secs"]
        vel_key = rk(f"device:velocity:{device_hash}")
        async with r.pipeline() as pipe:
            pipe.zadd(vel_key, {str(now): now})
            pipe.zremrangebyscore(vel_key, 0, window_start)
            pipe.zcard(vel_key)
            pipe.expire(vel_key, risk_config["velocity_window_secs"] * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"]
    except Exception as e:
        logging.error(f"Device Velocity Check Failed: {e}")
        return False

async def _check_velocity(uid: str, risk_config: dict, merchant_key_hash: str | None) -> bool:
    try:
        now = time.time()
        window_start = now - risk_config["velocity_window_secs"]
        vel_key = _merchant_state_key(merchant_key_hash, "velocity", uid)
        async with r.pipeline() as pipe:
            pipe.zadd(vel_key, {str(now): now})
            pipe.zremrangebyscore(vel_key, 0, window_start)
            pipe.zcard(vel_key)
            pipe.expire(vel_key, risk_config["velocity_window_secs"] * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"]
    except Exception as e:
        logging.error(f"Velocity Check Failed: {e}")
        return False

async def _check_sybil(uid: str, address: str, risk_config: dict, merchant_key_hash: str | None, merchant_email: str | None) -> bool:
    try:
        address_hash = hashlib.sha256(vector_pulse.address_fingerprint(address).encode()).hexdigest()
        key = _merchant_state_key(merchant_key_hash, "addr", address_hash)
        async with r.pipeline() as pipe:
            pipe.sadd(key, uid)
            pipe.scard(key)
            pipe.expire(key, 86400 * 7)
            if merchant_email:
                idx_key = rk(f"addr_index:{merchant_email}")
                pipe.sadd(idx_key, key)
                pipe.expire(idx_key, 86400 * 90)
            res = await pipe.execute()
        return res[1] > risk_config["sybil_address_limit"]
    except Exception as e:
        logging.error(f"Sybil Check Failed: {e}")
        return False

async def _check_price_anomaly(uid: str, amount: float, risk_config: dict, merchant_key_hash: str | None) -> tuple[bool, float, float]:
    try:
        history_key = _merchant_state_key(merchant_key_hash, "history", uid)
        history_raw = await r.lrange(history_key, 0, risk_config["history_len"] - 1)
        history = [float(x) for x in history_raw]
        is_anomaly, avg, std_dev = vector_pulse.detect_amount_anomaly(history, amount, risk_config["z_score_threshold"])
        async with r.pipeline() as pipe:
            pipe.lpush(history_key, amount)
            pipe.ltrim(history_key, 0, risk_config["history_len"] - 1)
            pipe.expire(history_key, 60 * 60 * 24 * 7)
            await pipe.execute()
        return is_anomaly, avg, std_dev
    except Exception as e:
        logging.error(f"Price Anomaly Check Failed: {e}")
        return False, 0.0, 0.0

async def _get_trust_score(uid: str, merchant_key_hash: str | None) -> float:
    try:
        delivered = await r.get(_merchant_state_key(merchant_key_hash, "repdelivered", uid))
        total = await r.get(_merchant_state_key(merchant_key_hash, "reptotal", uid))
        return vector_pulse.calculate_trust_score(int(delivered or 0), int(total or 0))
    except Exception:
        return 50.0

# Circuit Breaker State for GeoIP
GEOIP_CIRCUIT_STATE = {
    "failures": 0,
    "last_failure": 0,
    "is_open": False,
    "threshold": 3,
    "cooldown_secs": 60
}

async def _check_ip_intelligence(ip: str) -> bool:
    if ip == "127.0.0.1": return False
    
    # Check Circuit Breaker
    now = time.time()
    if GEOIP_CIRCUIT_STATE["is_open"]:
        if now - GEOIP_CIRCUIT_STATE["last_failure"] > GEOIP_CIRCUIT_STATE["cooldown_secs"]:
            GEOIP_CIRCUIT_STATE["is_open"] = False
            GEOIP_CIRCUIT_STATE["failures"] = 0
            logging.info("GeoIP Circuit Breaker: Resetting to CLOSED state")
        else:
            # Circuit is OPEN, bypass lookup with neutral result
            return False

    try:
        match = await asyncio.to_thread(GEO_READER.get, ip)
        is_risky_geo = False
        if match:
            country = match.get("country", {}).get("iso_code")
            if country and country != "IN":
                is_risky_geo = True
        
        # Reset failures on success
        GEOIP_CIRCUIT_STATE["failures"] = 0
        
        cache_key = rk(f"ipint:{ip}")
        cached = await r.get(cache_key)
        if cached is not None:
            return cached == "1" or is_risky_geo
        await r.setex(cache_key, 60 * 60 * 24, "1" if is_risky_geo else "0")
        return is_risky_geo
    except Exception as e:
        GEOIP_CIRCUIT_STATE["failures"] += 1
        GEOIP_CIRCUIT_STATE["last_failure"] = now
        logging.error(f"IP Intelligence Lookup Failed (Failures: {GEOIP_CIRCUIT_STATE['failures']}): {e}")
        
        if GEOIP_CIRCUIT_STATE["failures"] >= GEOIP_CIRCUIT_STATE["threshold"]:
            GEOIP_CIRCUIT_STATE["is_open"] = True
            logging.error(f"GeoIP Circuit Breaker: TRIPPED (OPEN) for {GEOIP_CIRCUIT_STATE['cooldown_secs']}s")
            
        return False

def _calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in kilometers between two points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def _check_geo_velocity(uid: str, ip: str, device_hash: str | None, risk_config: dict) -> bool:
    if not device_hash or not ip or ip == "127.0.0.1":
        return False
    try:
        geo = await asyncio.to_thread(GEO_READER.get, ip)
        if not geo: return False
        lat = geo.get("location", {}).get("latitude")
        lon = geo.get("location", {}).get("longitude")
        if lat is None or lon is None: return False
        
        now = time.time()
        geo_key = rk(f"geo:velocity:{device_hash}")
        last_geo_raw = await r.get(geo_key)
        
        is_impossible_travel = False
        if last_geo_raw:
            last_geo = json.loads(last_geo_raw)
            last_lat, last_lon, last_ts = last_geo["lat"], last_geo["lon"], last_geo["ts"]
            
            # Delegate complex spatial-temporal evaluation to Rust
            is_impossible_travel, _speed = vector_pulse.evaluate_geo_velocity(
                last_lat, last_lon, last_ts,
                lat, lon, now,
                800.0 # Speed threshold in km/h
            )
            
            if is_impossible_travel:
                logging.warning(f"Impossible Travel Detected by Rust Engine: device {device_hash}")
            
        await r.setex(geo_key, 3600 * 24, json.dumps({"lat": lat, "lon": lon, "ts": now}))
        return is_impossible_travel
    except Exception as e:
        logging.error(f"Geo Velocity Check (Rust Bridge) Failed: {e}")
        return False

def _check_time_anomaly() -> bool:
    try:
        now_utc = datetime.datetime.utcnow()
        now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
        return 2 <= now_ist.hour < 5
    except Exception as e:
        logging.error(f"Time Anomaly Check Failed: {e}")
        return False

def _check_bot_speed(checkout_time_secs: float | None) -> bool:
    if checkout_time_secs is None: return False
    return checkout_time_secs < 2.5

async def _check_disposable_email(email: str | None) -> bool:
    if not email or "@" not in email: return False
    parts = email.rsplit("@", 1)
    if len(parts) < 2: return False
    domain = parts[1].lower()
    cache_key = rk(f"disposable:{domain}")
    cached = await r.get(cache_key)
    if cached is not None: return cached == "1"
    disposable_domains = {"mailinator.com", "yopmail.com", "10minutemail.com", "temp-mail.org"} # etc
    is_disposable = domain in disposable_domains
    await r.setex(cache_key, 86400, "1" if is_disposable else "0")
    return is_disposable

async def _check_high_risk_pin(pin: str | None) -> bool:
    if not pin: return False
    try:
        return await r.sismember(rk("high_risk_pins"), pin.strip())
    except Exception:
        return False

async def _check_identity_cache(email: str | None, phone: str | None) -> bool:
    """Checks if the email or phone is in the global high-risk identity set."""
    try:
        async with r.pipeline() as pipe:
            if email: pipe.sismember(rk("global:blacklist:email"), email.lower().strip())
            if phone: pipe.sismember(rk("global:blacklist:phone"), phone.strip())
            res = await pipe.execute()
        return any(res)
    except Exception as e:
        logging.error(f"Identity Cache Check Failed: {e}")
        return False

async def _check_identity_cluster(uid: str, address: str, pin: str, ip: str, merchant_key_hash: str) -> tuple[bool, float]:
    try:
        addr_fp = vector_pulse.address_fingerprint(address)
        subnet = _ip_prefix(ip)
        
        addr_key = rk(f"cluster:addr:{merchant_key_hash}:{hashlib.md5(addr_fp.encode()).hexdigest()}")
        pin_key = rk(f"cluster:pin:{merchant_key_hash}:{pin}")
        subnet_key = rk(f"cluster:subnet:{merchant_key_hash}:{subnet}")
        
        async with r.pipeline() as pipe:
            pipe.sadd(addr_key, uid)
            pipe.scard(addr_key)
            pipe.expire(addr_key, 86400 * 30)
            
            pipe.sadd(pin_key, uid)
            pipe.scard(pin_key)
            pipe.expire(pin_key, 86400 * 30)
            
            pipe.sadd(subnet_key, uid)
            pipe.scard(subnet_key)
            pipe.expire(subnet_key, 86400 * 30)
            
            res = await pipe.execute()
            
        shared_addr = res[1]
        shared_pin = res[4]
        shared_subnet = res[7]
        
        return vector_pulse.evaluate_identity_cluster(shared_addr, shared_pin, shared_subnet)
    except Exception as e:
        logging.error(f"Identity Cluster Check Failed: {e}")
        return False, 0.0

def _calculate_risk_score(velocity_flag, sybil_flag, anomaly_flag, identity_flag, cohort_flag, trust_score, vpn_flag, global_network_flag, gibberish_flag, device_velocity_flag, suspicious_name_flag, geo_velocity_flag, time_anomaly_flag, bot_speed_flag, suspicious_phone_flag, disposable_email_flag, email_name_mismatch_flag, poor_address_flag, high_risk_pin_flag, risk_config, consortium_hits=0, is_quarantined=False, reputation_map=None, governance_weights=None):
    """
    Advanced Pillar: Cognitive Ensemble & Explainability.
    Calculates total score and returns XAI Impact Breakdown.
    """
    impacts = {}
    score = 0.0
    
    # Helper for weight resolution
    def _get_w(key, default_key):
        if governance_weights and key in governance_weights:
            return float(governance_weights[key])
        return float(risk_config[default_key])

    # Track individual factor impacts
    if velocity_flag:
        impacts["HIGH_VELOCITY"] = _get_w("velocity_weight", "velocity_weight")
    if sybil_flag:
        impacts["ADDRESS_SYBIL"] = _get_w("sybil_weight", "sybil_weight")
    if anomaly_flag:
        impacts["PRICE_ANOMALY"] = _get_w("anomaly_weight", "anomaly_weight")
    if identity_flag:
        impacts["GLOBAL_ID_BLACKLIST"] = _get_w("identity_weight", "identity_weight")
    if vpn_flag:
        impacts["VPN_DETECTED"] = _get_w("vpn_weight", "vpn_weight")
    if global_network_flag:
        impacts["GLOBAL_CONSORTIUM"] = _get_w("global_network_weight", "global_network_weight")
    if gibberish_flag:
        impacts["GIBBERISH_ADDRESS"] = risk_config["gibberish_weight"]
    if device_velocity_flag:
        impacts["DEVICE_VELOCITY"] = risk_config["device_velocity_weight"]
    if suspicious_name_flag:
        impacts["SUSPICIOUS_NAME"] = risk_config["suspicious_name_weight"]
    if geo_velocity_flag:
        impacts["IMPOSSIBLE_TRAVEL"] = risk_config["geo_velocity_weight"]
    if time_anomaly_flag:
        impacts["TIME_OF_DAY"] = risk_config["time_anomaly_weight"]
    if bot_speed_flag:
        impacts["BOT_SPEED"] = _get_w("bot_speed_weight", "bot_speed_weight")
    if suspicious_phone_flag:
        impacts["SUSPICIOUS_PHONE"] = risk_config["suspicious_phone_weight"]
    if disposable_email_flag:
        impacts["DISPOSABLE_EMAIL"] = risk_config["disposable_email_weight"]
    if email_name_mismatch_flag:
        impacts["EMAIL_NAME_MISMATCH"] = risk_config["email_name_mismatch_weight"]
    if poor_address_flag:
        impacts["POOR_ADDRESS"] = risk_config["poor_address_weight"]
    if high_risk_pin_flag:
        impacts["HIGH_RISK_PIN"] = risk_config["high_risk_pin_weight"]
    
    if is_quarantined:
        impacts["GLOBAL_QUARANTINE"] = 40.0 # High fixed impact for quarantine
        
    if consortium_hits > 0:
        c_impact = min(5, consortium_hits) * risk_config.get("global_network_weight", 15.0)
        impacts["FRAUD_RING_LINK"] = c_impact

    # Pillar 2: Global Pulse Reputation Signals
    if reputation_map:
        # Penalize low reputation (Trust below 0.5)
        # Reward high reputation (Trust above 0.7)
        avg_rep = sum(reputation_map.values()) / len(reputation_map)
        
        if avg_rep < 0.4:
            rep_penalty = (0.5 - avg_rep) * 40.0 # Significant penalty for poor global standing
            impacts["GLOBAL_REPUTATION_PENALTY"] = float(rep_penalty)
        elif avg_rep > 0.8:
            rep_bonus = (avg_rep - 0.8) * 20.0 # Reward for consistent clean history across network
            impacts["GLOBAL_REPUTATION_BOOST"] = float(-rep_bonus)

    # Sum initial impacts
    score = sum(impacts.values())

    # Trust Factor (Negative Impact / Boost)
    trust_floor = risk_config["trust_floor"]
    if trust_score < trust_floor:
        penalty = (trust_floor - trust_score) * risk_config["trust_penalty_multiplier"]
        impacts["LOW_TRUST_PENALTY"] = float(penalty)
        score += penalty
    elif trust_score > 70.0:
        boost = (trust_score - 70.0) * 0.5 # Reward very high trust
        impacts["HIGH_TRUST_REWARD"] = float(-boost)
        score -= boost

    # Pillar 1 (v4): Cognitive Conflict Resolution (Simplified Dempster-Shafer)
    # If we have heavy fraud signals but also high trust, we resolve the conflict.
    if trust_score > 85.0 and score > risk_config.get("decision_threshold", 50.0):
        # We have high 'belief' in both fraud and trust.
        # Professional AI reduces 'fuzziness' by applying a conflict coefficient.
        conflict_reduction = (score - 50.0) * 0.3
        impacts["COGNITIVE_CONFLICT_RESOLUTION"] = float(-conflict_reduction)
        score -= conflict_reduction

    final_score = max(0.0, min(100.0, score))
    return final_score, impacts

def _check_behavioral_dna(order: Order, risk_config: dict):
    """
    Advanced Pillar: Behavioral DNA.
    Analyzes keystroke velocity and mouse entropy.
    Humans have higher entropy and medium velocity. Bots have zero velocity or zero entropy.
    """
    flags = []
    score = 0
    
    if order.keystroke_velocity is not None:
        if order.keystroke_velocity < 10 or order.keystroke_velocity > 500:
            flags.append("UNNATURAL_KEYSTROKE_VELOCITY")
            score += risk_config.get("bot_speed_weight", 10.0)
            
    if order.mouse_movement_entropy is not None:
        if order.mouse_movement_entropy < 1.0:
            flags.append("BOT_LIKE_MOUSE_MOVEMENT")
            score += risk_config.get("bot_speed_weight", 15.0)
        # Pillar 3: Robotic Consistency (Too Perfect)
        elif order.mouse_movement_entropy > 4.5: # Extremely high, perfect entropy
             flags.append("ROBOTIC_CONSISTENCY")
             score += risk_config.get("bot_speed_weight", 10.0)
            
    return flags, score

async def run_risk_analysis(order: Order, merchant_key_hash: str | None, merchant_email: str) -> dict:
    start_time = time.time()
    # Phase 29: Emergency Kill-switch (High Availability Governance)
    if EMERGENCY_KILL_SWITCH:
        logging.critical("GLOBAL EMERGENCY KILL-SWITCH ENGAGED: Bypassing Risk Engine.")
        return {"score": 0.0, "decision": "ALLOW", "flags": ["EMERGENCY_BYPASS"]}

    risk_config = RISK_CONFIG
    uid, amount, address, client_ip = order.uid, order.amt, order.addr, order.ip
    
    # Pillar 1 & 2: Vector Intelligence
    order_hash = generate_semantic_hash(address, order.name, order.email)
    quarantine_task = check_vector_cluster(order_hash)
    
    velocity_task = _check_velocity(uid, risk_config, merchant_key_hash)
    sybil_task = _check_sybil(uid, address, risk_config, merchant_key_hash, merchant_email)
    price_task = _check_price_anomaly(uid, amount, risk_config, merchant_key_hash)
    trust_task = _get_trust_score(uid, merchant_key_hash)
    ip_task = _check_ip_intelligence(client_ip)
    global_velocity_task = _check_global_velocity(client_ip, risk_config)
    global_sybil_task = _check_global_sybil(uid, address, risk_config)
    device_velocity_task = _check_device_velocity(uid, order.device_hash, risk_config)
    geo_velocity_task = _check_geo_velocity(uid, client_ip, order.device_hash, risk_config)
    
    is_gibberish_flag = False
    try: is_gibberish_flag = vector_pulse.is_gibberish_address(address)
    except: pass
    
    is_suspicious_name_flag = False
    try: is_suspicious_name_flag = vector_pulse.is_suspicious_name(order.name or "")
    except: pass
    
    is_suspicious_phone_flag = False
    try: is_suspicious_phone_flag = vector_pulse.is_suspicious_phone(order.phone or "")
    except: pass
    
    is_time_anomaly_flag = _check_time_anomaly()
    is_bot_speed_flag = _check_bot_speed(order.checkout_time_secs)
    is_disposable_email_task = _check_disposable_email(order.email)
    
    is_email_name_mismatch_flag = False
    try: is_email_name_mismatch_flag = vector_pulse.is_email_name_mismatch(order.name or "", order.email or "")
    except: pass
    
    is_poor_address_flag = False
    try: is_poor_address_flag = vector_pulse.has_poor_address_structure(address)
    except: pass
    
    high_risk_pin_task = _check_high_risk_pin(order.pin)
    identity_cache_task = _check_identity_cache(order.email, order.phone)
    identity_cluster_task = _check_identity_cluster(uid, address, order.pin, client_ip, merchant_key_hash)
    
    # Pillar 2: Graph Analysis
    graph_task = link_identity(uid, order.email, order.phone, address, client_ip, merchant_email)
    
    # Pillar 13 (v4): Behavioral Transformers (Cognitive Signal Analysis)
    behavior_task = analyze_session_behavior(merchant_email, order.session_id) if order.session_id else asyncio.sleep(0, result=None)
    
    results = await asyncio.gather(
        velocity_task, sybil_task, price_task, trust_task, ip_task, 
        global_velocity_task, global_sybil_task, device_velocity_task, 
        geo_velocity_task, high_risk_pin_task, is_disposable_email_task,
        identity_cache_task, identity_cluster_task, graph_task, quarantine_task,
        behavior_task
    )
    (
        is_velocity_flag, is_sybil_flag, (is_price_anomaly, avg, std_dev), 
        trust_score, is_vpn_flag, is_global_velocity_flag, is_global_sybil_flag, 
        is_device_velocity_flag, is_geo_velocity_flag, is_high_risk_pin_flag, 
        is_disposable_email_flag, is_identity_flag, (is_cluster_flag, cluster_score),
        graph_res, is_quarantined, behavior_res
    ) = results
    
    consortium_hits = graph_res.get("hits", 0)
    reputation_map = graph_res.get("reputation", {})
    
    is_global_network_flag = is_global_velocity_flag or is_global_sybil_flag or (consortium_hits > 0) or is_quarantined
    
    # Pillar 8: Real-time Attack Alerts
    if is_quarantined or consortium_hits >= 3:
        # Proactive alerting for coordinated waves
        alert_type = "GLOBAL_QUARANTINE_TRIGGERED" if is_quarantined else "COORDINATED_RING_DETECTED"
        await dispatch_alert(merchant_email, alert_type, {
            "uid": uid,
            "consortium_hits": consortium_hits,
            "is_quarantined": is_quarantined,
            "flags": [f for f in results if isinstance(f, bool) and f] # Simple summary of active flags
        })

    # Pillar 4: Behavioral DNA
    behavioral_flags, behavioral_score = _check_behavioral_dna(order, risk_config)
    
    # Inject Phase 13 Behavioral Signals
    if behavior_res and "score_impact" in behavior_res:
        cog_impact = behavior_res["score_impact"]
        if cog_impact > 0:
            behavioral_score += cog_impact
            behavioral_flags.append(f"COGNITIVE_ANOMALY_DETECTED({behavior_res.get('event_count', 0)} events)")
            if behavior_res.get("entropy", 1.0) < 0.2:
                behavioral_flags.append("LOW_INTERACTION_ENTROPY")

    # Pillar 1 (v4): Cognitive Ensemble Scoring
    # Phase 29: Autonomous Governance (Dynamic Weight Adjustment)
    governance_weights = await governance_service.get_adjusted_weights(merchant_email)
    
    # Override standard weights with tuned governance weights
    risk_score, xai_impacts = _calculate_risk_score(
        is_velocity_flag, is_sybil_flag, is_price_anomaly, is_identity_flag, is_cluster_flag, trust_score,
        is_vpn_flag, is_global_network_flag, is_gibberish_flag, is_device_velocity_flag,
        is_suspicious_name_flag, is_geo_velocity_flag, is_time_anomaly_flag, is_bot_speed_flag,
        is_suspicious_phone_flag, is_disposable_email_flag, is_email_name_mismatch_flag,
        is_poor_address_flag, is_high_risk_pin_flag, risk_config,
        consortium_hits=consortium_hits, is_quarantined=is_quarantined, reputation_map=reputation_map,
        governance_weights=governance_weights
    )
    
    # Add Behavioral Impacts to XAI
    if behavioral_score > 0:
        risk_score = min(100.0, risk_score + behavioral_score)
        impact_per_flag = behavioral_score / len(behavioral_flags) if behavioral_flags else 0
        for b_flag in behavioral_flags:
             xai_impacts[b_flag] = impact_per_flag

    reasons = []
    reasons.extend(behavioral_flags)
    if is_velocity_flag: reasons.append("HIGH_VELOCITY")
    if is_sybil_flag: reasons.append("ADDRESS_SYBIL_DETECTED")
    if is_price_anomaly: reasons.append("HIGH_DEVIATION")
    if is_vpn_flag: reasons.append("ANONYMOUS_IP_DETECTED")
    if is_identity_flag: reasons.append("GLOBAL_IDENTITY_BLACKLIST")
    if is_global_network_flag: reasons.append("GLOBAL_CONSORTIUM_BLOCK")
    if is_quarantined: reasons.append("GLOBAL_QUARANTINE_TRIGGERED")
    if consortium_hits > 0: reasons.append(f"CROSS_MERCHANT_FRAUD_RING_DETECTED({consortium_hits})")
    if is_gibberish_flag: reasons.append("GIBBERISH_ADDRESS")
    if is_device_velocity_flag: reasons.append("DEVICE_FINGERPRINT_VELOCITY")
    if is_suspicious_name_flag: reasons.append("SUSPICIOUS_NAME")
    if is_geo_velocity_flag: reasons.append("IMPOSSIBLE_TRAVEL")
    if is_time_anomaly_flag: reasons.append("TIME_OF_DAY_ANOMALY")
    if is_bot_speed_flag: reasons.append("BOT_SPEED_CHECKOUT")
    if is_suspicious_phone_flag: reasons.append("SUSPICIOUS_PHONE")
    if is_disposable_email_flag: reasons.append("DISPOSABLE_EMAIL")
    if is_email_name_mismatch_flag: reasons.append("EMAIL_NAME_MISMATCH")
    if is_poor_address_flag: reasons.append("POOR_ADDRESS_STRUCTURE")
    if is_high_risk_pin_flag: reasons.append("HIGH_RISK_PIN")
    if is_cluster_flag: reasons.append("IDENTITY_CLUSTER_DETECTED")
    if trust_score < risk_config["trust_floor"] and trust_score != 50.0: reasons.append("LOW_TRUST_SCORE")
    
    # Global Pulse Indicators
    avg_rep = sum(reputation_map.values()) / len(reputation_map) if reputation_map else 0.5
    if avg_rep < 0.4: reasons.append("GLOBAL_REPUTATION_WARNING")
    elif avg_rep > 0.8: reasons.append("NETWORK_WIDE_TRUSTED_USER")
    
    risk_result = {"score": risk_score, "flags": reasons, "trust_score": trust_score, "xai_impacts": xai_impacts, "metrics": {"velocity": is_velocity_flag, "sybil": is_sybil_flag, "price": is_price_anomaly, "trust": trust_score, "vpn": is_vpn_flag, "global_network": is_global_network_flag, "is_quarantined": is_quarantined, "consortium_hits": consortium_hits, "gibberish": is_gibberish_flag, "device_velocity": is_device_velocity_flag, "suspicious_name": is_suspicious_name_flag, "geo_velocity": is_geo_velocity_flag, "time_anomaly": is_time_anomaly_flag, "bot_speed": is_bot_speed_flag, "suspicious_phone": is_suspicious_phone_flag, "disposable_email": is_disposable_email_flag, "email_name_mismatch": is_email_name_mismatch_flag, "poor_address": is_poor_address_flag, "high_risk_pin": is_high_risk_pin_flag, "order_hash": order_hash}}
    risk_result["decision"] = "BLOCK" if risk_score >= risk_config.get("decision_threshold", 50.0) else "ALLOW"

    # Phase 28: Enterprise Telemetry (Usage-based Billing)
    latency_ms = (time.time() - start_time) * 1000 # Use start_time defined at the beginning of the function
    savings = 70.0 if risk_result["decision"] == "BLOCK" else 0.0
    asyncio.create_task(telemetry_service.record_scan(
        team_id=merchant_email, # Fallback to email if team_id not in context
        latency_ms=latency_ms,
        risk_score=risk_score,
        savings_inr=savings
    ))

    return risk_result
