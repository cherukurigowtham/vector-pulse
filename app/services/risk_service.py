import asyncio
import time
import hashlib
import logging
import datetime
import vector_pulse
import json
import math
from app.models import Order
from app.core.redis import r
from app.core.geoip import GEO_READER
from app.db.database import AUDIT_STORE
from app.services.graph_service import link_identity
from app.services.vector_service import generate_semantic_hash, check_vector_cluster

async def _log_audit_event(risk_id: str, email: str, context: dict, decision: str, shadow: bool):
    try:
        payload = {
            "risk_id": risk_id,
            "uid": context["uid"],
            "email": email,
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
    return f"{kind}:{_merchant_scope(key_hash)}:{suffix}"

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
        vel_key = f"global:velocity:ip:{ip}"
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
        key = f"global:sybil:addr:{address_hash}"
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
        vel_key = f"device:velocity:{device_hash}"
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
                idx_key = f"addr_index:{merchant_email}"
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
        
        cache_key = f"ipint:{ip}"
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
        geo_key = f"geo:velocity:{device_hash}"
        last_geo_raw = await r.get(geo_key)
        
        is_impossible_travel = False
        if last_geo_raw:
            last_geo = json.loads(last_geo_raw)
            last_lat, last_lon, last_ts = last_geo["lat"], last_geo["lon"], last_geo["ts"]
            
            dist_km = _calculate_haversine(last_lat, last_lon, lat, lon)
            time_diff_hours = (now - last_ts) / 3600.0
            
            if time_diff_hours > 0:
                speed_kmh = dist_km / time_diff_hours
                # If speed > 800 km/h (speed of a commercial jet), flag as impossible travel
                if speed_kmh > 800 and dist_km > 50:
                    is_impossible_travel = True
                    logging.warning(f"Impossible Travel Detected: {speed_kmh:.1f} km/h for device {device_hash}")
            
        await r.setex(geo_key, 3600 * 24, json.dumps({"lat": lat, "lon": lon, "ts": now}))
        return is_impossible_travel
    except Exception as e:
        logging.error(f"Geo Velocity Check Failed: {e}")
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
    domain = email.rsplit("@", 1)[1].lower()
    cache_key = f"disposable:{domain}"
    cached = await r.get(cache_key)
    if cached is not None: return cached == "1"
    disposable_domains = {"mailinator.com", "yopmail.com", "10minutemail.com", "temp-mail.org"} # etc
    is_disposable = domain in disposable_domains
    await r.setex(cache_key, 86400, "1" if is_disposable else "0")
    return is_disposable

async def _check_high_risk_pin(pin: str | None) -> bool:
    if not pin: return False
    try:
        return await r.sismember("high_risk_pins", pin.strip())
    except Exception:
        return False

async def _check_identity_cache(email: str | None, phone: str | None) -> bool:
    """Checks if the email or phone is in the global high-risk identity set."""
    try:
        async with r.pipeline() as pipe:
            if email: pipe.sismember("global:blacklist:email", email.lower().strip())
            if phone: pipe.sismember("global:blacklist:phone", phone.strip())
            res = await pipe.execute()
        return any(res)
    except Exception as e:
        logging.error(f"Identity Cache Check Failed: {e}")
        return False

async def _check_identity_cluster(uid: str, address: str, pin: str, ip: str, merchant_key_hash: str) -> tuple[bool, float]:
    try:
        addr_fp = vector_pulse.address_fingerprint(address)
        subnet = _ip_prefix(ip)
        
        addr_key = f"cluster:addr:{merchant_key_hash}:{hashlib.md5(addr_fp.encode()).hexdigest()}"
        pin_key = f"cluster:pin:{merchant_key_hash}:{pin}"
        subnet_key = f"cluster:subnet:{merchant_key_hash}:{subnet}"
        
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

def _calculate_risk_score(velocity_flag, sybil_flag, anomaly_flag, identity_flag, cohort_flag, trust_score, vpn_flag, global_network_flag, gibberish_flag, device_velocity_flag, suspicious_name_flag, geo_velocity_flag, time_anomaly_flag, bot_speed_flag, suspicious_phone_flag, disposable_email_flag, email_name_mismatch_flag, poor_address_flag, high_risk_pin_flag, risk_config, consortium_hits=0):
    score = 0.0
    if velocity_flag: score += risk_config["velocity_weight"]
    if sybil_flag: score += risk_config["sybil_weight"]
    if anomaly_flag: score += risk_config["anomaly_weight"]
    if identity_flag: score += risk_config["identity_weight"]
    if vpn_flag: score += risk_config["vpn_weight"]
    if global_network_flag: score += risk_config["global_network_weight"]
    if gibberish_flag: score += risk_config["gibberish_weight"]
    if device_velocity_flag: score += risk_config["device_velocity_weight"]
    if suspicious_name_flag: score += risk_config["suspicious_name_weight"]
    if geo_velocity_flag: score += risk_config["geo_velocity_weight"]
    if time_anomaly_flag: score += risk_config["time_anomaly_weight"]
    if bot_speed_flag: score += risk_config["bot_speed_weight"]
    if suspicious_phone_flag: score += risk_config["suspicious_phone_weight"]
    if disposable_email_flag: score += risk_config["disposable_email_weight"]
    if email_name_mismatch_flag: score += risk_config["email_name_mismatch_weight"]
    if poor_address_flag: score += risk_config["poor_address_weight"]
    if high_risk_pin_flag: score += risk_config["high_risk_pin_weight"]
    
    # Pillar 2: Consortium Multiplier
    if consortium_hits > 0:
        # Each unique merchant hit adds weight, capped at 3 hits for scoring
        score += min(3, consortium_hits) * risk_config.get("global_network_weight", 15.0)

    trust_floor = risk_config["trust_floor"]
    if trust_score < trust_floor:
        score += (trust_floor - trust_score) * risk_config["trust_penalty_multiplier"]
    return max(0.0, min(100.0, score))

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

async def run_risk_analysis(order: Order, risk_config: dict, merchant_key_hash: str, merchant_email: str):
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
    
    results = await asyncio.gather(
        velocity_task, sybil_task, price_task, trust_task, ip_task, 
        global_velocity_task, global_sybil_task, device_velocity_task, 
        geo_velocity_task, high_risk_pin_task, is_disposable_email_task,
        identity_cache_task, identity_cluster_task, graph_task, quarantine_task
    )
    (
        is_velocity_flag, is_sybil_flag, (is_price_anomaly, avg, std_dev), 
        trust_score, is_vpn_flag, is_global_velocity_flag, is_global_sybil_flag, 
        is_device_velocity_flag, is_geo_velocity_flag, is_high_risk_pin_flag, 
        is_disposable_email_flag, is_identity_flag, (is_cluster_flag, cluster_score),
        consortium_hits, is_quarantined
    ) = results
    
    is_global_network_flag = is_global_velocity_flag or is_global_sybil_flag or (consortium_hits > 0) or is_quarantined

    # Pillar 4: Behavioral DNA
    behavioral_flags, behavioral_score = _check_behavioral_dna(order, risk_config)
    
    is_global_network_flag = is_global_velocity_flag or is_global_sybil_flag or (consortium_hits > 0)
    
    risk_score = _calculate_risk_score(is_velocity_flag, is_sybil_flag, is_price_anomaly, is_identity_flag, is_cluster_flag, trust_score, is_vpn_flag, is_global_network_flag, is_gibberish_flag, is_device_velocity_flag, is_suspicious_name_flag, is_geo_velocity_flag, is_time_anomaly_flag, is_bot_speed_flag, is_suspicious_phone_flag, is_disposable_email_flag, is_email_name_mismatch_flag, is_poor_address_flag, is_high_risk_pin_flag, risk_config, consortium_hits=consortium_hits)
    risk_score = min(100.0, risk_score + behavioral_score)
    
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
    
    return {"score": risk_score, "flags": reasons, "trust_score": trust_score, "metrics": {"velocity": is_velocity_flag, "sybil": is_sybil_flag, "price": is_price_anomaly, "trust": trust_score, "vpn": is_vpn_flag, "global_network": is_global_network_flag, "is_quarantined": is_quarantined, "consortium_hits": consortium_hits, "gibberish": is_gibberish_flag, "device_velocity": is_device_velocity_flag, "suspicious_name": is_suspicious_name_flag, "geo_velocity": is_geo_velocity_flag, "time_anomaly": is_time_anomaly_flag, "bot_speed": is_bot_speed_flag, "suspicious_phone": is_suspicious_phone_flag, "disposable_email": is_disposable_email_flag, "email_name_mismatch": is_email_name_mismatch_flag, "poor_address": is_poor_address_flag, "high_risk_pin": is_high_risk_pin_flag, "order_hash": order_hash}}
