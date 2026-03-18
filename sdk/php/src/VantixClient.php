<?php

namespace Vantix;

use Psr\Http\Client\ClientInterface;
use Psr\Http\Message\RequestFactoryInterface;
use Psr\Http\Message\StreamFactoryInterface;

class VantixClient
{
    private $apiKey;
    private $httpClient;
    private $requestFactory;
    private $streamFactory;
    private $baseUrl;

    public function __construct(
        string $apiKey,
        ClientInterface $httpClient,
        RequestFactoryInterface $requestFactory,
        StreamFactoryInterface $streamFactory,
        string $baseUrl = 'https://api.vantix.ai'
    ) {
        $this->apiKey = $apiKey;
        $this->httpClient = $httpClient;
        $this->requestFactory = $requestFactory;
        $this->streamFactory = $streamFactory;
        $this->baseUrl = rtrim($baseUrl, '/');
    }

    /**
     * Analyze an order for RTO risk.
     * 
     * @param array $orderData
     * @return array
     * @throws \Exception
     */
    public function analyze(array $orderData): array
    {
        $url = $this->baseUrl . '/v1/risk/analyze';
        
        $request = $this->requestFactory->createRequest('POST', $url)
            ->withHeader('Content-Type', 'application/json')
            ->withHeader('X-API-Key', $this->apiKey)
            ->withHeader('User-Agent', 'vantix-php/0.1.0')
            ->withBody($this->streamFactory->createStream(json_encode($orderData)));

        $response = $this->httpClient->sendRequest($request);

        if ($response->getStatusCode() !== 200) {
            throw new \Exception('Vantix API Error: Status ' . $response->getStatusCode());
        }

        return json_decode((string)$response->getBody(), true);
    }
}
