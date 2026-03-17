import json
import logging
import time
from typing import Dict, Any, List, Set
from app.core.redis import r

logger = logging.getLogger(__name__)

class IdentityLinker:
    """
    Phase 23: Predictive Identity Links.
    Maintains a real-time identity graph in Redis to detect coordinated fraud rings.
    """

    async def link_identities(self, email: str, ip: str, device_id: str = None):
        """
        Creates bidirectional links between email, IP, and device ID.
        """
        try:
            # Atomic linking using Redis sets
            pipe = r.pipeline()
            
            # Email -> IPs/Devices
            pipe.sadd(f"id:email:{email}:ips", ip)
            if device_id: pipe.sadd(f"id:email:{email}:devices", device_id)
            
            # IP -> Emails/Devices
            pipe.sadd(f"id:ip:{ip}:emails", email)
            if device_id: pipe.sadd(f"id:ip:{ip}:devices", device_id)
            
            # Device -> Emails/IPs
            if device_id:
                pipe.sadd(f"id:device:{device_id}:emails", email)
                pipe.sadd(f"id:device:{device_id}:ips", ip)
            
            # TTL for graph nodes (30 days)
            keys = [f"id:email:{email}:ips", f"id:email:{email}:devices", 
                    f"id:ip:{ip}:emails", f"id:ip:{ip}:devices"]
            if device_id:
                keys.extend([f"id:device:{device_id}:emails", f"id:device:{device_id}:ips"])
            
            for key in keys:
                pipe.expire(key, 86400 * 30)
                
            await pipe.execute()
        except Exception as e:
            logger.error(f"Identity linking failed: {e}")

    async def get_cluster_stats(self, email: str, ip: str, device_id: str = None) -> Dict[str, Any]:
        """
        Calculates the density of the identity cluster.
        Returns the number of unique emails/IPs/Devices connected to this transaction.
        """
        try:
            # Find all emails sharing this IP
            emails_on_ip = await r.smembers(f"id:ip:{ip}:emails")
            # Find all IPs used by this email
            ips_for_email = await r.smembers(f"id:email:{email}:ips")
            
            unique_emails = set(emails_on_ip)
            unique_ips = set(ips_for_email)
            unique_devices = set()
            
            if device_id:
                emails_on_device = await r.smembers(f"id:device:{device_id}:emails")
                unique_emails.update(emails_on_device)
                
            stats = {
                "cluster_size": len(unique_emails),
                "ip_span": len(unique_ips),
                "is_active_ring": len(unique_emails) > 5 # Threshold for a 'ring'
            }
            return stats
        except:
            return {"cluster_size": 0, "ip_span": 0, "is_active_ring": False}

    async def get_identity_graph(self, id_type: str, id_val: str) -> Dict[str, List[str]]:
        """
        Retrieves direct neighbors in the identity graph.
        """
        if id_type not in ["email", "ip", "device"]:
            return {}
            
        data = {}
        if id_type == "email":
            data["ips"] = list(await r.smembers(f"id:email:{id_val}:ips"))
            data["devices"] = list(await r.smembers(f"id:email:{id_val}:devices"))
        elif id_type == "ip":
            data["emails"] = list(await r.smembers(f"id:ip:{id_val}:emails"))
            data["devices"] = list(await r.smembers(f"id:ip:{id_val}:devices"))
        elif id_type == "device":
            data["emails"] = list(await r.smembers(f"id:device:{id_val}:emails"))
            data["ips"] = list(await r.smembers(f"id:device:{id_val}:ips"))
            
        return data

identity_linker = IdentityLinker()
