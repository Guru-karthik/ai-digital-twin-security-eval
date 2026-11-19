<?php

namespace Tests\Feature;

use App\Models\AuditEvent;
use App\Models\Lead;

class LeadApiTest extends ApiTestCase
{
    public function test_service_can_create_lead_and_status_is_pending(): void
    {
        $this->service()->postJson('/api/v1/leads', ['email' => 'v@example.com', 'name' => 'V', 'notes' => 'hi'])
            ->assertCreated()->assertJson(['email' => 'v@example.com', 'status' => 'pending']);
    }

    public function test_create_cannot_set_status(): void
    {
        $this->service()->postJson('/api/v1/leads', ['email' => 'v@example.com', 'status' => 'approved'])
            ->assertCreated()->assertJson(['status' => 'pending']);
    }

    public function test_create_requires_service_token(): void
    {
        $this->postJson('/api/v1/leads', ['email' => 'v@example.com'])->assertStatus(401);
        $this->withToken('wrong')->postJson('/api/v1/leads', ['email' => 'v@example.com'])->assertStatus(401);
        $this->actingAs($this->admin(), 'sanctum')->postJson('/api/v1/leads', ['email' => 'v@example.com'])->assertStatus(401);
    }

    public function test_service_endpoints_fail_closed_when_token_unset(): void
    {
        config(['services.console.service_token' => '']);
        $this->postJson('/api/v1/leads', ['email' => 'v@example.com'])->assertStatus(401);
        $this->withToken('')->postJson('/api/v1/leads', ['email' => 'v@example.com'])->assertStatus(401);
    }

    public function test_create_validates(): void
    {
        $this->service()->postJson('/api/v1/leads', ['email' => 'bad'])->assertStatus(422);
        $this->service()->postJson('/api/v1/leads', ['email' => 'a@example.com', 'notes' => str_repeat('x', 2001)])->assertStatus(422);
    }

    public function test_list_requires_auth_and_paginates(): void
    {
        Lead::create(['email' => 'a@example.com']);
        Lead::create(['email' => 'b@example.com']);

        $this->getJson('/api/v1/leads')->assertStatus(401);
        $this->actingAs($this->viewer(), 'sanctum')->getJson('/api/v1/leads?per_page=1')
            ->assertOk()->assertJson(['page' => 1, 'per_page' => 1, 'total' => 2])->assertJsonCount(1, 'data');
    }

    public function test_list_filters_by_status_and_validates_it(): void
    {
        Lead::create(['email' => 'a@example.com']);
        $this->actingAs($this->viewer(), 'sanctum');

        $this->getJson('/api/v1/leads?status=approved')->assertOk()->assertJson(['total' => 0]);
        $this->getJson('/api/v1/leads?status=bogus')->assertStatus(422);
        $this->getJson('/api/v1/leads?per_page=1000')->assertStatus(422);
    }

    public function test_show_and_404(): void
    {
        $lead = Lead::create(['email' => 'a@example.com']);
        $this->actingAs($this->viewer(), 'sanctum');

        $this->getJson("/api/v1/leads/{$lead->id}")->assertOk()->assertJson(['email' => 'a@example.com']);
        $this->getJson('/api/v1/leads/999')->assertStatus(404);
    }

    public function test_admin_can_approve_and_it_is_audited(): void
    {
        $lead = Lead::create(['email' => 'a@example.com']);
        $admin = $this->admin();

        $this->actingAs($admin, 'sanctum')->patchJson("/api/v1/leads/{$lead->id}", ['status' => 'approved'])
            ->assertOk()->assertJson(['status' => 'approved', 'reviewed_by' => $admin->id]);

        $event = AuditEvent::firstOrFail();
        $this->assertSame('admin_action', $event->type);
        $this->assertSame("lead:{$lead->id}", $event->subject);
        $this->assertSame($admin->email, $event->actor);
    }

    public function test_viewer_cannot_review(): void
    {
        $lead = Lead::create(['email' => 'a@example.com']);

        $this->actingAs($this->viewer(), 'sanctum')->patchJson("/api/v1/leads/{$lead->id}", ['status' => 'approved'])->assertStatus(403);
        $this->assertSame('pending', $lead->fresh()->status);
        $this->assertDatabaseCount('audit_events', 0);
    }

    public function test_review_rejects_invalid_status(): void
    {
        $lead = Lead::create(['email' => 'a@example.com']);

        $this->actingAs($this->admin(), 'sanctum')->patchJson("/api/v1/leads/{$lead->id}", ['status' => 'pending'])->assertStatus(422);
    }

    public function test_html_in_notes_is_stored_verbatim_and_returned_as_json(): void
    {
        $this->service()->postJson('/api/v1/leads', ['email' => 'a@example.com', 'notes' => '<script>alert(1)</script>'])->assertCreated();
        $this->actingAs($this->viewer(), 'sanctum')->getJson('/api/v1/leads')
            ->assertHeader('Content-Type', 'application/json')->assertJsonPath('data.0.notes', '<script>alert(1)</script>');
    }
}
