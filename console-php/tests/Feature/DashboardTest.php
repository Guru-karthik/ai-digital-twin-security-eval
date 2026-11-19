<?php

namespace Tests\Feature;

use App\Models\AuditEvent;
use App\Models\Conversation;
use App\Models\Lead;
use App\Models\User;

class DashboardTest extends ApiTestCase
{
    private const XSS = '<script>alert(1)</script>';

    public function test_pages_redirect_to_login_when_signed_out(): void
    {
        foreach (['/leads', '/conversations', '/evaluation-runs', '/audit-events'] as $path) {
            $this->get($path)->assertRedirect('/login');
        }
        $this->get('/')->assertRedirect('/leads');
    }

    public function test_login_flow_and_session_regeneration(): void
    {
        User::factory()->create(['email' => 'a@example.com', 'role' => 'admin']);

        $this->get('/login')->assertOk()->assertSee('Sign in');
        $this->post('/login', ['email' => 'a@example.com', 'password' => 'password'])->assertRedirect('/leads');
        $this->assertAuthenticated();
    }

    public function test_bad_login_shows_generic_error(): void
    {
        User::factory()->create(['email' => 'a@example.com']);

        $this->from('/login')->post('/login', ['email' => 'a@example.com', 'password' => 'bad'])
            ->assertRedirect('/login')->assertSessionHasErrors(['email' => 'Invalid credentials.']);
        $this->from('/login')->post('/login', ['email' => 'nobody@example.com', 'password' => 'bad'])
            ->assertSessionHasErrors(['email' => 'Invalid credentials.']);
        $this->assertGuest();
    }

    public function test_web_login_is_rate_limited(): void
    {
        for ($i = 0; $i < 5; $i++) {
            $this->post('/login', ['email' => 'x@example.com', 'password' => 'bad']);
        }
        $this->post('/login', ['email' => 'x@example.com', 'password' => 'bad'])->assertStatus(429);
    }

    public function test_logout_ends_session(): void
    {
        $this->actingAs($this->viewer())->post('/logout')->assertRedirect('/login');
        $this->assertGuest();
    }

    public function test_csrf_is_enforced_on_state_changing_posts(): void
    {
        $lead = Lead::create(['email' => 'a@example.com']);
        $this->actingAs($this->admin());
        $this->app['env'] = 'production'; // Laravel skips CSRF checks only when running unit tests
        $this->withMiddleware();

        $this->post("/leads/{$lead->id}/review", ['status' => 'approved'])->assertStatus(419);
        $this->assertSame('pending', $lead->fresh()->status);
    }

    public function test_admin_sees_review_buttons_and_can_approve(): void
    {
        $lead = Lead::create(['email' => 'a@example.com']);
        $admin = $this->admin();

        $this->actingAs($admin)->get('/leads')->assertOk()->assertSee('Approve')->assertSee('Reject');
        $this->actingAs($admin)->post("/leads/{$lead->id}/review", ['status' => 'approved'])->assertRedirect();
        $this->assertSame('approved', $lead->fresh()->status);
        $this->assertSame('admin_action', AuditEvent::firstOrFail()->type);
    }

    public function test_viewer_sees_no_review_buttons_and_cannot_approve(): void
    {
        $lead = Lead::create(['email' => 'a@example.com']);
        $viewer = $this->viewer();

        $this->actingAs($viewer)->get('/leads')->assertOk()->assertDontSee('Approve');
        $this->actingAs($viewer)->post("/leads/{$lead->id}/review", ['status' => 'approved'])->assertStatus(403);
        $this->assertSame('pending', $lead->fresh()->status);
    }

    public function test_review_rejects_invalid_status(): void
    {
        $lead = Lead::create(['email' => 'a@example.com']);

        $this->actingAs($this->admin())->post("/leads/{$lead->id}/review", ['status' => 'pending'])->assertSessionHasErrors('status');
    }

    public function test_user_content_is_escaped_everywhere(): void
    {
        Lead::create(['email' => 'a@example.com', 'name' => self::XSS, 'notes' => self::XSS]);
        $conv = Conversation::create(['external_id' => 'c1', 'defense' => self::XSS, 'message_count' => 1,
            'messages' => [['role' => 'user', 'content' => self::XSS]]]);
        AuditEvent::create(['type' => 'tool_call', 'actor' => self::XSS, 'subject' => self::XSS, 'detail' => ['x' => self::XSS]]);
        $viewer = $this->viewer();

        foreach (['/leads', '/conversations', "/conversations/{$conv->id}", '/audit-events'] as $path) {
            $body = $this->actingAs($viewer)->get($path)->assertOk()->getContent();
            $this->assertStringNotContainsString('<script>alert(1)', $body, "unescaped content on $path");
        }
        $this->actingAs($viewer)->get('/leads')->assertSee('&lt;script&gt;alert(1)&lt;/script&gt;', false);
    }

    public function test_conversation_detail_and_other_pages_render(): void
    {
        $conv = Conversation::create(['external_id' => 'c1', 'message_count' => 1, 'messages' => [['role' => 'user', 'content' => 'hello there']]]);
        $viewer = $this->viewer();

        $this->actingAs($viewer)->get("/conversations/{$conv->id}")->assertOk()->assertSee('hello there');
        $this->actingAs($viewer)->get('/conversations/999')->assertNotFound();
        $this->actingAs($viewer)->get('/evaluation-runs')->assertOk();
        $this->actingAs($viewer)->get('/audit-events')->assertOk();
    }

    public function test_security_headers_present(): void
    {
        $res = $this->get('/login');

        $res->assertHeader('X-Frame-Options', 'DENY')->assertHeader('X-Content-Type-Options', 'nosniff')
            ->assertHeader('Referrer-Policy', 'no-referrer');
        $csp = $res->headers->get('Content-Security-Policy');
        $this->assertStringContainsString("default-src 'none'", $csp);
        $this->assertStringContainsString("frame-ancestors 'none'", $csp);
        $this->assertStringNotContainsString('unsafe-inline', $csp);
        $this->assertStringContainsString('no-store', $res->headers->get('Cache-Control'));
    }

    public function test_hsts_only_over_https(): void
    {
        $this->get('/login')->assertHeaderMissing('Strict-Transport-Security');
        $this->get('https://localhost/login')->assertHeader('Strict-Transport-Security');
    }

    public function test_status_filter_ignores_unknown_values(): void
    {
        Lead::create(['email' => 'a@example.com']);

        $this->actingAs($this->viewer())->get('/leads?status=bogus')->assertOk()->assertSee('a@example.com');
    }
}
