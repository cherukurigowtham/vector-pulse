package repository

import (
	"context"
	"github.com/redis/go-redis/v9"
)

type Cache interface {
	HExists(ctx context.Context, key, field string) (bool, error)
	HGetAll(ctx context.Context, key string) (map[string]string, error)
	HSet(ctx context.Context, key string, values ...interface{}) error
	SAdd(ctx context.Context, key string, members ...interface{}) error
	Set(ctx context.Context, key string, value interface{}, expiration int) error
}

type RedisStore struct {
	client *redis.Client
}

func NewRedisStore(client *redis.Client) *RedisStore {
	return &RedisStore{client: client}
}

func (r *RedisStore) HExists(ctx context.Context, key, field string) (bool, error) {
	return r.client.HExists(ctx, key, field).Result()
}

func (r *RedisStore) HGetAll(ctx context.Context, key string) (map[string]string, error) {
	return r.client.HGetAll(ctx, key).Result()
}

func (r *RedisStore) HSet(ctx context.Context, key string, values ...interface{}) error {
	return r.client.HSet(ctx, key, values...).Err()
}

func (r *RedisStore) SAdd(ctx context.Context, key string, members ...interface{}) error {
	return r.client.SAdd(ctx, key, members...).Err()
}

func (r *RedisStore) Set(ctx context.Context, key string, value interface{}, expiration int) error {
	return r.client.Set(ctx, key, value, 0).Err()
}
