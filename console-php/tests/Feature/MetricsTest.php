<?php

namespace Tests\Feature;

use App\Models\Lead;

class MetricsTest extends ApiTestCase
{
    public function test_disabled_without_token(): void
    {
        config(['services.console.metrics_token' => '']);
        $this->get('/metrics')->assertNotFound();
        $this->withToken('')->get('/metrics')->assertNotFound();
    }

    public function test_requires_the_right_token(): void
    {
        config(['services.console.metrics_token' => 'm-token']);
        $this->get('/metrics')->assertStatus(401);
        $this->withToken('wrong')->get('/metrics')->assertStatus(401);
        $this->withToken(self::SERVICE_TOKEN)->get('/metrics')->assertStatus(401); // service token is not the metrics token
    }

    public function test_exposes_counts_in_prometheus_format(): void
    {
        config(['services.console.metrics_token' => 'm-token']);
        Lead::create(['email' => 'a@example.com']);

        $res = $this->withToken('m-token')->get('/metrics')->assertOk();
        $this->assertStringContainsString('text/plain', $res->headers->get('Content-Type'));
        $body = $res->getContent();
        $this->assertStringContainsString('console_leads{status="pending"} 1', $body);
        $this->assertStringContainsString('console_leads{status="approved"} 0', $body);
        $this->assertStringContainsString('console_audit_events{type="admin_action"} 0', $body);
        $this->assertStringNotContainsString('a@example.com', $body); // counts only, no personal data
    }
}
