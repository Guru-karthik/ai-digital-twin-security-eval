<?php

namespace Tests\Feature;

use App\Models\User;

class AuthTest extends ApiTestCase
{
    public function test_login_returns_token_and_role(): void
    {
        User::factory()->create(['email' => 'a@example.com', 'role' => 'admin']);

        $this->postJson('/api/v1/auth/login', ['email' => 'a@example.com', 'password' => 'password'])
            ->assertOk()->assertJsonStructure(['token', 'role'])->assertJson(['role' => 'admin']);
    }

    public function test_wrong_password_is_401(): void
    {
        User::factory()->create(['email' => 'a@example.com']);

        $this->postJson('/api/v1/auth/login', ['email' => 'a@example.com', 'password' => 'nope'])->assertStatus(401);
    }

    public function test_login_validates_input(): void
    {
        $this->postJson('/api/v1/auth/login', ['email' => 'not-an-email'])->assertStatus(422);
    }

    public function test_login_is_rate_limited(): void
    {
        for ($i = 0; $i < 5; $i++) {
            $this->postJson('/api/v1/auth/login', ['email' => 'x@example.com', 'password' => 'bad'])->assertStatus(401);
        }
        $this->postJson('/api/v1/auth/login', ['email' => 'x@example.com', 'password' => 'bad'])->assertStatus(429);
    }

    public function test_logout_revokes_token(): void
    {
        $token = $this->admin()->createToken('t')->plainTextToken;

        $this->withToken($token)->postJson('/api/v1/auth/logout')->assertNoContent();
        $this->assertDatabaseCount('personal_access_tokens', 0);
    }

    public function test_role_is_not_mass_assignable(): void
    {
        $u = new User(['name' => 'x', 'email' => 'x@example.com', 'role' => 'admin']);
        $this->assertNotSame('admin', $u->role);
    }
}
