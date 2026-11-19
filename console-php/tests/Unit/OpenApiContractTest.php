<?php

namespace Tests\Unit;

use App\Models\AuditEvent;
use App\Models\Lead;
use App\Models\User;
use PHPUnit\Framework\TestCase;
use Symfony\Component\Yaml\Yaml;

/** Keeps the code's enums in step with docs/openapi.yaml (the contract written first in M1). */
class OpenApiContractTest extends TestCase
{
    private function schemas(): array
    {
        return Yaml::parseFile(dirname(__DIR__, 3).'/docs/openapi.yaml')['components']['schemas'];
    }

    public function test_lead_statuses_match_contract(): void
    {
        $this->assertSame($this->schemas()['LeadStatus']['enum'], Lead::STATUSES);
    }

    public function test_audit_types_match_contract(): void
    {
        $this->assertSame($this->schemas()['AuditType']['enum'], AuditEvent::TYPES);
    }

    public function test_roles_match_contract(): void
    {
        $this->assertSame($this->schemas()['Role']['enum'], User::ROLES);
    }
}
