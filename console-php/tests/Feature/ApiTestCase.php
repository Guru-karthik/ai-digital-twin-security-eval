<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

abstract class ApiTestCase extends TestCase
{
    use RefreshDatabase;

    protected const SERVICE_TOKEN = 'test-service-token';

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.console.service_token' => self::SERVICE_TOKEN]);
    }

    protected function admin(): User
    {
        return User::factory()->create(['role' => 'admin']);
    }

    protected function viewer(): User
    {
        return User::factory()->create(['role' => 'viewer']);
    }

    protected function service(): static
    {
        return $this->withToken(self::SERVICE_TOKEN);
    }
}
