<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\EvaluationRun;
use Illuminate\Http\Request;

class EvaluationRunController extends Controller
{
    use Paginates;

    public function index(Request $request)
    {
        $request->validate(['defense' => ['sometimes', 'string', 'max:32']]);
        $q = EvaluationRun::query();
        if ($request->filled('defense')) {
            $q->where('defense', $request->query('defense'));
        }

        return $this->paginated($q, $request);
    }

    public function show(EvaluationRun $evaluationRun)
    {
        return $evaluationRun;
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'run_key' => ['required', 'string', 'max:255'],
            'defense' => ['required', 'string', 'max:32'],
            'model' => ['required', 'string', 'max:100'],
            'total_cases' => ['required', 'integer', 'min:0'],
            'passed_cases' => ['required', 'integer', 'min:0', 'lte:total_cases'],
            'attack_success_rate' => ['sometimes', 'nullable', 'numeric', 'between:0,1'],
            'mean_latency_s' => ['sometimes', 'nullable', 'numeric'],
            'cost_usd' => ['sometimes', 'nullable', 'numeric'],
            'failed_checks' => ['sometimes', 'array'],
            'failed_checks.*' => ['string', 'max:500'],
        ]);

        // Idempotent: re-posting the same (run_key, model, defense) updates that run instead of duplicating it.
        $run = EvaluationRun::updateOrCreate(
            ['run_key' => $data['run_key'], 'model' => $data['model'], 'defense' => $data['defense']],
            $data,
        );

        return response()->json($run->refresh(), $run->wasRecentlyCreated ? 201 : 200);
    }
}
