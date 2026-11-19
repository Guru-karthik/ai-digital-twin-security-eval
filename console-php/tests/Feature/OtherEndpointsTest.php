<?php

namespace Tests\Feature;

use App\Models\AuditEvent;
use App\Models\Conversation;
use App\Models\EvaluationRun;

class OtherEndpointsTest extends ApiTestCase
{
    private function conv(string $id = 'c1'): array
    {
        return ['external_id' => $id, 'defense' => 'D2', 'model' => 'qwen3:8b',
            'messages' => [['role' => 'user', 'content' => 'hi'], ['role' => 'assistant', 'content' => 'hello']]];
    }

    public function test_conversation_create_list_show(): void
    {
        $this->service()->postJson('/api/v1/conversations', $this->conv())
            ->assertCreated()->assertJson(['external_id' => 'c1', 'message_count' => 2])->assertJsonMissing(['content' => 'hi']);

        $this->actingAs($this->viewer(), 'sanctum');
        $this->getJson('/api/v1/conversations')->assertOk()->assertJsonMissing(['content' => 'hi']);
        $id = Conversation::firstOrFail()->id;
        $this->getJson("/api/v1/conversations/$id")->assertOk()->assertJsonPath('messages.0.content', 'hi');
    }

    public function test_conversation_validation_and_unique_external_id(): void
    {
        $this->service()->postJson('/api/v1/conversations', $this->conv())->assertCreated();
        $this->service()->postJson('/api/v1/conversations', $this->conv())->assertStatus(422);
        $bad = $this->conv('c2');
        $bad['messages'][0]['role'] = 'system';
        $this->service()->postJson('/api/v1/conversations', $bad)->assertStatus(422);
    }

    public function test_conversation_create_needs_service_token(): void
    {
        $this->postJson('/api/v1/conversations', $this->conv())->assertStatus(401);
    }

    public function test_evaluation_run_create_and_list_filter(): void
    {
        $run = ['run_key' => 'defenses-dev-qwen3-8b', 'defense' => 'D2', 'model' => 'qwen3:8b', 'total_cases' => 10,
            'passed_cases' => 8, 'attack_success_rate' => 0.2, 'failed_checks' => ['case-1']];
        $this->service()->postJson('/api/v1/evaluation-runs', $run)->assertCreated()->assertJson(['passed_cases' => 8]);

        $this->actingAs($this->viewer(), 'sanctum');
        $this->getJson('/api/v1/evaluation-runs?defense=D2')->assertOk()->assertJson(['total' => 1]);
        $this->getJson('/api/v1/evaluation-runs?defense=D3')->assertOk()->assertJson(['total' => 0]);
        $id = EvaluationRun::firstOrFail()->id;
        $this->getJson("/api/v1/evaluation-runs/$id")->assertOk()->assertJsonPath('failed_checks.0', 'case-1');
    }

    public function test_evaluation_run_post_is_idempotent_upsert(): void
    {
        $run = ['run_key' => 'r1', 'defense' => 'D2', 'model' => 'm', 'total_cases' => 10, 'passed_cases' => 8];
        $this->service()->postJson('/api/v1/evaluation-runs', $run)->assertCreated();
        $this->service()->postJson('/api/v1/evaluation-runs', [...$run, 'passed_cases' => 9])
            ->assertOk()->assertJson(['passed_cases' => 9]);
        $this->service()->postJson('/api/v1/evaluation-runs', [...$run, 'defense' => 'D3'])->assertCreated();

        $this->assertSame(2, EvaluationRun::count());
        $this->assertSame(9, EvaluationRun::where('defense', 'D2')->firstOrFail()->passed_cases);
    }

    public function test_evaluation_run_validation(): void
    {
        $base = ['run_key' => 'r', 'defense' => 'D2', 'model' => 'm', 'total_cases' => 5, 'passed_cases' => 9];
        $this->service()->postJson('/api/v1/evaluation-runs', $base)->assertStatus(422);
        $this->service()->postJson('/api/v1/evaluation-runs', [...$base, 'passed_cases' => 1, 'attack_success_rate' => 1.5])->assertStatus(422);
    }

    public function test_audit_event_create_and_filter(): void
    {
        $this->service()->postJson('/api/v1/audit-events', ['type' => 'policy_decision', 'actor' => 'agent', 'detail' => ['decision' => 'deny']])
            ->assertCreated();
        $this->service()->postJson('/api/v1/audit-events', ['type' => 'bogus', 'actor' => 'agent'])->assertStatus(422);

        $this->actingAs($this->viewer(), 'sanctum');
        $this->getJson('/api/v1/audit-events?type=policy_decision')->assertOk()->assertJson(['total' => 1]);
        $this->getJson('/api/v1/audit-events?type=tool_call')->assertOk()->assertJson(['total' => 0]);
        $this->assertSame(1, AuditEvent::count());
    }

    public function test_read_endpoints_require_auth(): void
    {
        foreach (['conversations', 'evaluation-runs', 'audit-events', 'leads'] as $path) {
            $this->getJson("/api/v1/$path")->assertStatus(401);
        }
    }

    public function test_api_errors_are_json_not_html(): void
    {
        $this->getJson('/api/v1/nope')->assertStatus(404)->assertHeader('Content-Type', 'application/json');
    }
}
