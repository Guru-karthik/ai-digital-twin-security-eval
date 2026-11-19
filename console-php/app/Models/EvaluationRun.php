<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;

#[Fillable(['run_key', 'defense', 'model', 'total_cases', 'passed_cases', 'attack_success_rate',
    'mean_latency_s', 'cost_usd', 'failed_checks'])]
class EvaluationRun extends Model
{
    protected function casts(): array
    {
        return ['failed_checks' => 'array'];
    }
}
