<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;

#[Fillable(['type', 'actor', 'subject', 'detail'])]
class AuditEvent extends Model
{
    public const TYPES = ['tool_call', 'policy_decision', 'output_guard', 'admin_action', 'eval_run'];

    protected function casts(): array
    {
        return ['detail' => 'array'];
    }
}
