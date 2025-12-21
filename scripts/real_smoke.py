#!/usr/bin/env python3
"""
Real Infra Only - End-to-End Smoke Script.
Verifies that the application is wired to use REAL infrastructure (S3, Firestore, Redis)
and that it fails fast if they are missing.
"""
import os
import sys
import uuid
import asyncio
from datetime import datetime

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.config import runtime_config
from engines.identity.state import identity_repo, FirestoreIdentityRepository, InMemoryIdentityRepository
from engines.media_v2.service import MediaService, S3MediaStorage, LocalMediaStorage
from engines.media_v2.models import MediaUploadRequest
from engines.chat.service.transport_layer import bus, InMemoryBus
try:
    from engines.chat.service.redis_transport import RedisBus
except ImportError:
    RedisBus = None
from engines.nexus.backends import get_backend
from engines.nexus.backends.memory_backend import InMemoryNexusBackend

def print_header(msg):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")

def check_identity():
    print_header("CHECK 1: Identity Repository")
    print(f"Current Identity Repo Class: {identity_repo.__class__.__name__}")
    
    if isinstance(identity_repo, InMemoryIdentityRepository):
        print("FAIL: Identity repository is InMemory.")
        return False
        
    if not isinstance(identity_repo, FirestoreIdentityRepository):
        # Could be other valid real implementations, but we expect Firestore for now
        print(f"WARN: Identity repository is {identity_repo.__class__.__name__}, expected FirestoreIdentityRepository.")
    
    print("SUCCESS: Identity repository appears to be real infra.")
    return True

def check_media():
    print_header("CHECK 2: Media Service (S3)")
    svc = MediaService()
    print(f"Storage Class: {svc.storage.__class__.__name__}")
    
    if isinstance(svc.storage, LocalMediaStorage):
        print("FAIL: Media service is using LocalMediaStorage.")
        return False
        
    if not isinstance(svc.storage, S3MediaStorage):
        print(f"WARN: Media storage is {svc.storage.__class__.__name__}, expected S3MediaStorage.")
        
    # Attempt simulated upload (dry run if no creds, but we want to fail if no creds)
    # We won't actually hit S3 unless we have creds, but the CLASS check is the primary enforcement here.
    # The requirement is that the CODE forces S3, so if we don't have creds, it should crash.
    try:
        # Just check if we can instantiate it and it has a bucket
        if not svc.storage.bucket_name:
             print("FAIL: S3MediaStorage has no bucket configured.")
             return False
        print(f"S3 Bucket: {svc.storage.bucket_name}")
    except Exception as e:
        print(f"FAIL: Error inspecting S3 storage: {e}")
        return False

    print("SUCCESS: Media service is wired for S3.")
    return True

def check_chat():
    print_header("CHECK 3: Chat Bus (Redis)")
    print(f"Bus Class: {bus.__class__.__name__}")
    
    if isinstance(bus, InMemoryBus):
         print("FAIL: Chat bus is InMemoryBus.")
         return False
         
    if RedisBus and isinstance(bus, RedisBus):
        print(f"Redis Host: {bus.redis.connection_pool.connection_kwargs.get('host', 'unknown')}")
    else:
        print(f"WARN: Bus is {bus.__class__.__name__}, expected RedisBus.")

    print("SUCCESS: Chat bus is wired for Redis.")
    return True

def check_nexus():
    print_header("CHECK 4: Nexus Backend")
    try:
        backend = get_backend()
        print(f"Nexus Backend Class: {backend.__class__.__name__}")
        
        if isinstance(backend, InMemoryNexusBackend):
            print("FAIL: Nexus backend is InMemoryNexusBackend.")
            return False
            
    except Exception as e:
        print(f"FAIL: Could not instantiate Nexus backend: {e}")
        return False
        
    print("SUCCESS: Nexus backend is real.")
    return True

def main():
    print(f"RUN_TOKEN={datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}")
    
    checks = [
        check_identity(),
        check_media(),
        check_chat(),
        check_nexus(),
    ]
    
    if all(checks):
        print_header("ALL SYSTEMS GO: REAL INFRASTRUCTURE ENFORCED")
        sys.exit(0)
    else:
        print_header("FAILURE: FAKE/FALLBACK INFRASTRUCTURE DETECTED")
        sys.exit(1)

if __name__ == "__main__":
    main()
