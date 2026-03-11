import redis

# Connect to the local database
r = redis.Redis(host='localhost', port=6379, db=0)

# Store a feature (User 2's average from your log)
r.set('user:user_2:avg', 1579.34)

# Retrieve it
val = r.get('user:user_2:avg')
print(f"Redis Feature Store: {val.decode('utf-8')}")
