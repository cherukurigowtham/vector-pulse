package core

import (
	"context"
	"fmt"
	"vantix/internal/config"

	"github.com/redis/go-redis/v9"
)

var RDB *redis.Client
var Ctx = context.Background()

func InitRedis() {
	addr := fmt.Sprintf("%s:%d", config.GlobalConfig.RedisHost, config.GlobalConfig.RedisPort)
	
	RDB = redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: config.GlobalConfig.RedisPassword,
		DB:       0, // use default DB
	})

	// Test connection
	_, err := RDB.Ping(Ctx).Result()
	if err != nil {
		fmt.Printf("Redis connection failed: %v\n", err)
	}
}
